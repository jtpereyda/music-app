#!/usr/bin/env python3
"""Deterministic, narrowly scoped MusicXML repairs for audited SATB sources."""

from __future__ import annotations

import copy
from collections import Counter
from dataclasses import dataclass
import re
import xml.etree.ElementTree as ET


NORMALIZER_NAME = "open-hymnal-satb-normalizer"
NORMALIZER_VERSION = "1"
TIMELESS_TRUTHS_NORMALIZER_NAME = "timeless-truths-satb-normalizer"
SPLIT_COMBINED_CHORD_VOICES = "split_combined_chord_voices"
DROP_EMPTY_PARTS = "drop_empty_parts"
ALIGN_MEASURE_NUMBERS = "align_measure_numbers"
NORMALIZE_SIBELIUS_LYRIC_ROWS = "normalize_sibelius_lyric_rows"
SPLIT_SIBELIUS_SATB_DYADS = "split_sibelius_satb_dyads"
SPLIT_SIBELIUS_MIXED_VOICES = "split_sibelius_mixed_voices"
SPLIT_SIBELIUS_MIXED_VOICES_WITH_CONTEXT = (
    "split_sibelius_mixed_voices_with_context"
)
SPLIT_SIBELIUS_DIVISI_VOICES_WITH_CONTEXT = (
    "split_sibelius_divisi_voices_with_context"
)
SPLIT_SIBELIUS_SHARED_RESTS_WITH_CONTEXT = (
    "split_sibelius_shared_rests_with_context"
)
SPLIT_SIBELIUS_HIDDEN_DUPLICATES_WITH_CONTEXT = (
    "split_sibelius_hidden_duplicates_with_context"
)
SPLIT_SIBELIUS_SIMULTANEOUS_OVERLAPS_WITH_CONTEXT = (
    "split_sibelius_simultaneous_overlaps_with_context"
)
SPLIT_SIBELIUS_VOICE2_PAIR_FALLBACK_WITH_CONTEXT = (
    "split_sibelius_voice2_pair_fallback_with_context"
)
SPLIT_SIBELIUS_EXTRA_VOICES_WITH_CONTEXT = (
    "split_sibelius_extra_voices_with_context"
)
STRIP_SOURCE_PAGE_CREDITS = "strip_source_page_credits"
DROP_NON_SOPRANO_LYRICS = "drop_non_soprano_lyrics"
SET_WORK_TITLE = "set_work_title"
SET_MODE_FROM_SOURCE_KEY_LABEL = "set_mode_from_source_key_label"

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
    profile: str = ""
    duplicated_unison_events: int = 0
    preserved_context_events: int = 0


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
        namespace = ""
        if "}" in note.tag:
            namespace = note.tag.split("}", 1)[0] + "}"
        voice = ET.Element(f"{namespace}voice")
        followers = {
            "accidental",
            "beam",
            "dot",
            "lyric",
            "notations",
            "notehead",
            "play",
            "staff",
            "stem",
            "time-modification",
            "type",
        }
        insertion_index = next(
            (
                index
                for index, child in enumerate(note)
                if _local_name(child.tag) in followers
            ),
            len(note),
        )
        note.insert(insertion_index, voice)
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


_SIBELIUS_LYRIC_ROW_TO_VERSE = {
    "-95": "1",
    "-120": "2",
    "-145": "3",
    "-170": "4",
    # The refrain is printed as a single shared lyric row.
    "-100": "1",
}


def _normalize_sibelius_lyric_rows(root: ET.Element) -> int:
    lyrics = [
        element
        for element in root.iter()
        if _local_name(element.tag) == "lyric"
    ]
    if not lyrics:
        raise SatbNormalizationError("Score contains no lyrics to normalize.")
    seen_verses: set[str] = set()
    for lyric in lyrics:
        source_number = lyric.get("number", "")
        row = lyric.get("default-y")
        verse = _SIBELIUS_LYRIC_ROW_TO_VERSE.get(row, "")
        match = re.fullmatch(r"part\d+verse(\d+)", source_number)
        if not verse and match:
            source_verse = int(match.group(1))
            verse = str(max(1, source_verse))
        if not verse:
            raise SatbNormalizationError(
                "Unexpected Sibelius lyric identifier "
                f"{source_number!r} at row {lyric.get('default-y')!r}."
            )
        lyric.set("number", verse)
        seen_verses.add(verse)
    if "1" not in seen_verses:
        raise SatbNormalizationError(
            f"Expected a first Sibelius lyric row, found {sorted(seen_verses)}."
        )
    return len(lyrics)


def _drop_non_soprano_lyrics(root: ET.Element) -> int:
    parts = _direct_children(root, "part")
    removed = 0
    for part in parts[1:]:
        for note in (
            element
            for element in part.iter()
            if _local_name(element.tag) == "note"
        ):
            for lyric in _direct_children(note, "lyric"):
                note.remove(lyric)
                removed += 1
    return removed


def _set_work_title(root: ET.Element, work_title: str) -> bool:
    work = _direct_child(root, "work")
    if work is None:
        namespace = ""
        if "}" in root.tag:
            namespace = root.tag.split("}", 1)[0] + "}"
        work = ET.Element(f"{namespace}work")
        root.insert(0, work)
    title = _direct_child(work, "work-title")
    if title is None:
        namespace = ""
        if "}" in work.tag:
            namespace = work.tag.split("}", 1)[0] + "}"
        title = ET.SubElement(work, f"{namespace}work-title")
    if (title.text or "") == work_title:
        return False
    title.text = work_title
    return True


