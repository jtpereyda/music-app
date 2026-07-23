#!/usr/bin/env python3
"""Convert the audited HymnsToGod Mup SATB subset to canonical MusicXML.

Mup's MIDI output intentionally collapses ordinary ``s`` (space) groups, so
MIDI is useful for listening but is not a lossless notation interchange
format.  This converter instead reads Mup's expanded notation statements and
preserves their measure timing, pitch spelling, voice overlays, and primary
lyrics.  The official Mup executable is used only for macro expansion.

The supported profile is deliberately narrow:

* two five-line staves, with treble and bass default octaves;
* two voices per staff, expressed as a dyad/unison primary stream plus an
  optional second rhythmic stream;
* simple and dotted durations (no tuplets or grace notes);
* static key and time signatures; and
* the lyric constructs used by the audited HymnsToGod tranche.

Inputs outside that profile fail closed instead of being approximated.
"""

from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Iterable

from music21 import (
    bar,
    clef,
    key,
    metadata,
    meter,
    note,
    pitch,
    stream,
    tie,
)


CONVERTER_NAME = "hymns-to-god-mup-satb"
CONVERTER_VERSION = "1"
CANONICAL_ENCODING_DATE = "2026-07-22"

_MUSIC_ASSIGNMENT_RE = re.compile(
    r"^\s*([12])(?:\s+([12]))?\s*:\s*(.*?)\s*$"
)
_BAR_RE = re.compile(r"^\s*(bar|invisbar|dblbar|endbar)\b")
_DURATION_RE = re.compile(r"^(256|128|64|32|16|8|4|2|1)(\.*)")
_QUOTED_RE = re.compile(r'"((?:\\.|[^"\\])*)"')
_KEY_RE = re.compile(r"^\s*key\s*=\s*([^\s]+)", re.MULTILINE)
_TIME_RE = re.compile(r"^\s*time\s*=\s*([0-9]+/[0-9]+)", re.MULTILINE)
_TITLE_RE = re.compile(r"^\s*title\s+bold\b.*$", re.MULTILINE)
_FONT_ESCAPE_RE = re.compile(r"\\f\([^)]*\)")
_ANGLE_RE = re.compile(r"<[^>]*>")
_ALIGNMENT_RE = re.compile(r"^\s*[+-]?\d+(?:\.\d+)?\|")
_BRACKET_ATTRIBUTE_RE = re.compile(r"\[[^\]]*\]")

_KEY_FIFTHS = {
    "7&": -7,
    "6&": -6,
    "5&": -5,
    "4&": -4,
    "3&": -3,
    "2&": -2,
    "1&": -1,
    "c&": -7,
    "g&": -6,
    "d&": -5,
    "a&": -4,
    "e&": -3,
    "b&": -2,
    "f": -1,
    "c": 0,
    "0": 0,
    "1#": 1,
    "2#": 2,
    "3#": 3,
    "4#": 4,
    "5#": 5,
    "6#": 6,
    "7#": 7,
    "g": 1,
    "d": 2,
    "a": 3,
    "e": 4,
    "b": 5,
    "f#": 6,
    "c#": 7,
}
_NATURAL_SEMITONES = {
    "c": 0,
    "d": 2,
    "e": 4,
    "f": 5,
    "g": 7,
    "a": 9,
    "b": 11,
}


class MupConversionError(ValueError):
    """Raised when a source falls outside the audited conversion profile."""


@dataclass(frozen=True)
class ParsedPitch:
    step: str
    alter: int
    octave: int
    small: bool = False
    tie_to_next: bool = False

    @property
    def midi(self) -> int:
        return (
            12 * (self.octave + 1)
            + _NATURAL_SEMITONES[self.step]
            + self.alter
        )

    def to_music21(self) -> pitch.Pitch:
        value = pitch.Pitch()
        value.step = self.step.upper()
        value.octave = self.octave
        if self.alter:
            value.accidental = pitch.Accidental(self.alter)
        return value


