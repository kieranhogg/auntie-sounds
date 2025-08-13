import re
import time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from urllib.parse import urljoin

import requests


class BaseStream:
    def __init__(self):
        self.is_dynamic = False
        self.segment_duration = 0
        self.segment_timescale = 1
        self.start_number = 1
        self.end_number = None
        self.comparison_start_number = None
        self.media_template = ""
        self.base_url = ""

    def get_segment_url(self, number):
        return self.base_url + self.media_template.replace("$Number$", str(number))

    def seek_to_offset(self, offset_seconds):
        ticks = int(offset_seconds * self.segment_timescale)
        segments = ticks // self.segment_duration
        if self.is_dynamic:
            segment_number = max(
                self.comparison_start_number, self.end_number - segments
            )
        else:
            segment_number = self.start_number + segments
        return segment_number

    def generate_playlist(self, start_segment, count):
        duration_sec = self.segment_duration / self.segment_timescale
        lines = [
            "#EXTM3U",
            "#EXT-X-VERSION:3",
            f"#EXT-X-MEDIA-SEQUENCE:{start_segment}",
            f"#EXT-X-TARGETDURATION:{int(duration_sec) + 1}",
        ]
        for i in range(count):
            num = start_segment + i
            if self.end_number and num > self.end_number:
                break
            url = self.get_segment_url(num)
            lines.append(f"#EXTINF:{duration_sec:.3f},")
            lines.append(url)
        if not self.is_dynamic:
            lines.append("#EXT-X-ENDLIST")
        return "\n".join(lines)


class DashStream(BaseStream):
    def __init__(self, mpd_url, allow, override_epoch=None):
        super().__init__()
        self.mpd_url = mpd_url
        self.allow = allow
        self.override_epoch = override_epoch
        self._parse_mpd()

    def _parse_mpd(self):
        def parse_duration(s):
            m = re.match(r"P(?:[^T]*T)?(?:(\d+)H)?(?:(\d+)M)?(?:([\d.]+)S)?", s or "")
            h, m_, s_ = (
                int(m.group(1) or 0),
                int(m.group(2) or 0),
                float(m.group(3) or 0),
            )
            return int(h * 3600 + m_ * 60 + s_)

        def parse_datetime(ts):
            try:
                return (
                    datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
                    .replace(tzinfo=UTC)
                    .timestamp()
                )
            except:
                return None

        r = requests.get(self.mpd_url)
        root = ET.fromstring(r.content)
        base = r.url

        self.base_url = urljoin(base, "./")
        self.is_dynamic = root.attrib.get("type", "static") == "dynamic"
        timeshift = parse_duration(root.attrib.get("timeShiftBufferDepth"))
        duration = parse_duration(root.attrib.get("mediaPresentationDuration"))
        availability_start = parse_datetime(
            root.attrib.get("availabilityStartTime", "")
        )

        period = root.find("Period")
        for adapt in period.findall("AdaptationSet"):
            if adapt.attrib.get("mimeType") != "audio/mp4":
                continue
            for rep in adapt.findall("Representation"):
                if any(rep.attrib.get("id") == a[0] for a in self.allow):
                    seg = adapt.find("SegmentTemplate")
                    self.media_template = seg.attrib.get("media")
                    self.segment_timescale = int(seg.attrib.get("timescale", "1"))
                    self.segment_duration = int(seg.attrib.get("duration"))
                    self.start_number = int(seg.attrib.get("startNumber", "1"))
                    now = (
                        time.time()
                        if self.override_epoch is None
                        else self.override_epoch
                    )
                    if self.is_dynamic and availability_start:
                        live_time = now - availability_start
                        seg_count = int(
                            (live_time * self.segment_timescale)
                            // self.segment_duration
                        )
                        self.end_number = self.start_number + seg_count
                        self.comparison_start_number = max(
                            self.start_number,
                            self.end_number
                            - (timeshift * self.segment_timescale)
                            // self.segment_duration,
                        )
                    else:
                        seg_count = int(
                            (duration * self.segment_timescale) // self.segment_duration
                        )
                        self.end_number = self.start_number + seg_count - 1
                        self.comparison_start_number = self.start_number
                    return


class HlsStream(BaseStream):
    def __init__(self, m3u8_url):
        super().__init__()
        self.m3u8_url = m3u8_url
        self._parse_m3u8()

    def _parse_m3u8(self):
        r = requests.get(self.m3u8_url)
        r.raise_for_status()
        lines = r.text.strip().splitlines()

        self.base_url = self.m3u8_url.rsplit("/", 1)[0] + "/"
        self.is_dynamic = "#EXT-X-ENDLIST" not in r.text

        media_sequence = 0
        durations = []
        segment_urls = []

        for i, line in enumerate(lines):
            if line.startswith("#EXT-X-MEDIA-SEQUENCE"):
                media_sequence = int(line.split(":")[1])
            elif line.startswith("#EXTINF:"):
                duration = float(line.split(":")[1].rstrip(","))
                durations.append(duration)
                next_line = lines[i + 1] if i + 1 < len(lines) else None
                if next_line and not next_line.startswith("#"):
                    segment_urls.append(next_line)

        if not segment_urls:
            raise ValueError("No media segments found in HLS playlist.")

        self.segment_duration = int(durations[0]) if durations else 6
        self.segment_timescale = 1  # HLS durations are already in seconds

        self.start_number = media_sequence
        self.end_number = media_sequence + len(segment_urls) - 1
        self.comparison_start_number = self.start_number

        # Try to detect media_template like 'segment-$Number$.ts'
        example_seg = segment_urls[0]
        number_match = re.search(r"(\d+)", example_seg)
        if number_match:
            seg_number = number_match.group(1)
            media_template = example_seg.replace(seg_number, "$Number$")
            self.media_template = media_template
        else:
            raise ValueError("Unable to infer segment numbering pattern in HLS.")

        # Store segment map (optional)
        self.segment_map = {
            self.start_number + i: urljoin(self.base_url, seg)
            for i, seg in enumerate(segment_urls)
        }

    def get_segment_url(self, number):
        # Use exact segment from map if available (for non-template HLS)
        if hasattr(self, "segment_map") and number in self.segment_map:
            return self.segment_map[number]
        return super().get_segment_url(number)