def _set_mode_from_source_key_label(root: ET.Element, key_label: str) -> bool:
    mode = next(
        (element for element in root.iter() if _local_name(element.tag) == "mode"),
        None,
    )
    if mode is None:
        raise SatbNormalizationError("Score has no key mode element.")
    current = (mode.text or "").strip().casefold()
    if current in {"major", "minor"}:
        return False
    if current not in {"", "none"}:
        raise SatbNormalizationError(f"Unsupported source key mode {current!r}.")
    if not re.fullmatch(r"[A-G](?:♭|♯)?m?", key_label):
        raise SatbNormalizationError(
            f"Unsupported Timeless Truths key label {key_label!r}."
        )
    mode.text = "minor" if key_label.endswith("m") else "major"
    return True


def _hidden_rest(source: ET.Element, *, voice: str, duration: int) -> ET.Element:
    namespace = ""
    if "}" in source.tag:
        namespace = source.tag.split("}", 1)[0] + "}"
    note = ET.Element(f"{namespace}note", {"print-object": "no"})
    ET.SubElement(note, f"{namespace}rest")
    duration_element = ET.SubElement(note, f"{namespace}duration")
    duration_element.text = str(duration)
    voice_element = ET.SubElement(note, f"{namespace}voice")
    voice_element.text = voice
    staff = _direct_child(source, "staff")
    if staff is not None:
        note.append(copy.deepcopy(staff))
    return note


def _filled_voice_events(
    events: list[tuple[int, ET.Element]],
    *,
    extent: int,
    voice: str,
) -> list[ET.Element]:
    result: list[ET.Element] = []
    cursor = 0
    for onset, note in events:
        if onset < cursor:
            raise SatbNormalizationError(
                f"Sibelius voice {voice} contains overlapping notes."
            )
        if onset > cursor:
            result.append(
                _hidden_rest(note, voice=voice, duration=onset - cursor)
            )
        result.append(note)
        cursor = onset + _required_int(note, "duration")
    if not result:
        raise SatbNormalizationError(f"Sibelius voice {voice} is empty.")
    if cursor > extent:
        raise SatbNormalizationError(
            f"Sibelius voice {voice} exceeds its measure."
        )
    if cursor < extent:
        result.append(
            _hidden_rest(result[-1], voice=voice, duration=extent - cursor)
        )
    return result


def _remove_slurs(note: ET.Element) -> None:
    for notations in _direct_children(note, "notations"):
        for child in list(notations):
            if _local_name(child.tag) == "slur":
                notations.remove(child)
        if not list(notations):
            note.remove(notations)


def _append_slur(note: ET.Element, slur: ET.Element) -> None:
    notations = _direct_child(note, "notations")
    if notations is None:
        namespace = ""
        if "}" in note.tag:
            namespace = note.tag.split("}", 1)[0] + "}"
        notations = ET.Element(f"{namespace}notations")
        insertion_index = next(
            (
                index
                for index, child in enumerate(note)
                if _local_name(child.tag) in {"lyric", "play"}
            ),
            len(note),
        )
        note.insert(insertion_index, notations)
    notations.append(copy.deepcopy(slur))


def _split_sibelius_measure(measure: ET.Element) -> None:
    timed_notes, extent = _timed_notes(measure)
    by_onset: dict[int, list[_TimedNote]] = {}
    for timed in timed_notes:
        by_onset.setdefault(timed.onset, []).append(timed)
    if not by_onset or min(by_onset) != 0:
        raise SatbNormalizationError(
            "Sibelius SATB dyads must begin at the start of each measure."
        )

    upper_events: list[tuple[int, ET.Element]] = []
    lower_events: list[tuple[int, ET.Element]] = []
    for onset in sorted(by_onset):
        group = by_onset[onset]
        pitched = [
            timed
            for timed in group
            if _direct_child(timed.note, "pitch") is not None
        ]
        if len(pitched) != 2:
            raise SatbNormalizationError(
                "Each Sibelius SATB onset must contain exactly two pitches."
            )
        ordered = sorted(pitched, key=lambda timed: _pitch_value(timed.note))
        lower_source = ordered[0].note
        upper_source = ordered[-1].note
        lyrics = [
            lyric
            for timed in group
            for lyric in _direct_children(timed.note, "lyric")
        ]
        slurs = [
            slur
            for timed in group
            for notations in _direct_children(timed.note, "notations")
            for slur in _direct_children(notations, "slur")
        ]
        upper_note = _prepare_note(upper_source, voice="1", lyrics=lyrics)
        lower_note = _prepare_note(lower_source, voice="2", lyrics=[])
        _remove_slurs(upper_note)
        _remove_slurs(lower_note)
        for slur in slurs:
            orientation = slur.get("orientation")
            if orientation == "over":
                _append_slur(upper_note, slur)
            elif orientation == "under":
                _append_slur(lower_note, slur)
            else:
                raise SatbNormalizationError(
                    "Sibelius slur is missing an over/under orientation."
                )
        upper_events.append(
            (
                onset,
                upper_note,
            )
        )
        lower_events.append(
            (
                onset,
                lower_note,
            )
        )

    upper = _filled_voice_events(upper_events, extent=extent, voice="1")
    lower = _filled_voice_events(lower_events, extent=extent, voice="2")
    stream_names = {"backup", "forward", "note"}
    stream_indices = [
        index
        for index, child in enumerate(measure)
        if _local_name(child.tag) in stream_names
    ]
    if not stream_indices:
        raise SatbNormalizationError("Sibelius measure contains no note stream.")
    first, last = min(stream_indices), max(stream_indices)
    intervening = [
        child
        for child in list(measure)[first : last + 1]
        if _local_name(child.tag) not in stream_names
    ]
    if intervening:
        raise SatbNormalizationError(
            "Sibelius measure interleaves unsupported notation with its voices."
        )

    namespace = ""
    if "}" in measure.tag:
        namespace = measure.tag.split("}", 1)[0] + "}"
    backup = ET.Element(f"{namespace}backup")
    backup_duration = ET.SubElement(backup, f"{namespace}duration")
    backup_duration.text = str(extent)
    children = list(measure)
    measure[:] = [
        *children[:first],
        *upper,
        backup,
        *lower,
        *children[last + 1 :],
    ]


