from __future__ import annotations

from pathlib import Path
import re
import sys


source = Path(sys.argv[-1]).read_text(encoding="utf-8")
reference_match = re.search(r"^X:\s*(.+?)\s*$", source, re.MULTILINE)
title_match = re.search(r"^T:\s*(.+?)\s*$", source, re.MULTILINE)
reference = reference_match.group(1) if reference_match else ""
title = title_match.group(1) if title_match else "Untitled"

if reference == "999":
    print("intentional fixture failure", file=sys.stderr)
    raise SystemExit(7)
if reference == "2":
    print("-- decoded from utf-8", file=sys.stderr)
    print("-- skipped I-field: newpage", file=sys.stderr)
    print("-- done in 0.01 secs", file=sys.stderr)

print(
    f"""<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <work><work-title>{title}</work-title></work>
  <part-list>
    <score-part id="P1"><part-name>Voice</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <key><fifths>0</fifths><mode>major</mode></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <staves>1</staves>
      </attributes>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>1</duration>
        <voice>1</voice>
        <lyric number="1"><syllabic>single</syllabic><text>{reference}</text></lyric>
      </note>
      <note>
        <rest/>
        <duration>3</duration>
        <voice>1</voice>
      </note>
    </measure>
  </part>
</score-partwise>"""
)