@dataclass
class ParsedGroup:
    onset: Fraction
    duration: Fraction
    kind: str
    pitches: tuple[ParsedPitch, ...] = ()
    tie_to_next: bool = False
    lyric_continue: bool = False

    @property
    def end(self) -> Fraction:
        return self.onset + self.duration


@dataclass(frozen=True)
class ParsedLyric:
    header: str
    prefix: str
    text: str
    using_staff: int
    using_voice: int


@dataclass
class ParsedMeasure:
    assignments: dict[tuple[int, int], list[ParsedGroup]] = field(
        default_factory=dict
    )
    lyrics: list[ParsedLyric] = field(default_factory=list)
    bar_type: str = "bar"


@dataclass(frozen=True)
class SemanticEvent:
    onset: Fraction
    duration: Fraction
    value: ParsedPitch | None
    attack: bool
    tie_to_next: bool = False

    @property
    def end(self) -> Fraction:
        return self.onset + self.duration


@dataclass(frozen=True)
class LyricToken:
    text: str
    syllabic: str


@dataclass(frozen=True)
class ParsedScore:
    title: str
    time_signature: str
    fifths: int
    measures: tuple[ParsedMeasure, ...]


def _duration(value: str, dots: str) -> Fraction:
    base = Fraction(4, int(value))
    result = base
    addition = base
    for _ in dots:
        addition /= 2
        result += addition
    return result


def _measure_duration(time_signature: str) -> Fraction:
    numerator, denominator = (int(value) for value in time_signature.split("/"))
    return Fraction(numerator * 4, denominator)


def _quoted_strings(value: str) -> list[str]:
    return [match.group(1) for match in _QUOTED_RE.finditer(value)]


def _source_title(expanded: str) -> str:
    match = _TITLE_RE.search(expanded)
    if match is None:
        raise MupConversionError("Could not locate the bold score title.")
    values = [value for value in _quoted_strings(match.group(0)) if value]
    if len(values) != 1:
        raise MupConversionError("Expected one non-empty bold score title.")
    return _decode_mup_text(values[0])


def _key_accidentals(fifths: int) -> dict[str, int]:
    signature = key.KeySignature(fifths)
    result: dict[str, int] = {}
    for step in _NATURAL_SEMITONES:
        accidental = signature.accidentalByStep(step.upper())
        result[step] = 0 if accidental is None else int(accidental.alter)
    return result


def _accidental_value(symbols: str, fallback: int) -> int:
    if not symbols:
        return fallback
    # A printed accidental is absolute for the measure, not an increment
    # relative to the key signature. Combinations such as ``n#`` therefore
    # still resolve to a single sharp.
    value = 0
    index = 0
    while index < len(symbols):
        symbol = symbols[index]
        if symbol == "n":
            value = 0
        elif symbol == "#":
            value += 1
        elif symbol == "x":
            value += 2
        elif symbol == "&":
            if index + 1 < len(symbols) and symbols[index + 1] == "&":
                value -= 2
                index += 1
            else:
                value -= 1
        index += 1
    return value