def _split_sibelius_satb_dyads(root: ET.Element) -> int:
    parts = _direct_children(root, "part")
    if len(parts) != 2:
        raise SatbNormalizationError(
            f"Expected two Sibelius SATB parts, found {len(parts)}."
        )
    for part in parts:
        measures = _direct_children(part, "measure")
        if not measures:
            raise SatbNormalizationError("Sibelius SATB part has no measures.")
        for measure in measures:
            _split_sibelius_measure(measure)
    return len(parts)


def _timed_note_groups(measure: ET.Element) -> tuple[list[list[_TimedNote]], int]:
    timed_notes, extent = _timed_notes(measure)
    groups: list[list[_TimedNote]] = []
    current: list[_TimedNote] = []
    for timed in timed_notes:
        if _direct_child(timed.note, "chord") is None:
            if current:
                groups.append(current)
            current = [timed]
        elif not current:
            raise SatbNormalizationError(
                "Sibelius chord follower appeared without a leading note."
            )
        else:
            current.append(timed)
    if current:
        groups.append(current)
    return groups, extent


def _group_voice(group: list[_TimedNote]) -> str:
    explicit = {
        (_direct_child(timed.note, "voice").text or "").strip()
        for timed in group
        if _direct_child(timed.note, "voice") is not None
    }
    explicit.discard("")
    if len(explicit) > 1:
        raise SatbNormalizationError(
            f"Sibelius chord group mixes source voices {sorted(explicit)}."
        )
    return next(iter(explicit), "1")


def _event_overlaps(
    events: list[tuple[int, ET.Element]],
    *,
    onset: int,
    duration: int,
) -> bool:
    end = onset + duration
    return any(
        event_onset < end
        and event_onset + _required_int(note, "duration") > onset
        for event_onset, note in events
    )


def _append_oriented_slurs(
    *,
    sources: list[ET.Element],
    upper: ET.Element | None,
    lower: ET.Element | None,
) -> None:
    slurs = [
        slur
        for source in sources
        for notations in _direct_children(source, "notations")
        for slur in _direct_children(notations, "slur")
    ]
    for note in (upper, lower):
        if note is not None:
            _remove_slurs(note)
    for slur in slurs:
        orientation = slur.get("orientation")
        if orientation == "over" and upper is not None:
            _append_slur(upper, slur)
        elif orientation == "under" and lower is not None:
            _append_slur(lower, slur)
        elif upper is not None and lower is None:
            _append_slur(upper, slur)
        elif lower is not None and upper is None:
            _append_slur(lower, slur)
        else:
            raise SatbNormalizationError(
                "Sibelius slur cannot be assigned to a semantic voice."
            )


def _mark_chord_follower(note: ET.Element) -> None:
    namespace = ""
    if "}" in note.tag:
        namespace = note.tag.split("}", 1)[0] + "}"
    chord = ET.Element(f"{namespace}chord")
    insertion_index = next(
        (
            index
            for index, child in enumerate(note)
            if _local_name(child.tag) in {"pitch", "unpitched", "rest"}
        ),
        0,
    )
    note.insert(insertion_index, chord)


def _expand_chord_followers(
    notes: list[ET.Element],
    followers: dict[int, list[ET.Element]],
) -> list[ET.Element]:
    result: list[ET.Element] = []

    def append(note: ET.Element) -> None:
        result.append(note)
        for follower in followers.get(id(note), []):
            append(follower)

    for note in notes:
        append(note)
    return result


def _merge_exact_hidden_duplicates(
    events: list[tuple[int, ET.Element]],
    followers: dict[int, list[ET.Element]],
) -> list[tuple[int, ET.Element]]:
    result: list[tuple[int, ET.Element]] = []
    by_event: dict[tuple[int, int, tuple[int, int]], ET.Element] = {}
    for onset, note in events:
        if _direct_child(note, "pitch") is None:
            result.append((onset, note))
            continue
        key = (onset, _required_int(note, "duration"), _pitch_value(note))
        existing = by_event.get(key)
        if existing is None:
            by_event[key] = note
            result.append((onset, note))
            continue
        hidden = note if note.get("print-object") == "no" else existing
        visible = existing if hidden is note else note
        if hidden.get("print-object") != "no" or visible.get("print-object") == "no":
            result.append((onset, note))
            continue
        if visible is note:
            result.remove((onset, existing))
            result.append((onset, visible))
            by_event[key] = visible
        _mark_chord_follower(hidden)
        followers.setdefault(id(visible), []).append(hidden)
    return result


def _merge_simultaneous_overlaps(
    events: list[tuple[int, ET.Element]],
    followers: dict[int, list[ET.Element]],
) -> list[tuple[int, ET.Element]]:
    result: list[tuple[int, ET.Element]] = []
    lead_onset: int | None = None
    lead: ET.Element | None = None
    lead_end = 0
    for onset, note in sorted(events, key=lambda event: event[0]):
        if onset < lead_end:
            if onset != lead_onset or lead is None:
                result.append((onset, note))
                continue
            _mark_chord_follower(note)
            followers.setdefault(id(lead), []).append(note)
            continue
        result.append((onset, note))
        lead_onset = onset
        lead = note
        lead_end = onset + _required_int(note, "duration")
    return result


