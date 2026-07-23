#!/usr/bin/env python3
"""Deterministic, narrowly scoped MusicXML repairs for audited SATB sources."""

from __future__ import annotations

import copy
from dataclasses import dataclass
import xml.etree.ElementTree as ET


NORMALIZER_NAME = "open-hymnal-satb-normalizer"
NORMALIZER_VERSION = "1"
SPLIT_COMBINED_CHORD_VOICES = "split_combined_chord_voices"
DROP_EMPTY_PARTS = "drop_empty_parts"
ALIGN_MEASURE_NUMBERS = "align_measure_numbers"

_DOCTYPE = (
    '<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" '
    '"http://www.musicxml.org/dtds/partwise.dtd">'
)
_STEP_OFFSETS = {
    "C": 0,
    "D": 2,
    "E": 4,
    "F": 5,
    "G": 7,
    "A": 9,
    "B": 11,
}


class SatbNormalizationError(ValueError):
    """Raised when a score does not match a supported, lossless repair."""


@dataclass(frozen=True)
class NormalizationResult:
    data: bytes
    operations: tuple[str, ...]


@dataclass(frozen=True)
class _TimedNote:
    onset: int
    duration: int
    note: ET.Element
    in_primary_stream: bool


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _direct_child(element: ET.Element, name: str) -> ET.Element | None:
    return next(
        (child for child in element if _local_name(child.tag) == name),
        None,
    )


def _direct_children(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in element if _local_name(child.tag) == name]


def _required_int(element: ET.Element, child_name: str) -> int:
    child = _direct_child(element, child_name)
    if child is None or child.text is None:
        raise SatbNormalizationError(
            f"Expected {child_name!r} on {_local_name(element.tag)!r}."
        )
    return int(child.text)


def _timed_notes(measure: ET.Element) -> tuple[list[_TimedNote], int]:
    cursor = 0
    primary_extent = 0
    last_onset: int | None = None
    in_primary_stream = True
    result: list[_TimedNote] = []
    for child in measure:
        name = _local_name(child.tag)
        if name == "backup":
            duration = _required_int(child, "duration")
            if in_primary_stream:
                primary_extent = cursor
                in_primary_stream = False
            cursor -= duration
            last_onset = None
            continue
        if name == "forward":
            if in_primary_stream:
                raise SatbNormalizationError(
                    "Combined-voice normalization does not support forward elements."
                )
            cursor += _required_int(child, "duration")
            last_onset = None
            continue
        if name != "note":
            continue

        duration_element = _direct_child(child, "duration")
        if duration_element is None:
            raise SatbNormalizationError(
                "Combined-voice normalization does not support grace notes."
            )
        duration = int(duration_element.text or "0")
        is_chord = _direct_child(child, "chord") is not None
        if is_chord:
            if last_onset is None:
                raise SatbNormalizationError(
                    "Chord follower appeared without a leading note."
                )
            onset = last_onset
        else:
            onset = cursor
            last_onset = onset
            cursor += duration
        result.append(
            _TimedNote(
                onset=onset,
                duration=duration,
                note=child,
                in_primary_stream=in_primary_stream,
            )
        )
    if in_primary_stream:
        primary_extent = cursor
    return result, primary_extent


def _pitch_value(note: ET.Element) -> tuple[int, int]:
    pitch = _direct_child(note, "pitch")
    if pitch is None:
        raise SatbNormalizationError("Expected a pitched note.")
    step_element = _direct_child(pitch, "step")
    octave_element = _direct_child(pitch, "octave")
    if (
        step_element is None
        or step_element.text not in _STEP_OFFSETS
        or octave_element is None
        or octave_element.text is None
    ):
        raise SatbNormalizationError("Could not determine a note pitch.")
    alter_element = _direct_child(pitch, "alter")
    alter = int(alter_element.text or "0") if alter_element is not None else 0
    octave = int(octave_element.text)
    return (12 * octave + _STEP_OFFSETS[step_element.text] + alter, octave)


def _set_voice(note: ET.Element, value: str) -> None:
    voice = _direct_child(note, "voice")
    if voice is None:
        raise SatbNormalizationError("Expected every note to declare a voice.")
    voice.text = value