def _parse_pitch_cluster(
    value: str,
    *,
    default_octave: int,
    key_accidentals: dict[str, int],
    measure_accidentals: dict[tuple[str, int], int],
) -> tuple[ParsedPitch, ...]:
    """Parse the compact Mup pitch cluster at the start of a group."""
    value = _BRACKET_ATTRIBUTE_RE.sub("", value).strip()
    if not value:
        return ()

    # Chord-wide attributes begin after whitespace. Individual note
    # attributes (small ``?``, tie ``~``, and slur targets ``<...>``) remain
    # in the compact cluster and are handled below.
    cluster = value.split(maxsplit=1)[0]
    result: list[ParsedPitch] = []
    index = 0
    while index < len(cluster):
        character = cluster[index].lower()
        if character in "()":
            index += 1
            continue
        if character not in _NATURAL_SEMITONES:
            # Slur destinations and note-shape attributes are notation-only.
            if character == "<":
                closing = cluster.find(">", index + 1)
                if closing == -1:
                    raise MupConversionError(
                        f"Unclosed note attribute in pitch cluster {cluster!r}."
                    )
                index = closing + 1
                continue
            if character in "?~":
                index += 1
                continue
            raise MupConversionError(
                f"Unsupported character {cluster[index]!r} in pitch cluster "
                f"{cluster!r}."
            )

        step = character
        index += 1
        accidental_symbols = ""
        octave_marks = ""
        small = False
        tied = False
        while index < len(cluster):
            character = cluster[index].lower()
            if character in _NATURAL_SEMITONES or character == "(":
                break
            if character in "#&xn":
                accidental_symbols += character
                index += 1
                continue
            if character in "+-" or character.isdigit():
                octave_marks += character
                index += 1
                continue
            if character == "?":
                small = True
                index += 1
                continue
            if character == "~":
                tied = True
                index += 1
                continue
            if character == "<":
                closing = cluster.find(">", index + 1)
                if closing == -1:
                    raise MupConversionError(
                        f"Unclosed note attribute in pitch cluster {cluster!r}."
                    )
                index = closing + 1
                continue
            if character == ")":
                index += 1
                continue
            raise MupConversionError(
                f"Unsupported character {cluster[index]!r} in pitch cluster "
                f"{cluster!r}."
            )

        if octave_marks.isdigit():
            octave = int(octave_marks)
        else:
            octave = (
                default_octave
                + octave_marks.count("+")
                - octave_marks.count("-")
            )
        accidental_key = (step, octave)
        fallback = measure_accidentals.get(
            accidental_key,
            key_accidentals[step],
        )
        alter = _accidental_value(accidental_symbols, fallback)
        if accidental_symbols:
            measure_accidentals[accidental_key] = alter
        result.append(
            ParsedPitch(
                step=step,
                alter=alter,
                octave=octave,
                small=small,
                tie_to_next=tied,
            )
        )
    return tuple(result)


def _parse_music_groups(
    body: str,
    *,
    default_duration: Fraction,
    default_octave: int,
    key_accidentals: dict[str, int],
    measure_accidentals: dict[tuple[str, int], int],
) -> list[ParsedGroup]:
    raw_groups = body.split(";")
    if raw_groups and not raw_groups[-1].strip():
        raw_groups.pop()
    if not raw_groups:
        raise MupConversionError("A music assignment contains no groups.")

    result: list[ParsedGroup] = []
    previous: ParsedGroup | None = None
    onset = Fraction(0)
    previous_duration: Fraction | None = None
    for raw in raw_groups:
        token = _BRACKET_ATTRIBUTE_RE.sub("", raw).strip()
        duration_match = _DURATION_RE.match(token)
        if duration_match:
            group_duration = _duration(
                duration_match.group(1),
                duration_match.group(2),
            )
            token = token[duration_match.end() :].strip()
        elif previous_duration is not None:
            group_duration = previous_duration
        else:
            group_duration = default_duration

        if not token:
            if previous is None:
                raise MupConversionError("The first group cannot be empty.")
            kind = previous.kind
            pitches = copy.deepcopy(previous.pitches)
        else:
            first = token[0].lower()
            if first == "r":
                kind = "rest"
                pitches = ()
            elif first in {"s", "u"} and (
                first == "s" or token.lower().startswith("us")
            ):
                kind = "space"
                pitches = ()
            elif first in _NATURAL_SEMITONES or first in "([":
                kind = "pitch"
                pitches = _parse_pitch_cluster(
                    token,
                    default_octave=default_octave,
                    key_accidentals=key_accidentals,
                    measure_accidentals=measure_accidentals,
                )
                if not pitches:
                    raise MupConversionError(
                        f"Could not parse pitches from group {raw!r}."
                    )
            else:
                # A duration-only group can include chord-wide modifiers.
                modifier_words = token.lower().split()
                if previous is not None and set(modifier_words) <= {
                    "tie",
                    "slur",
                    "dotted",
                    "dashed",
                    "up",
                    "down",
                }:
                    kind = previous.kind
                    pitches = copy.deepcopy(previous.pitches)
                else:
                    raise MupConversionError(
                        f"Unsupported music group {raw!r}."
                    )

        lower_token = token.lower()
        tie_to_next = bool(re.search(r"(?:^|\s)tie(?:\s|$)", lower_token))
        tie_to_next = tie_to_next or any(value.tie_to_next for value in pitches)
        lyric_continue = tie_to_next or bool(
            re.search(r"(?:^|\s)slur(?:\s|$)", lower_token)
        )
        group = ParsedGroup(
            onset=onset,
            duration=group_duration,
            kind=kind,
            pitches=pitches,
            tie_to_next=tie_to_next,
            lyric_continue=lyric_continue,
        )
        result.append(group)
        previous = group
        previous_duration = group_duration
        onset += group_duration
    return result