def _assert_non_overlapping_events(
    events: list[tuple[int, ET.Element]],
    *,
    voice: str,
) -> None:
    cursor = 0
    for onset, note in sorted(events, key=lambda event: event[0]):
        if onset < cursor:
            raise SatbNormalizationError(
                f"Sibelius semantic voice {voice} contains overlapping notes."
            )
        cursor = onset + _required_int(note, "duration")


def _interleaved_stream_context(
    measure: ET.Element,
    *,
    extent: int,
) -> tuple[
    int,
    int,
    list[tuple[int, ET.Element]],
    list[tuple[int, ET.Element]],
]:
    """Locate supported notation embedded in the two serialized note streams."""
    stream_names = {"backup", "forward", "note"}
    stream_indices = [
        index
        for index, child in enumerate(measure)
        if _local_name(child.tag) in stream_names
    ]
    if not stream_indices:
        raise SatbNormalizationError("Sibelius measure contains no note stream.")
    first, last = min(stream_indices), max(stream_indices)
    cursor = 0
    in_primary_stream = True
    upper_context: list[tuple[int, ET.Element]] = []
    lower_context: list[tuple[int, ET.Element]] = []
    for child in list(measure)[first : last + 1]:
        name = _local_name(child.tag)
        if name == "backup":
            cursor -= _required_int(child, "duration")
            in_primary_stream = False
        elif name == "forward":
            cursor += _required_int(child, "duration")
        elif name == "note":
            if _direct_child(child, "chord") is None:
                cursor += _required_int(child, "duration")
        else:
            if name not in {"barline", "direction"}:
                raise SatbNormalizationError(
                    "Sibelius measure interleaves unsupported "
                    f"{name!r} notation with its voices."
                )
            if not 0 <= cursor <= extent:
                raise SatbNormalizationError(
                    "Sibelius interleaved notation falls outside its measure."
                )
            target = upper_context if in_primary_stream else lower_context
            target.append((cursor, child))
    return first, last, upper_context, lower_context


def _merge_stream_context(
    notes: list[ET.Element],
    context: list[tuple[int, ET.Element]],
    *,
    extent: int,
) -> list[ET.Element]:
    """Reinsert notation at the same serialized voice cursor."""
    result: list[ET.Element] = []
    context_index = 0
    cursor = 0
    for note in notes:
        while (
            context_index < len(context)
            and context[context_index][0] == cursor
        ):
            result.append(context[context_index][1])
            context_index += 1
        duration = (
            0
            if _direct_child(note, "chord") is not None
            else _required_int(note, "duration")
        )
        if (
            context_index < len(context)
            and cursor < context[context_index][0] < cursor + duration
        ):
            raise SatbNormalizationError(
                "Sibelius interleaved notation does not align with a "
                "normalized voice boundary."
            )
        result.append(note)
        cursor += duration
    if cursor != extent:
        raise SatbNormalizationError(
            "Sibelius normalized voice does not match its measure extent."
        )
    while context_index < len(context) and context[context_index][0] == extent:
        result.append(context[context_index][1])
        context_index += 1
    if context_index != len(context):
        raise SatbNormalizationError(
            "Sibelius interleaved notation could not be restored losslessly."
        )
    return result