def _prepare_note(
    source: ET.Element,
    *,
    voice: str,
    lyrics: list[ET.Element],
) -> ET.Element:
    note = copy.deepcopy(source)
    for chord in _direct_children(note, "chord"):
        note.remove(chord)
    for lyric in _direct_children(note, "lyric"):
        note.remove(lyric)
    _set_voice(note, voice)
    stem = _direct_child(note, "stem")
    if stem is not None:
        stem.text = "up" if voice == "1" else "down"
    if voice == "1":
        note.extend(copy.deepcopy(lyrics))
    return note


def _voice_pair(notes: list[_TimedNote]) -> tuple[ET.Element, ET.Element]:
    pitched = [
        timed
        for timed in notes
        if _direct_child(timed.note, "pitch") is not None
    ]
    if pitched:
        if len(pitched) > 2:
            raise SatbNormalizationError(
                "An onset contains more than two pitches and is not an SATB dyad."
            )
        durations = {timed.duration for timed in pitched}
        if len(durations) != 1:
            raise SatbNormalizationError(
                "Simultaneous combined-voice pitches have different durations."
            )
        ordered = sorted(pitched, key=lambda timed: _pitch_value(timed.note))
        lower = ordered[0].note
        upper = ordered[-1].note
    else:
        rests = [
            timed
            for timed in notes
            if _direct_child(timed.note, "rest") is not None
        ]
        if not rests:
            raise SatbNormalizationError("An onset has neither a pitch nor a rest.")
        durations = {timed.duration for timed in rests}
        if len(durations) != 1:
            raise SatbNormalizationError(
                "Simultaneous combined-voice rests have different durations."
            )
        upper = lower = rests[0].note

    lyrics = [
        lyric
        for timed in notes
        for lyric in _direct_children(timed.note, "lyric")
    ]
    return (
        _prepare_note(upper, voice="1", lyrics=lyrics),
        _prepare_note(lower, voice="2", lyrics=[]),
    )


def _split_measure(measure: ET.Element) -> None:
    timed_notes, primary_extent = _timed_notes(measure)
    by_onset: dict[int, list[_TimedNote]] = {}
    primary_onsets: list[int] = []
    for timed in timed_notes:
        by_onset.setdefault(timed.onset, []).append(timed)
        if (
            timed.in_primary_stream
            and _direct_child(timed.note, "chord") is None
        ):
            primary_onsets.append(timed.onset)

    if not primary_onsets or set(primary_onsets) != set(by_onset):
        raise SatbNormalizationError(
            "Secondary voice events do not align with the combined primary stream."
        )

    pairs = {onset: _voice_pair(by_onset[onset]) for onset in primary_onsets}
    cursor = 0
    for onset in primary_onsets:
        upper = pairs[onset][0]
        duration = _required_int(upper, "duration")
        if onset != cursor:
            raise SatbNormalizationError(
                "Combined primary voice does not form a contiguous measure."
            )
        cursor += duration
    if cursor != primary_extent:
        raise SatbNormalizationError(
            "Combined primary voice duration does not match the measure extent."
        )

    original_children = list(measure)
    rebuilt: list[ET.Element] = []
    cursor = 0
    first_backup_seen = False
    inserted_lower = False
    last_primary_onset: int | None = None
    for child in original_children:
        name = _local_name(child.tag)
        if name == "backup":
            first_backup_seen = True
            if not inserted_lower:
                backup = copy.deepcopy(child)
                duration = _direct_child(backup, "duration")
                if duration is None:
                    raise SatbNormalizationError("Backup is missing its duration.")
                duration.text = str(primary_extent)
                rebuilt.append(backup)
                rebuilt.extend(pairs[onset][1] for onset in primary_onsets)
                inserted_lower = True
            continue
        if first_backup_seen and name in {"note", "forward"}:
            continue
        if name == "note":
            is_chord = _direct_child(child, "chord") is not None
            if is_chord:
                continue
            onset = cursor
            cursor += _required_int(child, "duration")
            last_primary_onset = onset
            rebuilt.append(pairs[onset][0])
            continue
        rebuilt.append(child)

    if last_primary_onset is None:
        raise SatbNormalizationError("Measure contains no primary notes.")
    if not inserted_lower:
        namespace = ""
        if "}" in measure.tag:
            namespace = measure.tag.split("}", 1)[0] + "}"
        backup = ET.Element(f"{namespace}backup")
        duration = ET.SubElement(backup, f"{namespace}duration")
        duration.text = str(primary_extent)
        insertion_index = max(
            index
            for index, child in enumerate(rebuilt)
            if _local_name(child.tag) == "note"
        ) + 1
        rebuilt[insertion_index:insertion_index] = [
            backup,
            *(pairs[onset][1] for onset in primary_onsets),
        ]

    measure[:] = rebuilt