def _parse_lyric(line: str) -> ParsedLyric:
    before_colon, after_colon = line.split(":", 1)
    strings = _quoted_strings(after_colon)
    if not strings:
        raise MupConversionError(f"Lyric line has no text string: {line!r}.")
    quoted_match = _QUOTED_RE.search(after_colon)
    if quoted_match is None:
        raise MupConversionError(f"Could not locate lyric text: {line!r}.")
    prefix = after_colon[: quoted_match.start()].strip()
    prefix = re.sub(r"^\[[^\]]+\]\s*", "", prefix)
    using = re.search(r"\busing\s+([12])(?:\s+([12]))?", before_colon)
    using_staff = int(using.group(1)) if using else 1
    using_voice = int(using.group(2) or "1") if using else 1
    normalized_header = " ".join(before_colon.split())
    return ParsedLyric(
        header=normalized_header,
        prefix=prefix,
        text=strings[0],
        using_staff=using_staff,
        using_voice=using_voice,
    )


def parse_expanded_mup(expanded: str) -> ParsedScore:
    time_match = _TIME_RE.search(expanded)
    key_match = _KEY_RE.search(expanded)
    if time_match is None or key_match is None:
        raise MupConversionError("Source must declare a time and key signature.")
    time_signature = time_match.group(1).lower()
    key_token = key_match.group(1).lower()
    if key_token not in _KEY_FIFTHS:
        raise MupConversionError(f"Unsupported key declaration {key_token!r}.")
    fifths = _KEY_FIFTHS[key_token]
    measure_extent = _measure_duration(time_signature)
    signature_accidentals = _key_accidentals(fifths)

    music_marker = re.search(r"^\s*music\s*$", expanded, re.MULTILINE)
    if music_marker is None:
        raise MupConversionError("Source has no music context.")
    music_text = expanded[music_marker.end() :]

    measures: list[ParsedMeasure] = []
    assignments: dict[tuple[int, int], list[ParsedGroup]] = {}
    lyrics: list[ParsedLyric] = []
    accidental_state = {1: {}, 2: {}}
    for raw_line in music_text.splitlines():
        line = raw_line.split("//", 1)[0].strip()
        if not line:
            continue
        assignment_match = _MUSIC_ASSIGNMENT_RE.match(line)
        if assignment_match:
            staff_number = int(assignment_match.group(1))
            voice_number = int(assignment_match.group(2) or "1")
            assignment_key = (staff_number, voice_number)
            if assignment_key in assignments:
                raise MupConversionError(
                    f"Duplicate staff/voice assignment in one measure: "
                    f"{assignment_key}."
                )
            groups = _parse_music_groups(
                assignment_match.group(3),
                default_duration=Fraction(
                    4,
                    int(time_signature.split("/", 1)[1]),
                ),
                default_octave=4 if staff_number == 1 else 3,
                key_accidentals=signature_accidentals,
                measure_accidentals=accidental_state[staff_number],
            )
            extent = sum((group.duration for group in groups), Fraction(0))
            if extent != measure_extent:
                raise MupConversionError(
                    f"Staff {staff_number} voice {voice_number} has duration "
                    f"{extent}, expected {measure_extent}."
                )
            assignments[assignment_key] = groups
            continue
        if line.startswith("lyrics between"):
            lyrics.append(_parse_lyric(line))
            continue
        bar_match = _BAR_RE.match(line)
        if bar_match:
            if not assignments:
                raise MupConversionError("A barline appeared before any music.")
            measures.append(
                ParsedMeasure(
                    assignments=assignments,
                    lyrics=lyrics,
                    bar_type=bar_match.group(1),
                )
            )
            assignments = {}
            lyrics = []
            accidental_state = {1: {}, 2: {}}
            continue

    if assignments or lyrics:
        raise MupConversionError("Source ended without a terminating barline.")
    if not measures:
        raise MupConversionError("Source contains no complete measures.")
    return ParsedScore(
        title=_source_title(expanded),
        time_signature=time_signature,
        fifths=fifths,
        measures=tuple(measures),
    )