def _split_sibelius_mixed_measure(
    measure: ET.Element,
    *,
    allow_divisi: bool = False,
    allow_extra_voices: bool = False,
    allow_hidden_duplicates: bool = False,
    allow_shared_rests: bool = False,
    allow_simultaneous_overlaps: bool = False,
    allow_voice2_pair_fallback: bool = False,
    preserve_context: bool = False,
) -> None:
    groups, extent = _timed_note_groups(measure)
    if not groups:
        raise SatbNormalizationError("Sibelius measure contains no note groups.")

    upper_events: list[tuple[int, ET.Element]] = []
    lower_events: list[tuple[int, ET.Element]] = []
    upper_followers: dict[int, list[ET.Element]] = {}
    lower_followers: dict[int, list[ET.Element]] = {}
    upper_rests: list[tuple[int, ET.Element]] = []
    lower_rests: list[tuple[int, ET.Element]] = []
    pending_unisons: list[
        tuple[int, ET.Element, list[ET.Element], ET.Element]
    ] = []
    for group in groups:
        voice = _group_voice(group)
        pitched = [
            timed
            for timed in group
            if _direct_child(timed.note, "pitch") is not None
        ]
        rests = [
            timed
            for timed in group
            if _direct_child(timed.note, "rest") is not None
        ]
        sources = [timed.note for timed in group]
        lyrics = [
            lyric
            for source in sources
            for lyric in _direct_children(source, "lyric")
        ]
        if voice == "1" and len(pitched) == 2:
            ordered = sorted(pitched, key=lambda timed: _pitch_value(timed.note))
            lower = _prepare_note(ordered[0].note, voice="2", lyrics=[])
            upper = _prepare_note(ordered[1].note, voice="1", lyrics=lyrics)
            _append_oriented_slurs(sources=sources, upper=upper, lower=lower)
            upper_events.append((pitched[0].onset, upper))
            lower_events.append((pitched[0].onset, lower))
        elif allow_divisi and voice == "1" and len(pitched) == 3:
            ordered = sorted(pitched, key=lambda timed: _pitch_value(timed.note))
            lower = _prepare_note(ordered[0].note, voice="2", lyrics=[])
            upper = _prepare_note(ordered[1].note, voice="1", lyrics=lyrics)
            follower = _prepare_note(ordered[2].note, voice="1", lyrics=[])
            _remove_slurs(follower)
            _mark_chord_follower(follower)
            _append_oriented_slurs(sources=sources, upper=upper, lower=lower)
            upper_events.append((pitched[0].onset, upper))
            lower_events.append((pitched[0].onset, lower))
            upper_followers[id(upper)] = [follower]
        elif allow_divisi and voice == "1" and len(pitched) == 4:
            ordered = sorted(pitched, key=lambda timed: _pitch_value(timed.note))
            lower = _prepare_note(ordered[0].note, voice="2", lyrics=[])
            upper = _prepare_note(ordered[1].note, voice="1", lyrics=lyrics)
            followers = [
                _prepare_note(timed.note, voice="1", lyrics=[])
                for timed in ordered[2:]
            ]
            for follower in followers:
                _remove_slurs(follower)
                _mark_chord_follower(follower)
            _append_oriented_slurs(sources=sources, upper=upper, lower=lower)
            upper_events.append((pitched[0].onset, upper))
            lower_events.append((pitched[0].onset, lower))
            upper_followers[id(upper)] = followers
        elif voice == "1" and len(pitched) == 1:
            source = pitched[0]
            upper = _prepare_note(source.note, voice="1", lyrics=lyrics)
            upper_events.append((source.onset, upper))
            pending_unisons.append((source.onset, source.note, sources, upper))
        elif voice == "1" and not pitched and rests:
            source = rests[0]
            upper = _prepare_note(source.note, voice="1", lyrics=lyrics)
            lower = (
                _prepare_note(source.note, voice="2", lyrics=[])
                if allow_shared_rests
                else None
            )
            _append_oriented_slurs(sources=sources, upper=upper, lower=lower)
            upper_rests.append((source.onset, upper))
            if lower is not None:
                lower_rests.append((source.onset, lower))
        elif voice == "2" and len(pitched) == 1:
            source = pitched[0]
            lower = _prepare_note(source.note, voice="2", lyrics=[])
            _append_oriented_slurs(sources=sources, upper=None, lower=lower)
            lower_events.append((source.onset, lower))
        elif allow_divisi and voice == "2" and len(pitched) == 2:
            ordered = sorted(pitched, key=lambda timed: _pitch_value(timed.note))
            lower = _prepare_note(ordered[0].note, voice="2", lyrics=[])
            follower = _prepare_note(ordered[1].note, voice="2", lyrics=[])
            _remove_slurs(follower)
            _mark_chord_follower(follower)
            _append_oriented_slurs(sources=sources, upper=None, lower=lower)
            lower_events.append((pitched[0].onset, lower))
            lower_followers[id(lower)] = [follower]
        elif voice == "2" and not pitched and rests:
            source = rests[0]
            lower = _prepare_note(source.note, voice="2", lyrics=[])
            _append_oriented_slurs(sources=sources, upper=None, lower=lower)
            lower_rests.append((source.onset, lower))
        elif allow_extra_voices and voice in {"3", "4"} and pitched:
            stems = {
                (_direct_child(timed.note, "stem").text or "").strip()
                for timed in pitched
                if _direct_child(timed.note, "stem") is not None
            }
            stems.discard("")
            target = ""
            if stems == {"up"}:
                target = "upper"
            elif stems == {"down"}:
                target = "lower"
            elif not stems and all(
                timed.note.get("print-object") == "no" for timed in pitched
            ):
                event = (
                    pitched[0].onset,
                    pitched[0].duration,
                    _pitch_value(pitched[0].note),
                )
                upper_match = any(
                    (
                        onset,
                        _required_int(note, "duration"),
                        _pitch_value(note),
                    )
                    == event
                    for onset, note in upper_events
                    if _direct_child(note, "pitch") is not None
                )
                lower_match = any(
                    (
                        onset,
                        _required_int(note, "duration"),
                        _pitch_value(note),
                    )
                    == event
                    for onset, note in lower_events
                    if _direct_child(note, "pitch") is not None
                )
                if upper_match != lower_match:
                    target = "upper" if upper_match else "lower"
            if not target:
                raise SatbNormalizationError(
                    f"Sibelius source voice {voice!r} cannot be assigned "
                    "from its stem direction."
                )
            ordered = sorted(pitched, key=lambda timed: _pitch_value(timed.note))
            semantic_voice = "1" if target == "upper" else "2"
            lead = _prepare_note(
                ordered[0].note,
                voice=semantic_voice,
                lyrics=lyrics if target == "upper" else [],
            )
            followers = [
                _prepare_note(timed.note, voice=semantic_voice, lyrics=[])
                for timed in ordered[1:]
            ]
            for follower in followers:
                _remove_slurs(follower)
                _mark_chord_follower(follower)
            _append_oriented_slurs(
                sources=sources,
                upper=lead if target == "upper" else None,
                lower=lead if target == "lower" else None,
            )
            target_events = upper_events if target == "upper" else lower_events
            target_followers = (
                upper_followers if target == "upper" else lower_followers
            )
            target_events.append((pitched[0].onset, lead))
            if followers:
                target_followers[id(lead)] = followers
        elif allow_extra_voices and voice in {"3", "4"} and rests:
            source = rests[0]
            target = "upper" if voice == "3" else "lower"
            rest = _prepare_note(
                source.note,
                voice="1" if target == "upper" else "2",
                lyrics=lyrics if target == "upper" else [],
            )
            _append_oriented_slurs(
                sources=sources,
                upper=rest if target == "upper" else None,
                lower=rest if target == "lower" else None,
            )
            (upper_rests if target == "upper" else lower_rests).append(
                (source.onset, rest)
            )
        elif pitched:
            raise SatbNormalizationError(
                f"Unsupported Sibelius source voice {voice!r} with "
                f"{len(pitched)} simultaneous pitches."
            )

    for onset, rest in upper_rests:
        duration = _required_int(rest, "duration")
        if not _event_overlaps(upper_events, onset=onset, duration=duration):
            upper_events.append((onset, rest))
    for onset, rest in lower_rests:
        duration = _required_int(rest, "duration")
        if not _event_overlaps(lower_events, onset=onset, duration=duration):
            lower_events.append((onset, rest))

    for onset, source, sources, upper in pending_unisons:
        duration = _required_int(source, "duration")
        if _event_overlaps(lower_events, onset=onset, duration=duration):
            _append_oriented_slurs(sources=sources, upper=upper, lower=None)
            continue
        lower = _prepare_note(source, voice="2", lyrics=[])
        _append_oriented_slurs(sources=sources, upper=upper, lower=lower)
        lower_events.append((onset, lower))

    if allow_voice2_pair_fallback and not upper_events and not upper_rests:
        for onset, lower in lower_events:
            followers = lower_followers.get(id(lower), [])
            if len(followers) != 1:
                continue
            upper = _prepare_note(followers[0], voice="1", lyrics=[])
            upper_events.append((onset, upper))
            lower_followers.pop(id(lower))

    upper_events.sort(key=lambda event: event[0])
    lower_events.sort(key=lambda event: event[0])
    if allow_hidden_duplicates:
        upper_events = _merge_exact_hidden_duplicates(
            upper_events,
            upper_followers,
        )
        lower_events = _merge_exact_hidden_duplicates(
            lower_events,
            lower_followers,
        )
    if allow_simultaneous_overlaps:
        upper_events = _merge_simultaneous_overlaps(
            upper_events,
            upper_followers,
        )
        lower_events = _merge_simultaneous_overlaps(
            lower_events,
            lower_followers,
        )
    _assert_non_overlapping_events(upper_events, voice="1")
    _assert_non_overlapping_events(lower_events, voice="2")
    upper = _filled_voice_events(upper_events, extent=extent, voice="1")
    lower = _filled_voice_events(lower_events, extent=extent, voice="2")
    upper = _expand_chord_followers(upper, upper_followers)
    lower = _expand_chord_followers(lower, lower_followers)

    first, last, upper_context, lower_context = _interleaved_stream_context(
        measure,
        extent=extent,
    )
    if not preserve_context and (upper_context or lower_context):
        raise SatbNormalizationError(
            "Sibelius measure interleaves notation with its mixed voices."
        )
    if preserve_context:
        upper = _merge_stream_context(upper, upper_context, extent=extent)
        lower = _merge_stream_context(lower, lower_context, extent=extent)
    namespace = ""
    if "}" in measure.tag:
        namespace = measure.tag.split("}", 1)[0] + "}"
    backup = ET.Element(f"{namespace}backup")
    ET.SubElement(backup, f"{namespace}duration").text = str(extent)
    children = list(measure)
    measure[:] = [
        *children[:first],
        *upper,
        backup,
        *lower,
        *children[last + 1 :],
    ]


