from __future__ import annotations

from dataclasses import dataclass
import xml.etree.ElementTree as ET


@dataclass(frozen=True)
class MusicXMLValidation:
    valid: bool
    errors: list[dict[str, str]]
    warnings: list[dict[str, str]]
    stats: dict[str, object]


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _children(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in element if _local_name(child.tag) == name]


def _descendants(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in element.iter() if _local_name(child.tag) == name]


def _first_text(element: ET.Element, name: str) -> str:
    values = _children(element, name)
    if not values or values[0].text is None:
        return ""
    return values[0].text.strip()


def _problem(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def validate_musicxml(data: bytes) -> MusicXMLValidation:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    empty_stats: dict[str, object] = {
        "key_signatures": [],
        "lyric_elements": 0,
        "lyric_verse_ids": [],
        "measures": 0,
        "notes": 0,
        "parts": 0,
        "pitched_notes": 0,
        "rests": 0,
        "staves": 0,
        "time_signatures": [],
        "unpitched_notes": 0,
        "voices": 0,
    }
    if not data.strip():
        errors.append(_problem("empty_output", "Converter produced no MusicXML bytes."))
        return MusicXMLValidation(False, errors, warnings, empty_stats)

    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        errors.append(_problem("xml_parse_error", str(exc)))
        return MusicXMLValidation(False, errors, warnings, empty_stats)

    root_name = _local_name(root.tag)
    if root_name not in {"score-partwise", "score-timewise"}:
        errors.append(
            _problem(
                "unexpected_root",
                f"Expected score-partwise or score-timewise, found {root_name!r}.",
            )
        )

    if not _children(root, "part-list"):
        errors.append(_problem("missing_part_list", "MusicXML has no direct part-list element."))

    parts = _descendants(root, "part")
    measures = _descendants(root, "measure")
    notes = _descendants(root, "note")
    if not parts:
        errors.append(_problem("missing_parts", "MusicXML contains no part elements."))
    if not measures:
        errors.append(_problem("missing_measures", "MusicXML contains no measure elements."))
    if not notes:
        errors.append(_problem("missing_notes", "MusicXML contains no note elements."))

    pitched_notes = 0
    rests = 0
    unpitched_notes = 0
    lyric_elements = 0
    verse_ids: set[str] = set()
    voice_ids: set[tuple[str, str]] = set()
    invalid_payload_count = 0
    missing_duration_count = 0

    for part_index, part in enumerate(parts):
        part_id = part.get("id") or f"part-{part_index + 1}"
        for note in _descendants(part, "note"):
            has_pitch = bool(_children(note, "pitch"))
            has_rest = bool(_children(note, "rest"))
            has_unpitched = bool(_children(note, "unpitched"))
            if has_pitch:
                pitched_notes += 1
            elif has_rest:
                rests += 1
            elif has_unpitched:
                unpitched_notes += 1
            else:
                invalid_payload_count += 1

            if not _children(note, "grace") and not _children(note, "duration"):
                missing_duration_count += 1

            voice = _first_text(note, "voice")
            if voice:
                voice_ids.add((part_id, voice))
            for lyric in _children(note, "lyric"):
                lyric_elements += 1
                verse_id = lyric.get("number") or lyric.get("name")
                if verse_id:
                    verse_ids.add(verse_id)

    if invalid_payload_count:
        errors.append(
            _problem(
                "invalid_note_payload",
                f"{invalid_payload_count} note element(s) lack pitch, rest, or unpitched.",
            )
        )
    if missing_duration_count:
        errors.append(
            _problem(
                "missing_note_duration",
                f"{missing_duration_count} non-grace note element(s) lack duration.",
            )
        )

    staves_values: list[int] = []
    for staves in _descendants(root, "staves"):
        try:
            staves_values.append(int((staves.text or "").strip()))
        except ValueError:
            warnings.append(
                _problem("invalid_staves_value", f"Non-integer staves value: {staves.text!r}.")
            )
    if parts and not staves_values:
        staves_values = [1 for _ in parts]

    key_signatures: list[str] = []
    for key in _descendants(root, "key"):
        fifths = _first_text(key, "fifths")
        mode = _first_text(key, "mode")
        key_signatures.append(f"{fifths}:{mode}" if mode else fifths)

    time_signatures: list[str] = []
    for time in _descendants(root, "time"):
        beats = _first_text(time, "beats")
        beat_type = _first_text(time, "beat-type")
        time_signatures.append(f"{beats}/{beat_type}")

    stats = {
        "key_signatures": key_signatures,
        "lyric_elements": lyric_elements,
        "lyric_verse_ids": sorted(verse_ids),
        "measures": len(measures),
        "notes": len(notes),
        "parts": len(parts),
        "pitched_notes": pitched_notes,
        "rests": rests,
        "staves": sum(staves_values),
        "time_signatures": time_signatures,
        "unpitched_notes": unpitched_notes,
        "voices": len(voice_ids),
    }
    return MusicXMLValidation(not errors, errors, warnings, stats)