def _group_at(groups: list[ParsedGroup] | None, point: Fraction) -> ParsedGroup | None:
    if groups is None:
        return None
    return next((group for group in groups if group.onset <= point < group.end), None)


def _audible_pitches(group: ParsedGroup) -> list[ParsedPitch]:
    return sorted(
        (value for value in group.pitches if not value.small),
        key=lambda value: value.midi,
    )


def _semantic_voices(
    measure: ParsedMeasure,
    staff_number: int,
    measure_extent: Fraction,
) -> tuple[list[SemanticEvent], list[SemanticEvent]]:
    primary = measure.assignments.get((staff_number, 1))
    if primary is None:
        raise MupConversionError(
            f"Measure omits primary voice on staff {staff_number}."
        )
    secondary = measure.assignments.get((staff_number, 2))
    boundaries = {Fraction(0), measure_extent}
    for groups in (primary, secondary or []):
        for group in groups:
            boundaries.add(group.onset)
            boundaries.add(group.end)
    ordered = sorted(boundaries)

    upper_segments: list[SemanticEvent] = []
    lower_segments: list[SemanticEvent] = []
    for onset, end in zip(ordered, ordered[1:]):
        primary_group = _group_at(primary, onset)
        if primary_group is None:
            raise MupConversionError("Primary voice has a timing gap.")
        secondary_group = _group_at(secondary, onset)
        primary_values = _audible_pitches(primary_group)
        if len(primary_values) > 2:
            raise MupConversionError(
                f"Primary staff {staff_number} contains more than an SATB dyad."
            )
        if primary_group.kind == "pitch":
            if not primary_values:
                raise MupConversionError(
                    "A primary pitched group contains only cue-sized notes."
                )
            upper_value = primary_values[-1]
            lower_value = primary_values[0]
        else:
            upper_value = None
            lower_value = None

        secondary_supplies = (
            secondary_group is not None and secondary_group.kind != "space"
        )
        if secondary_supplies:
            secondary_values = _audible_pitches(secondary_group)
            if secondary_group.kind == "pitch":
                if len(secondary_values) != 1:
                    raise MupConversionError(
                        f"Secondary staff {staff_number} voice is not monophonic."
                    )
                lower_value = secondary_values[0]
            else:
                lower_value = None

        upper_attack = onset == primary_group.onset
        lower_source = secondary_group if secondary_supplies else primary_group
        lower_attack = onset == lower_source.onset
        duration = end - onset
        upper_segments.append(
            SemanticEvent(
                onset=onset,
                duration=duration,
                value=upper_value,
                attack=upper_attack,
                tie_to_next=(
                    primary_group.tie_to_next and end == primary_group.end
                ),
            )
        )
        lower_segments.append(
            SemanticEvent(
                onset=onset,
                duration=duration,
                value=lower_value,
                attack=lower_attack,
                tie_to_next=(
                    lower_source.tie_to_next and end == lower_source.end
                ),
            )
        )
    return (
        _merge_semantic_segments(upper_segments),
        _merge_semantic_segments(lower_segments),
    )