def _split_sibelius_mixed_voices(root: ET.Element) -> int:
    parts = _direct_children(root, "part")
    if len(parts) != 2:
        raise SatbNormalizationError(
            f"Expected two Sibelius SATB parts, found {len(parts)}."
        )
    for part in parts:
        measures = _direct_children(part, "measure")
        if not measures:
            raise SatbNormalizationError("Sibelius SATB part has no measures.")
        for measure in measures:
            _split_sibelius_mixed_measure(measure)
    return len(parts)


def _split_sibelius_mixed_voices_with_context(root: ET.Element) -> int:
    parts = _direct_children(root, "part")
    if len(parts) != 2:
        raise SatbNormalizationError(
            f"Expected two Sibelius SATB parts, found {len(parts)}."
        )
    for part in parts:
        measures = _direct_children(part, "measure")
        if not measures:
            raise SatbNormalizationError("Sibelius SATB part has no measures.")
        for measure in measures:
            _split_sibelius_mixed_measure(measure, preserve_context=True)
    return len(parts)


def _split_sibelius_divisi_voices_with_context(root: ET.Element) -> int:
    parts = _direct_children(root, "part")
    if len(parts) != 2:
        raise SatbNormalizationError(
            f"Expected two Sibelius SATB parts, found {len(parts)}."
        )
    for part in parts:
        measures = _direct_children(part, "measure")
        if not measures:
            raise SatbNormalizationError("Sibelius SATB part has no measures.")
        for measure in measures:
            _split_sibelius_mixed_measure(
                measure,
                allow_divisi=True,
                preserve_context=True,
            )
    return len(parts)


def _split_sibelius_shared_rests_with_context(root: ET.Element) -> int:
    parts = _direct_children(root, "part")
    if len(parts) != 2:
        raise SatbNormalizationError(
            f"Expected two Sibelius SATB parts, found {len(parts)}."
        )
    for part in parts:
        measures = _direct_children(part, "measure")
        if not measures:
            raise SatbNormalizationError("Sibelius SATB part has no measures.")
        for measure in measures:
            _split_sibelius_mixed_measure(
                measure,
                allow_divisi=True,
                allow_shared_rests=True,
                preserve_context=True,
            )
    return len(parts)


def _split_sibelius_hidden_duplicates_with_context(root: ET.Element) -> int:
    parts = _direct_children(root, "part")
    if len(parts) != 2:
        raise SatbNormalizationError(
            f"Expected two Sibelius SATB parts, found {len(parts)}."
        )
    for part in parts:
        measures = _direct_children(part, "measure")
        if not measures:
            raise SatbNormalizationError("Sibelius SATB part has no measures.")
        for measure in measures:
            _split_sibelius_mixed_measure(
                measure,
                allow_divisi=True,
                allow_hidden_duplicates=True,
                allow_shared_rests=True,
                preserve_context=True,
            )
    return len(parts)