def _split_combined_chord_voices(root: ET.Element) -> int:
    normalized_parts = 0
    for part in _direct_children(root, "part"):
        chord_count = sum(
            1
            for note in part.iter()
            if _local_name(note.tag) == "note"
            and _direct_child(note, "chord") is not None
        )
        if not chord_count:
            continue
        for measure in _direct_children(part, "measure"):
            _split_measure(measure)
        normalized_parts += 1
    if normalized_parts == 0:
        raise SatbNormalizationError(
            "Score contains no combined chord voices to split."
        )
    return normalized_parts


def _drop_empty_parts(root: ET.Element) -> int:
    empty_parts = [
        part
        for part in _direct_children(root, "part")
        if not any(_local_name(child.tag) == "note" for child in part.iter())
    ]
    if not empty_parts:
        raise SatbNormalizationError("Score contains no empty part.")
    part_list = _direct_child(root, "part-list")
    if part_list is None:
        raise SatbNormalizationError("Score is missing its part-list.")
    empty_ids = {part.get("id") for part in empty_parts}
    if None in empty_ids:
        raise SatbNormalizationError("Empty part is missing its ID.")
    for score_part in list(part_list):
        if (
            _local_name(score_part.tag) == "score-part"
            and score_part.get("id") in empty_ids
        ):
            part_list.remove(score_part)
    for part in empty_parts:
        root.remove(part)
    return len(empty_parts)


def _align_measure_numbers(root: ET.Element) -> int:
    parts = _direct_children(root, "part")
    if not parts:
        raise SatbNormalizationError("Score contains no parts.")
    reference_numbers = [
        measure.get("number")
        for measure in _direct_children(parts[0], "measure")
    ]
    if any(number is None for number in reference_numbers):
        raise SatbNormalizationError("Reference part has an unnumbered measure.")
    changes = 0
    for part in parts[1:]:
        measures = _direct_children(part, "measure")
        if len(measures) != len(reference_numbers):
            raise SatbNormalizationError(
                "Parts have different measure counts and cannot be aligned."
            )
        for measure, number in zip(measures, reference_numbers, strict=True):
            if measure.get("number") != number:
                measure.set("number", str(number))
                changes += 1
    return changes


def _serialize(root: ET.Element) -> bytes:
    ET.indent(root, space="  ")
    body = ET.tostring(root, encoding="unicode", short_empty_elements=True)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f"{_DOCTYPE}\n"
        f"{body}\n"
    ).encode("utf-8")


def normalize_satb_musicxml(data: bytes, operation: str) -> NormalizationResult:
    """Apply one audited SATB repair and return canonicalized MusicXML bytes."""
    root = ET.fromstring(data)
    if _local_name(root.tag) != "score-partwise":
        raise SatbNormalizationError("Expected score-partwise MusicXML.")
    if operation == SPLIT_COMBINED_CHORD_VOICES:
        _split_combined_chord_voices(root)
    elif operation == DROP_EMPTY_PARTS:
        _drop_empty_parts(root)
    else:
        raise SatbNormalizationError(f"Unknown SATB normalization {operation!r}.")
    operations = [operation]
    if _align_measure_numbers(root):
        operations.append(ALIGN_MEASURE_NUMBERS)
    return NormalizationResult(data=_serialize(root), operations=tuple(operations))