def _merge_semantic_segments(events: list[SemanticEvent]) -> list[SemanticEvent]:
    result: list[SemanticEvent] = []
    for event in events:
        if (
            result
            and not event.attack
            and result[-1].value == event.value
            and result[-1].end == event.onset
        ):
            previous = result.pop()
            result.append(
                SemanticEvent(
                    onset=previous.onset,
                    duration=previous.duration + event.duration,
                    value=previous.value,
                    attack=previous.attack,
                    tie_to_next=event.tie_to_next,
                )
            )
        else:
            result.append(event)
    return result


def _decode_mup_text(value: str) -> str:
    value = _FONT_ESCAPE_RE.sub("", value)
    value = value.replace(r"\(emdash)", "—")
    value = value.replace(r"\"", '"')
    value = value.replace(r"\(space)", " ")
    return value


def _lyric_tokens(value: str) -> list[LyricToken]:
    value = _decode_mup_text(value)
    value = _ANGLE_RE.sub("", value)
    value = _ALIGNMENT_RE.sub("", value)
    value = value.replace("~", "\ue000")
    result: list[LyricToken] = []
    for word in value.strip().split():
        pieces = [piece for piece in re.split(r"[-_]", word) if piece]
        if not pieces:
            continue
        for index, piece in enumerate(pieces):
            if len(pieces) == 1:
                syllabic = "single"
            elif index == 0:
                syllabic = "begin"
            elif index == len(pieces) - 1:
                syllabic = "end"
            else:
                syllabic = "middle"
            result.append(
                LyricToken(text=piece.replace("\ue000", " "), syllabic=syllabic)
            )
    return result


def _lyric_prefix_onsets(prefix: str) -> list[Fraction]:
    raw_groups = prefix.split(";")
    if raw_groups and not raw_groups[-1].strip():
        raw_groups.pop()
    result: list[Fraction] = []
    onset = Fraction(0)
    previous_duration: Fraction | None = None
    for raw in raw_groups:
        token = raw.strip()
        duration_match = _DURATION_RE.match(token)
        if duration_match:
            group_duration = _duration(
                duration_match.group(1),
                duration_match.group(2),
            )
            token = token[duration_match.end() :].strip()
        elif previous_duration is not None:
            group_duration = previous_duration
        else:
            raise MupConversionError(
                f"Lyric timing must begin with a duration: {prefix!r}."
            )
        if token.lower() != "s":
            result.append(onset)
        onset += group_duration
        previous_duration = group_duration
    return result


def _derived_lyric_onsets(
    measure: ParsedMeasure,
    lyric: ParsedLyric,
) -> list[Fraction]:
    if lyric.prefix:
        return _lyric_prefix_onsets(lyric.prefix)
    groups = measure.assignments.get((lyric.using_staff, lyric.using_voice))
    if groups is None:
        raise MupConversionError(
            f"Lyrics derive from missing staff {lyric.using_staff} "
            f"voice {lyric.using_voice}."
        )
    result: list[Fraction] = []
    previous_continues = False
    for group in groups:
        if group.kind == "pitch" and not previous_continues:
            result.append(group.onset)
        previous_continues = group.lyric_continue
    return result