def _split_sibelius_simultaneous_overlaps_with_context(root: ET.Element) -> int:
    parts = _direct_children(root, "part")
    if len(parts) != 2:
        raise SatbNormalizationError(
            f"Expected two Sibelius SATB parts, found {len(parts)}."
        )
    for part in parts:
        measures = _direct_children(part, "measure")
        if not measures:
            raise SatbNormalizationError("Sibelius SATB part has no measures.")
        for measure in measures:
            _split_sibelius_mixed_measure(
                measure,
                allow_divisi=True,
                allow_hidden_duplicates=True,
                allow_shared_rests=True,
                allow_simultaneous_overlaps=True,
                preserve_context=True,
            )
    return len(parts)


def _split_sibelius_voice2_pair_fallback_with_context(root: ET.Element) -> int:
    parts = _direct_children(root, "part")
    if len(parts) != 2:
        raise SatbNormalizationError(
            f"Expected two Sibelius SATB parts, found {len(parts)}."
        )
    for part in parts:
        measures = _direct_children(part, "measure")
        if not measures:
            raise SatbNormalizationError("Sibelius SATB part has no measures.")
        for measure in measures:
            _split_sibelius_mixed_measure(
                measure,
                allow_divisi=True,
                allow_hidden_duplicates=True,
                allow_shared_rests=True,
                allow_simultaneous_overlaps=True,
                allow_voice2_pair_fallback=True,
                preserve_context=True,
            )
    return len(parts)


def _split_sibelius_extra_voices_with_context(root: ET.Element) -> int:
    parts = _direct_children(root, "part")
    if len(parts) != 2:
        raise SatbNormalizationError(
            f"Expected two Sibelius SATB parts, found {len(parts)}."
        )
    for part in parts:
        measures = _direct_children(part, "measure")
        if not measures:
            raise SatbNormalizationError("Sibelius SATB part has no measures.")
        for measure in measures:
            _split_sibelius_mixed_measure(
                measure,
                allow_divisi=True,
                allow_extra_voices=True,
                allow_hidden_duplicates=True,
                allow_shared_rests=True,
                allow_simultaneous_overlaps=True,
                allow_voice2_pair_fallback=True,
                preserve_context=True,
            )
    return len(parts)


def _element_signature(element: ET.Element) -> tuple[object, ...]:
    return (
        _local_name(element.tag),
        tuple(sorted(element.attrib.items())),
        element.text or "",
        tuple(_element_signature(child) for child in element),
    )


def _contextual_notation_events(
    root: ET.Element,
    *,
    include_trailing_barlines: bool = False,
) -> list[list[Counter[tuple[str, int, tuple[object, ...]]]]]:
    result: list[list[Counter[tuple[str, int, tuple[object, ...]]]]] = []
    for part in _direct_children(root, "part"):
        part_events: list[Counter[tuple[str, int, tuple[object, ...]]]] = []
        for measure in _direct_children(part, "measure"):
            _, extent = _timed_notes(measure)
            _, last, upper, lower = _interleaved_stream_context(
                measure,
                extent=extent,
            )
            events = Counter(
                (
                    "measure"
                    if _local_name(element.tag) == "barline" and onset == extent
                    else voice,
                    onset,
                    _element_signature(element),
                )
                for voice, contexts in (("1", upper), ("2", lower))
                for onset, element in contexts
            )
            if include_trailing_barlines:
                events.update(
                    (
                        "measure",
                        extent,
                        _element_signature(element),
                    )
                    for element in list(measure)[last + 1 :]
                    if _local_name(element.tag) == "barline"
                )
            part_events.append(events)
        result.append(part_events)
    return result


def _verify_contextual_notation_preservation(
    source_root: ET.Element,
    normalized_root: ET.Element,
) -> int:
    source = _contextual_notation_events(
        source_root,
        include_trailing_barlines=True,
    )
    normalized = _contextual_notation_events(
        normalized_root,
        include_trailing_barlines=True,
    )
    if source != normalized:
        raise SatbNormalizationError(
            "Timeless Truths normalization changed interleaved notation."
        )
    interleaved_source = _contextual_notation_events(source_root)
    return sum(
        sum(measure.values())
        for part in interleaved_source
        for measure in part
    )


def _pitched_measure_events(
    root: ET.Element,
) -> tuple[
    list[list[Counter[tuple[int, int, int]]]],
    list[list[int]],
]:
    part_events: list[list[Counter[tuple[int, int, int]]]] = []
    part_extents: list[list[int]] = []
    for part in _direct_children(root, "part"):
        measure_events: list[Counter[tuple[int, int, int]]] = []
        measure_extents: list[int] = []
        for measure in _direct_children(part, "measure"):
            timed_notes, extent = _timed_notes(measure)
            measure_extents.append(extent)
            measure_events.append(
                Counter(
                    (timed.onset, timed.duration, _pitch_value(timed.note)[0])
                    for timed in timed_notes
                    if _direct_child(timed.note, "pitch") is not None
                )
            )
        part_events.append(measure_events)
        part_extents.append(measure_extents)
    return part_events, part_extents


