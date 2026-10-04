import datetime
import pathlib
import sys

version = sys.argv[1]
path = pathlib.Path("CHANGELOG.md")
text = path.read_text()

marker = "## [Unreleased]"
if marker not in text:
    sys.exit(f"CHANGELOG.md has no '{marker}' section")

before, after = text.split(marker, 1)
# everything up to the next '## [' heading (or EOF) is this release's notes
rest = after.split("\n## [", 1)
body = rest[0].strip("\n")
tail = ("\n## [" + rest[1]) if len(rest) > 1 else ""

if not body.strip():
    sys.exit("Unreleased section is empty — nothing to release")

today = datetime.datetime.now(tz=datetime.UTC).date().isoformat()
if "b" in version:
    # Betas don't touch the changelog: notes accumulate in [Unreleased]
    # until the stable release, and each beta's notes are a snapshot of it.
    body = f"!PRE-RELEASE VERSION!\n\nChanges since the last stable release:\n\n{body}"
else:
    path.write_text(f"{before}{marker}\n\n## [{version}] - {today}\n{body}\n{tail}")

pathlib.Path("release_notes.md").write_text(body + "\n")