def _primary_lyrics(
    measure: ParsedMeasure,
) -> list[tuple[str, list[tuple[Fraction, LyricToken]]]]:
    """Return the first between-staves lyric layer and its verses."""
    if not measure.lyrics:
        return []
    header = measure.lyrics[0].header
    prefix = measure.lyrics[0].prefix
    selected = [
        value
        for value in measure.lyrics
        if value.header == header and value.prefix == prefix
    ]
    result: list[tuple[str, list[tuple[Fraction, LyricToken]]]] = []
    for verse_index, lyric in enumerate(selected, start=1):
        tokens = _lyric_tokens(lyric.text)
        onsets = _derived_lyric_onsets(measure, lyric)
        if len(tokens) != len(onsets):
            raise MupConversionError(
                f"Lyric syllable/timing mismatch for {lyric.text!r}: "
                f"{len(tokens)} syllables and {len(onsets)} note positions."
            )
        result.append(
            (
                str(verse_index),
                list(zip(onsets, tokens)),
            )
        )
    return result


def _music21_voice(
    events: list[SemanticEvent],
    *,
    voice_id: str,
) -> tuple[stream.Voice, dict[Fraction, note.Note]]:
    result = stream.Voice(id=voice_id)
    notes_by_onset: dict[Fraction, note.Note] = {}
    created: list[note.NotRest] = []
    for event in events:
        quarter_length = float(event.duration)
        if event.value is None:
            element: note.NotRest = note.Rest(quarterLength=quarter_length)
        else:
            element = note.Note(
                event.value.to_music21(),
                quarterLength=quarter_length,
            )
            notes_by_onset[event.onset] = element
        result.insert(float(event.onset), element)
        created.append(element)

    for index, event in enumerate(events[:-1]):
        following = events[index + 1]
        if (
            event.tie_to_next
            and event.value is not None
            and following.value == event.value
            and isinstance(created[index], note.Note)
            and isinstance(created[index + 1], note.Note)
        ):
            created[index].tie = tie.Tie("start")
            created[index + 1].tie = tie.Tie("stop")
    return result, notes_by_onset


def score_to_music21(
    parsed: ParsedScore,
    *,
    lyricist: str | None = None,
    composer: str | None = None,
) -> stream.Score:
    result = stream.Score()
    result.metadata = metadata.Metadata()
    result.metadata.title = parsed.title
    if lyricist:
        result.metadata.lyricist = lyricist
    if composer:
        result.metadata.composer = composer

    measure_extent = _measure_duration(parsed.time_signature)
    parts = [stream.Part(id="P1"), stream.Part(id="P2")]
    parts[0].partName = "Soprano and Alto"
    parts[1].partName = "Tenor and Bass"
    for measure_index, parsed_measure in enumerate(parsed.measures, start=1):
        for staff_index, part in enumerate(parts, start=1):
            music_measure = stream.Measure(number=measure_index)
            if measure_index == 1:
                music_measure.insert(
                    0,
                    clef.TrebleClef() if staff_index == 1 else clef.BassClef(),
                )
                music_measure.insert(
                    0,
                    key.KeySignature(parsed.fifths).asKey("major"),
                )
                music_measure.insert(0, meter.TimeSignature(parsed.time_signature))
            upper_events, lower_events = _semantic_voices(
                parsed_measure,
                staff_index,
                measure_extent,
            )
            upper, upper_notes = _music21_voice(upper_events, voice_id="1")
            lower, _ = _music21_voice(lower_events, voice_id="2")
            if staff_index == 1:
                for verse_id, values in _primary_lyrics(parsed_measure):
                    for onset, lyric_token in values:
                        target = upper_notes.get(onset)
                        if target is None:
                            raise MupConversionError(
                                f"Lyric onset {onset} has no soprano attack in "
                                f"measure {measure_index}."
                            )
                        target.addLyric(
                            lyric_token.text,
                            lyricNumber=int(verse_id),
                        )
                        added = target.lyrics[-1]
                        added.syllabic = lyric_token.syllabic
            music_measure.insert(0, upper)
            music_measure.insert(0, lower)
            if parsed_measure.bar_type == "dblbar":
                music_measure.rightBarline = bar.Barline("double")
            elif parsed_measure.bar_type == "endbar":
                music_measure.rightBarline = bar.Barline("final")
            parts[staff_index - 1].append(music_measure)
    for part in parts:
        result.append(part)
    return result