def _verify_pitched_event_preservation(
    source_root: ET.Element,
    normalized_root: ET.Element,
) -> int:
    source_events, source_extents = _pitched_measure_events(source_root)
    normalized_events, normalized_extents = _pitched_measure_events(
        normalized_root
    )
    if source_extents != normalized_extents:
        raise SatbNormalizationError(
            "Timeless Truths normalization changed a measure extent."
        )
    if [len(part) for part in source_events] != [
        len(part) for part in normalized_events
    ]:
        raise SatbNormalizationError(
            "Timeless Truths normalization changed the measure topology."
        )
    duplicated_unisons = 0
    for part_index, source_part in enumerate(source_events):
        for measure_index, source_measure in enumerate(source_part):
            normalized_measure = normalized_events[part_index][measure_index]
            if any(
                normalized_measure[event] < count
                for event, count in source_measure.items()
            ):
                raise SatbNormalizationError(
                    "Timeless Truths normalization lost a pitched event at "
                    f"part {part_index + 1}, measure {measure_index + 1}."
                )
            if any(event not in source_measure for event in normalized_measure):
                raise SatbNormalizationError(
                    "Timeless Truths normalization introduced a new pitch at "
                    f"part {part_index + 1}, measure {measure_index + 1}."
                )
            duplicated_unisons += sum(normalized_measure.values()) - sum(
                source_measure.values()
            )
    return duplicated_unisons


def _append_timeless_truths_encoder(root: ET.Element) -> None:
    encoding = next(
        (
            element
            for element in root.iter()
            if _local_name(element.tag) == "encoding"
        ),
        None,
    )
    if encoding is None:
        raise SatbNormalizationError("Score has no encoding metadata.")
    namespace = ""
    if "}" in encoding.tag:
        namespace = encoding.tag.split("}", 1)[0] + "}"
    software = ET.SubElement(encoding, f"{namespace}software")
    software.text = "Transposify Timeless Truths normalizer v1"


def _strip_source_page_credits(root: ET.Element) -> int:
    credits = _direct_children(root, "credit")
    if not credits:
        raise SatbNormalizationError("Score has no source page credits to strip.")
    for credit in credits:
        root.remove(credit)
    return len(credits)


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


def normalize_timeless_truths_musicxml(
    data: bytes,
    *,
    source_key_label: str | None = None,
    work_title: str | None = None,
) -> NormalizationResult:
    """Normalize the audited Timeless Truths Sibelius SATB export."""
    profiles = [
        (
            "split_aligned_satb_dyads",
            SPLIT_SIBELIUS_SATB_DYADS,
            _split_sibelius_satb_dyads,
        ),
        (
            "split_primary_dyads_with_secondary_voice",
            SPLIT_SIBELIUS_MIXED_VOICES,
            _split_sibelius_mixed_voices,
        ),
        (
            "split_mixed_voices_with_interleaved_notation",
            SPLIT_SIBELIUS_MIXED_VOICES_WITH_CONTEXT,
            _split_sibelius_mixed_voices_with_context,
        ),
        (
            "split_divisi_voices_with_interleaved_notation",
            SPLIT_SIBELIUS_DIVISI_VOICES_WITH_CONTEXT,
            _split_sibelius_divisi_voices_with_context,
        ),
        (
            "split_shared_rests_with_interleaved_notation",
            SPLIT_SIBELIUS_SHARED_RESTS_WITH_CONTEXT,
            _split_sibelius_shared_rests_with_context,
        ),
        (
            "split_hidden_duplicates_with_interleaved_notation",
            SPLIT_SIBELIUS_HIDDEN_DUPLICATES_WITH_CONTEXT,
            _split_sibelius_hidden_duplicates_with_context,
        ),
        (
            "split_simultaneous_overlaps_with_interleaved_notation",
            SPLIT_SIBELIUS_SIMULTANEOUS_OVERLAPS_WITH_CONTEXT,
            _split_sibelius_simultaneous_overlaps_with_context,
        ),
        (
            "split_voice2_pair_fallback_with_interleaved_notation",
            SPLIT_SIBELIUS_VOICE2_PAIR_FALLBACK_WITH_CONTEXT,
            _split_sibelius_voice2_pair_fallback_with_context,
        ),
        (
            "split_extra_stem_directed_voices_with_interleaved_notation",
            SPLIT_SIBELIUS_EXTRA_VOICES_WITH_CONTEXT,
            _split_sibelius_extra_voices_with_context,
        ),
    ]
    errors: list[str] = []
    for profile, split_operation, splitter in profiles:
        source_root = ET.fromstring(data)
        root = ET.fromstring(data)
        if _local_name(root.tag) != "score-partwise":
            raise SatbNormalizationError("Expected score-partwise MusicXML.")
        try:
            _normalize_sibelius_lyric_rows(root)
            dropped_lyrics = _drop_non_soprano_lyrics(root)
            splitter(root)
            _strip_source_page_credits(root)
            _append_timeless_truths_encoder(root)
            operations = [
                NORMALIZE_SIBELIUS_LYRIC_ROWS,
                split_operation,
                STRIP_SOURCE_PAGE_CREDITS,
            ]
            if dropped_lyrics:
                operations.insert(1, DROP_NON_SOPRANO_LYRICS)
            if (
                source_key_label is not None
                and _set_mode_from_source_key_label(root, source_key_label)
            ):
                operations.append(SET_MODE_FROM_SOURCE_KEY_LABEL)
            if work_title is not None and _set_work_title(root, work_title):
                operations.append(SET_WORK_TITLE)
            if _align_measure_numbers(root):
                operations.append(ALIGN_MEASURE_NUMBERS)
            duplicated_unisons = _verify_pitched_event_preservation(
                source_root,
                root,
            )
            preserved_context_events = _verify_contextual_notation_preservation(
                source_root,
                root,
            )
            return NormalizationResult(
                data=_serialize(root),
                operations=tuple(operations),
                profile=profile,
                duplicated_unison_events=duplicated_unisons,
                preserved_context_events=preserved_context_events,
            )
        except SatbNormalizationError as exc:
            errors.append(f"{profile}: {exc}")
    raise SatbNormalizationError("; ".join(errors))
