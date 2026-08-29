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

today = datetime.date.today().isoformat()
new_text = f"{before}{marker}\n\n## [{version}] - {today}\n{body}\n{tail}"
path.write_text(new_text)
pathlib.Path("release_notes.md").write_text(body + "\n")