def expand_mup(source_path: Path, mup_executable: Path) -> str:
    completed = subprocess.run(
        [str(mup_executable), "-q", "-E", str(source_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise MupConversionError(
            f"Mup macro expansion failed for {source_path}: "
            f"{completed.stderr.strip()}"
        )
    return completed.stdout


def convert_source(
    *,
    source_path: Path,
    output_path: Path,
    mup_executable: Path,
    lyricist: str | None = None,
    composer: str | None = None,
    expected_title: str | None = None,
) -> None:
    parsed = parse_expanded_mup(expand_mup(source_path, mup_executable))
    if expected_title is not None and parsed.title != expected_title:
        raise MupConversionError(
            f"Expanded title {parsed.title!r} does not match "
            f"{expected_title!r}."
        )
    score = score_to_music21(
        parsed,
        lyricist=lyricist,
        composer=composer,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="hymns-to-god-mup-") as directory:
        generated = Path(directory) / "score.musicxml"
        score.write("musicxml", fp=generated)
        data = generated.read_text(encoding="utf-8")
    data = re.sub(
        r"<encoding-date>[^<]+</encoding-date>",
        f"<encoding-date>{CANONICAL_ENCODING_DATE}</encoding-date>",
        data,
        count=1,
    )
    output_path.write_text(data, encoding="utf-8", newline="\n")


def _manifest_records(path: Path) -> Iterable[dict[str, object]]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    records = manifest.get("records")
    if not isinstance(records, list):
        raise MupConversionError("Manifest must contain a records array.")
    return records


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_manifest_artifacts(
    *,
    manifest_path: Path,
    source_dir: Path,
    records: Iterable[dict[str, object]],
) -> None:
    raw_root = manifest_path.parent / "raw"
    donated_pattern = re.compile(
        rb"this (?:mup )?(?:source code|code|file) is donated to the "
        rb"public domain\.",
        re.IGNORECASE,
    )
    for record in records:
        record_id = str(record["id"])
        page_path = raw_root / str(record["page_file"])
        page_data = page_path.read_bytes()
        if _sha256_file(page_path) != record["page_sha256"]:
            raise MupConversionError(
                f"Page hash drift for manifest record {record_id!r}."
            )
        page_declaration = str(record["page_rights_declaration"])
        if (
            page_declaration.removeprefix("Copyright: ").encode("utf-8")
            not in page_data
        ):
            raise MupConversionError(
                f"Page rights declaration drift for {record_id!r}."
            )
        if record["disposition"] == "rights_hold":
            continue
        source_path = source_dir / str(record["source_file"])
        source_data = source_path.read_bytes()
        if _sha256_file(source_path) != record["source_sha256"]:
            raise MupConversionError(
                f"Mup source hash drift for manifest record {record_id!r}."
            )
        if donated_pattern.search(source_data) is None:
            raise MupConversionError(
                f"Mup source donation declaration drift for {record_id!r}."
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--mup-executable", required=True, type=Path)
    args = parser.parse_args()

    records = list(_manifest_records(args.manifest))
    _validate_manifest_artifacts(
        manifest_path=args.manifest,
        source_dir=args.source_dir,
        records=records,
    )
    converted = 0
    for record in records:
        if record.get("disposition") != "eligible":
            continue
        source_name = str(record["source_file"])
        output_name = f"{record['id']}.musicxml"
        convert_source(
            source_path=args.source_dir / source_name,
            output_path=args.output_dir / output_name,
            mup_executable=args.mup_executable,
            lyricist=str(record["lyricist"]),
            composer=str(record["composer"]),
            expected_title=str(record["title"]),
        )
        converted += 1
    print(f"Converted {converted} HymnsToGod Mup sources.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
