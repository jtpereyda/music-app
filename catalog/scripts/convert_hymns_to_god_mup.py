#!/usr/bin/env python3
"""Convert the audited HymnsToGod Mup SATB subset to canonical MusicXML.

Mup's MIDI output intentionally collapses ordinary ``s`` (space) groups, so
MIDI is useful for listening but is not a lossless notation interchange
format.  This converter instead reads Mup's expanded notation statements and
preserves their measure timing, pitch spelling, voice overlays, and primary
lyrics.  The official Mup executable is used only for macro expansion.

The supported profile is deliberately narrow:

* two five-line staves, with treble and bass default octaves;
* two semantic voices per staff, retaining divisi chords inside either voice;
* simple, dotted, and regular tuplet durations (no grace notes);
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
import unicodedata

from music21 import (
    bar,
    chord,
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
CONVERTER_VERSION = "2"
CANONICAL_ENCODING_DATE = "2026-08-03"

_MUSIC_ASSIGNMENT_RE = re.compile(
    r"^\s*([12])(?:\s+([12]))?\s*:\s*(.*?)\s*$"
)
_BAR_RE = re.compile(
    r"^\s*(bar|invisbar|dblbar|endbar|repeatstart|repeatend)\b"
)
_TIME_CHANGE_RE = re.compile(
    r"^\s*(?:score\s+)?time\s*=\s*([0-9]+/[0-9]+)\b"
)
_DURATION_RE = re.compile(r"^(256|128|64|32|16|8|4|2|1)(\.*)")
_QUOTED_RE = re.compile(r'"((?:\\.|[^"\\])*)"')
_KEY_RE = re.compile(
    r"^\s*key\s*=\s*([^\s]+)(?:\s+(major|minor))?",
    re.MULTILINE,
)
_TIME_RE = re.compile(r"^\s*time\s*=\s*([0-9]+/[0-9]+)", re.MULTILINE)
_TITLE_RE = re.compile(r"^\s*title(?:\s+bold)?\b.*$", re.MULTILINE)
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
    time_signature: str = "4/4"
    duration: Fraction = Fraction(4)


@dataclass(frozen=True)
class SemanticEvent:
    onset: Fraction
    duration: Fraction
    value: tuple[ParsedPitch, ...] | None
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
    mode: str
    measures: tuple[ParsedMeasure, ...]


def _duration(value: str, dots: str) -> Fraction:
    base = Fraction(4, int(value))
    result = base
    addition = base
    for _ in dots:
        addition /= 2
        result += addition
    return result


def _tuplet_scale(count: int) -> Fraction:
    if count < 2:
        raise MupConversionError(f"Invalid tuplet count {count}.")
    normal_count = 1 << (count.bit_length() - 1)
    if normal_count == count:
        normal_count //= 2
    return Fraction(normal_count, count)


def _timed_group_tokens(body: str) -> list[tuple[str, Fraction]]:
    """Split semicolon groups while retaining Mup ``{...}N`` tuplets."""
    result: list[tuple[str, Fraction]] = []
    buffer: list[str] = []
    index = 0
    while index < len(body):
        character = body[index]
        if character == "[":
            closing = body.find("]", index + 1)
            if closing == -1:
                raise MupConversionError(
                    f"Unclosed bracket attribute in {body!r}."
                )
            buffer.append(body[index : closing + 1])
            index = closing + 1
            continue
        if character == ";":
            result.append(("".join(buffer), Fraction(1)))
            buffer = []
            index += 1
            continue
        if character != "{":
            buffer.append(character)
            index += 1
            continue
        if "".join(buffer).strip():
            raise MupConversionError(
                f"Tuplet must begin at a group boundary: {body!r}."
            )
        buffer = []
        closing = body.find("}", index + 1)
        if closing == -1:
            raise MupConversionError(f"Unclosed tuplet in {body!r}.")
        count_start = closing + 1
        count_match = re.match(
            r"\s*(?:(?:above|below)\s+)?([0-9]+)",
            body[count_start:],
        )
        if count_match is None:
            raise MupConversionError(f"Tuplet has no count in {body!r}.")
        count_end = count_start + count_match.end()
        scale = _tuplet_scale(int(count_match.group(1)))
        inner_groups = body[index + 1 : closing].split(";")
        if inner_groups and not inner_groups[-1].strip():
            inner_groups.pop()
        if not inner_groups:
            raise MupConversionError(f"Tuplet has no groups in {body!r}.")
        result.extend((group, scale) for group in inner_groups)
        index = count_end
        if index < len(body) and body[index].lower() == "n":
            index += 1
        if index < len(body) and body[index] == ";":
            index += 1
    if buffer and "".join(buffer).strip():
        result.append(("".join(buffer), Fraction(1)))
    if not result:
        raise MupConversionError("An assignment contains no groups.")
    return result


def _measure_duration(time_signature: str) -> Fraction:
    numerator, denominator = (int(value) for value in time_signature.split("/"))
    return Fraction(numerator * 4, denominator)


def _quoted_strings(value: str) -> list[str]:
    return [match.group(1) for match in _QUOTED_RE.finditer(value)]


def _source_title(expanded: str) -> str:
    for match in _TITLE_RE.finditer(expanded):
        line = match.group(0)
        size_match = re.search(r"\(\s*([0-9]+)\s*\)", line)
        prominent = " bold" in line.lower() or (
            size_match is not None and int(size_match.group(1)) >= 18
        )
        values = [
            decoded
            for value in _quoted_strings(line)
            if (decoded := _decode_mup_text(value).strip())
        ]
        if prominent and len(values) == 1:
            return values[0]
    raise MupConversionError("Could not locate the prominent score title.")


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
    # ``bm`` and ``ebm`` are Mup's begin/end beam markers. They can be
    # attached directly to a single pitch instead of separated by whitespace.
    if cluster == "bm":
        cluster = "b"
    elif len(cluster) > 2 and cluster.endswith("bm"):
        cluster = cluster[:-2]
    for notation_suffix in ("slur", "tie"):
        if cluster.endswith(notation_suffix) and len(cluster) > len(
            notation_suffix
        ):
            cluster = cluster[: -len(notation_suffix)]
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
                for direction in ("up", "down"):
                    if cluster.startswith(direction, index):
                        index += len(direction)
                        break
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
    measure_extent: Fraction,
) -> list[ParsedGroup]:
    raw_groups = _timed_group_tokens(body)

    result: list[ParsedGroup] = []
    previous: ParsedGroup | None = None
    onset = Fraction(0)
    previous_notated_duration: Fraction | None = None
    for raw, duration_scale in raw_groups:
        token = _BRACKET_ATTRIBUTE_RE.sub("", raw).strip()
        token = re.sub(r"^\.\.\.\s*", "", token)
        duration_match = _DURATION_RE.match(token)
        if token.lower() == "mr":
            notated_duration = measure_extent
        elif duration_match:
            notated_duration = _duration(
                duration_match.group(1),
                duration_match.group(2),
            )
            token = token[duration_match.end() :].strip()
        elif previous_notated_duration is not None:
            notated_duration = previous_notated_duration
        else:
            notated_duration = default_duration
        group_duration = notated_duration * duration_scale

        if not token:
            if previous is None:
                raise MupConversionError("The first group cannot be empty.")
            kind = previous.kind
            pitches = copy.deepcopy(previous.pitches)
        else:
            first = token[0].lower()
            if token.lower() == "mr" or first == "r":
                kind = "rest"
                pitches = ()
            elif (
                re.fullmatch(r"s+", token.lower()) is not None
                or token.lower().startswith("s ")
                or token.lower().startswith("us")
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
        lyric_continue = tie_to_next or any(
            value.tie_to_next for value in pitches
        ) or bool(
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
        previous_notated_duration = notated_duration
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
    prefix = _BRACKET_ATTRIBUTE_RE.sub("", prefix).strip()
    normalized_header = " ".join(before_colon.split())
    using = re.search(r"\busing\s+([12])(?:\s+([12]))?", normalized_header)
    direct = re.fullmatch(
        r"lyrics\s+(?:(?:above|below)\s+)?([12])(?:\s+([12]))?",
        normalized_header,
    )
    if using:
        using_staff = int(using.group(1))
        using_voice = int(using.group(2) or "1")
    elif direct:
        using_staff = int(direct.group(1))
        using_voice = int(direct.group(2) or "1")
    else:
        using_staff = 1
        using_voice = 1
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
    mode = (key_match.group(2) or "major").lower()
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
        time_change = _TIME_CHANGE_RE.match(line)
        if time_change:
            if assignments or lyrics:
                raise MupConversionError(
                    "A time-signature change must occur at a measure boundary."
                )
            time_signature = time_change.group(1)
            measure_extent = _measure_duration(time_signature)
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
                measure_extent=measure_extent,
            )
            assignments[assignment_key] = groups
            continue
        if line.startswith("lyrics"):
            lyrics.append(_parse_lyric(line))
            continue
        bar_match = _BAR_RE.match(line)
        if bar_match:
            if not assignments:
                continue
            extents = {
                sum((group.duration for group in groups), Fraction(0))
                for groups in assignments.values()
            }
            actual_extent = max(extents)
            if actual_extent > measure_extent:
                raise MupConversionError(
                    f"Measure duration {actual_extent} exceeds {measure_extent}."
                )
            for groups in assignments.values():
                extent = sum(
                    (group.duration for group in groups), Fraction(0)
                )
                if extent < actual_extent:
                    groups.append(
                        ParsedGroup(
                            onset=extent,
                            duration=actual_extent - extent,
                            kind="space",
                        )
                    )
            measures.append(
                ParsedMeasure(
                    assignments=assignments,
                    lyrics=lyrics,
                    bar_type=bar_match.group(1),
                    time_signature=time_signature,
                    duration=actual_extent,
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
        mode=mode,
        measures=tuple(measures),
    )


def _group_at(groups: list[ParsedGroup] | None, point: Fraction) -> ParsedGroup | None:
    if groups is None:
        return None
    return next((group for group in groups if group.onset <= point < group.end), None)


def _audible_pitches(group: ParsedGroup) -> list[ParsedPitch]:
    full_size = [value for value in group.pitches if not value.small]
    return sorted(full_size or list(group.pitches), key=lambda value: value.midi)


def _semantic_voices(
    measure: ParsedMeasure,
    staff_number: int,
    measure_extent: Fraction,
) -> tuple[list[SemanticEvent], list[SemanticEvent]]:
    primary = measure.assignments.get((staff_number, 1))
    if primary is None:
        primary = measure.assignments.get((staff_number, 2))
        if primary is None:
            silent = [
                SemanticEvent(
                    onset=Fraction(0),
                    duration=measure_extent,
                    value=None,
                    attack=True,
                )
            ]
            return (
                copy.deepcopy(silent),
                copy.deepcopy(silent),
            )
        secondary = None
    else:
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
        if primary_group.kind == "pitch":
            if not primary_values:
                raise MupConversionError(
                    "A primary pitched group contains only cue-sized notes."
                )
            # The primary stream conventionally carries the upper semantic
            # part as its highest pitch. Any remaining pitches are the lower
            # part, including occasional divisi chords. A one-note unison is
            # intentionally present in both semantic parts, matching the
            # source's two-part hymn-staff convention.
            upper_value = (primary_values[-1],)
            lower_value = tuple(primary_values[:-1] or primary_values)
        else:
            upper_value = None
            lower_value = None

        secondary_supplies = (
            secondary_group is not None and secondary_group.kind != "space"
        )
        if secondary_supplies:
            secondary_values = _audible_pitches(secondary_group)
            if secondary_group.kind == "pitch":
                if not secondary_values:
                    raise MupConversionError(
                        "A secondary pitched group contains only cue-sized notes."
                    )
                # An explicit secondary stream replaces the lower part. Some
                # arrangements divide that part into two or more pitches; a
                # MusicXML chord preserves the complete printed harmony.
                lower_value = tuple(secondary_values)
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
    # Mup's ``_{N}`` syntax extends the preceding syllable across N groups;
    # the brace count controls engraving and is not another lyric token.
    value = re.sub(r"\{[0-9]+\}", "", value)
    value = value.replace("<>", "\ue001")
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
                syllabic = "begin" if word.endswith("-") else "single"
            elif index == 0:
                syllabic = "begin"
            elif index == len(pieces) - 1:
                syllabic = "end"
            else:
                syllabic = "middle"
            text = piece.replace("\ue000", " ").replace("\ue001", "")
            result.append(LyricToken(text=text, syllabic=syllabic))
    return result


def _lyric_prefix_onsets(prefix: str) -> list[Fraction]:
    raw_groups = _timed_group_tokens(prefix)
    result: list[Fraction] = []
    onset = Fraction(0)
    previous_notated_duration: Fraction | None = None
    for raw, duration_scale in raw_groups:
        token = raw.strip()
        duration_match = _DURATION_RE.match(token)
        if duration_match:
            notated_duration = _duration(
                duration_match.group(1),
                duration_match.group(2),
            )
            token = token[duration_match.end() :].strip()
        elif previous_notated_duration is not None:
            notated_duration = previous_notated_duration
        else:
            raise MupConversionError(
                f"Lyric timing must begin with a duration: {prefix!r}."
            )
        group_duration = notated_duration * duration_scale
        if token.lower() != "s":
            result.append(onset)
        onset += group_duration
        previous_notated_duration = notated_duration
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


def _measure_lyrics(
    measure: ParsedMeasure,
) -> list[tuple[int, int, str, list[tuple[Fraction, LyricToken]]]]:
    """Return every audible lyric layer, grouped into its source verses."""
    layers: dict[tuple[str, str, int, int], list[ParsedLyric]] = {}
    for lyric in measure.lyrics:
        key_value = (
            lyric.header,
            lyric.prefix,
            lyric.using_staff,
            lyric.using_voice,
        )
        layers.setdefault(key_value, []).append(lyric)

    result: list[
        tuple[int, int, str, list[tuple[Fraction, LyricToken]]]
    ] = []
    for (_, _, staff_number, voice_number), lyrics in layers.items():
        audible_verse = 0
        for lyric in lyrics:
            tokens = _lyric_tokens(lyric.text)
            if not tokens:
                continue
            onsets = _derived_lyric_onsets(measure, lyric)
            if len(tokens) < len(onsets):
                tokens.extend(
                    LyricToken(text="", syllabic="single")
                    for _ in range(len(onsets) - len(tokens))
                )
            if len(tokens) != len(onsets):
                raise MupConversionError(
                    f"Lyric syllable/timing mismatch for {lyric.text!r}: "
                    f"{len(tokens)} syllables and {len(onsets)} note positions."
                )
            audible_verse += 1
            result.append(
                (
                    staff_number,
                    voice_number,
                    str(audible_verse),
                    list(zip(onsets, tokens)),
                )
            )
    return result


def _music21_voice(
    events: list[SemanticEvent],
    *,
    voice_id: str,
) -> tuple[stream.Voice, dict[Fraction, note.NotRest]]:
    result = stream.Voice(id=voice_id)
    notes_by_onset: dict[Fraction, note.NotRest] = {}
    created: list[note.NotRest] = []
    for event in events:
        quarter_length = float(event.duration)
        if event.value is None:
            element: note.NotRest = note.Rest(quarterLength=quarter_length)
        else:
            if len(event.value) == 1:
                element = note.Note(
                    event.value[0].to_music21(),
                    quarterLength=quarter_length,
                )
            else:
                element = chord.Chord(
                    [value.to_music21() for value in event.value],
                    quarterLength=quarter_length,
                )
            notes_by_onset[event.onset] = element
        result.insert(float(event.onset), element)
        created.append(element)

    for index, event in enumerate(events):
        if event.value is None:
            continue

        def pitch_identity(value: ParsedPitch) -> tuple[str, int, int]:
            return value.step, value.alter, value.octave

        current_notes = (
            [created[index]]
            if isinstance(created[index], note.Note)
            else list(created[index].notes)
        )
        previous_event = events[index - 1] if index > 0 else None
        following_event = events[index + 1] if index + 1 < len(events) else None
        previous_values = {
            pitch_identity(value): value
            for value in (previous_event.value or ())
        } if previous_event is not None else {}
        following_values = {
            pitch_identity(value): value
            for value in (following_event.value or ())
        } if following_event is not None else {}
        for parsed_pitch, created_note in zip(event.value, current_notes, strict=True):
            identity = pitch_identity(parsed_pitch)
            previous_pitch = previous_values.get(identity)
            tied_from_previous = (
                previous_event is not None
                and previous_pitch is not None
                and (
                    previous_event.tie_to_next
                    or previous_pitch.tie_to_next
                )
            )
            tied_to_following = (
                following_event is not None
                and identity in following_values
                and (event.tie_to_next or parsed_pitch.tie_to_next)
            )
            if tied_from_previous and tied_to_following:
                created_note.tie = tie.Tie("continue")
            elif tied_from_previous:
                created_note.tie = tie.Tie("stop")
            elif tied_to_following:
                created_note.tie = tie.Tie("start")
    return result, notes_by_onset


def _split_events_at(
    events: list[SemanticEvent],
    split_points: set[Fraction],
) -> list[SemanticEvent]:
    result: list[SemanticEvent] = []
    for event in events:
        points = [
            event.onset,
            *sorted(
                point
                for point in split_points
                if event.onset < point < event.end
            ),
            event.end,
        ]
        for segment_index, (onset, end) in enumerate(zip(points, points[1:])):
            is_last = segment_index == len(points) - 2
            result.append(
                SemanticEvent(
                    onset=onset,
                    duration=end - onset,
                    value=event.value,
                    attack=event.attack if segment_index == 0 else False,
                    tie_to_next=(
                        event.tie_to_next
                        if is_last
                        else event.value is not None
                    ),
                )
            )
    return result


def _semantic_event_at(
    events: list[SemanticEvent], point: Fraction
) -> SemanticEvent | None:
    return next(
        (event for event in events if event.onset <= point < event.end),
        None,
    )


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

    parts = [stream.Part(id="P1"), stream.Part(id="P2")]
    parts[0].partName = "Soprano and Alto"
    parts[1].partName = "Tenor and Bass"
    previous_time_signature: str | None = None
    repeat_start = False
    for measure_index, parsed_measure in enumerate(parsed.measures, start=1):
        measure_extent = parsed_measure.duration
        measure_lyrics = _measure_lyrics(parsed_measure)
        semantic_voices = {
            staff_index: _semantic_voices(
                parsed_measure,
                staff_index,
                measure_extent,
            )
            for staff_index in (1, 2)
        }
        resolved_lyrics = []
        for lyric_staff, lyric_voice, verse_id, values in measure_lyrics:
            mapped: dict[
                tuple[int, int], list[tuple[Fraction, LyricToken]]
            ] = {}
            for onset, token in values:
                if not token.text:
                    continue
                audible: list[tuple[int, int]] = []
                attacking: list[tuple[int, int]] = []
                for staff in (1, 2):
                    for voice in (1, 2):
                        event = _semantic_event_at(
                            semantic_voices[staff][voice - 1], onset
                        )
                        if event is None or event.value is None:
                            continue
                        target = (staff, voice)
                        audible.append(target)
                        if event.attack and event.onset == onset:
                            attacking.append(target)
                candidates = attacking or audible
                requested = (lyric_staff, lyric_voice)
                same_staff = [
                    candidate
                    for candidate in candidates
                    if candidate[0] == lyric_staff
                ]
                same_voice = [
                    candidate
                    for candidate in candidates
                    if candidate[1] == lyric_voice
                ]
                if requested in candidates:
                    target = requested
                elif len(same_staff) == 1:
                    target = same_staff[0]
                elif len(same_voice) == 1:
                    target = same_voice[0]
                elif len(candidates) == 1:
                    target = candidates[0]
                else:
                    raise MupConversionError(
                        "Lyric timing does not resolve to a unique audible "
                        f"voice at {onset} in measure {measure_index}."
                    )
                mapped.setdefault(target, []).append((onset, token))
            resolved_lyrics.extend(
                (staff, voice, verse_id, mapped_values)
                for (staff, voice), mapped_values in mapped.items()
            )
        measure_lyrics = resolved_lyrics
        for staff_index, part in enumerate(parts, start=1):
            music_measure = stream.Measure(number=measure_index)
            nominal_extent = _measure_duration(parsed_measure.time_signature)
            if measure_index == 1 and measure_extent < nominal_extent:
                music_measure.paddingLeft = float(nominal_extent - measure_extent)
            if measure_index == 1:
                music_measure.insert(
                    0,
                    clef.TrebleClef() if staff_index == 1 else clef.BassClef(),
                )
                music_measure.insert(
                    0,
                    key.KeySignature(parsed.fifths).asKey(parsed.mode),
                )
            if parsed_measure.time_signature != previous_time_signature:
                music_measure.insert(
                    0,
                    meter.TimeSignature(parsed_measure.time_signature),
                )
            if repeat_start:
                music_measure.leftBarline = bar.Repeat(direction="start")
            upper_events, lower_events = semantic_voices[staff_index]
            upper_split_points = {
                onset
                for lyric_staff, lyric_voice, _, values in measure_lyrics
                if lyric_staff == staff_index and lyric_voice == 1
                for onset, _ in values
            }
            lower_split_points = {
                onset
                for lyric_staff, lyric_voice, _, values in measure_lyrics
                if lyric_staff == staff_index and lyric_voice == 2
                for onset, _ in values
            }
            upper_events = _split_events_at(upper_events, upper_split_points)
            lower_events = _split_events_at(lower_events, lower_split_points)
            upper, upper_notes = _music21_voice(upper_events, voice_id="1")
            lower, lower_notes = _music21_voice(lower_events, voice_id="2")
            for lyric_staff, lyric_voice, verse_id, values in measure_lyrics:
                if lyric_staff != staff_index:
                    continue
                target_notes = upper_notes if lyric_voice == 1 else lower_notes
                for onset, lyric_token in values:
                    if not lyric_token.text:
                        continue
                    target = target_notes.get(onset)
                    if target is None:
                        raise MupConversionError(
                            f"Lyric onset {onset} has no attack in staff "
                            f"{lyric_staff} voice {lyric_voice}, measure "
                            f"{measure_index}."
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
            elif parsed_measure.bar_type == "repeatend":
                music_measure.rightBarline = bar.Repeat(direction="end")
            parts[staff_index - 1].append(music_measure)
        repeat_start = parsed_measure.bar_type == "repeatstart"
        previous_time_signature = parsed_measure.time_signature
    for part in parts:
        result.append(part)
    return result


def expand_mup(source_path: Path, mup_executable: Path) -> str:
    completed = subprocess.run(
        [str(mup_executable), "-q", "-E", str(source_path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode != 0:
        raise MupConversionError(
            f"Mup macro expansion failed for {source_path}: "
            f"{completed.stderr.strip()}"
        )
    return completed.stdout


def _normalized_title(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")


def _normalized_title_variants(value: str) -> set[str]:
    variants = {_normalized_title(value)}
    article_match = re.match(r"^(.*),\s*(the|a|an)$", value, re.IGNORECASE)
    if article_match:
        variants.add(
            _normalized_title(
                f"{article_match.group(2)} {article_match.group(1)}"
            )
        )
    return variants


def convert_source(
    *,
    source_path: Path,
    output_path: Path,
    mup_executable: Path,
    lyricist: str | None = None,
    composer: str | None = None,
    expected_title: str | None = None,
) -> ParsedScore:
    parsed = parse_expanded_mup(expand_mup(source_path, mup_executable))
    if (
        expected_title is not None
        and not (
            _normalized_title_variants(parsed.title)
            & _normalized_title_variants(expected_title)
        )
    ):
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
    return parsed


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


def _mup_version(executable: Path) -> str:
    completed = subprocess.run(
        [str(executable), "-v"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    output = f"{completed.stdout}\n{completed.stderr}"
    match = re.search(r"\bVersion\s+([0-9]+(?:\.[0-9]+)*)\b", output)
    if completed.returncode != 0 or match is None:
        raise MupConversionError(
            f"Could not determine Mup version from {executable}."
        )
    return match.group(1)


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


def _validate_inventory_artifacts(
    *,
    inventory_path: Path,
    source_root: Path,
    records: Iterable[dict[str, object]],
) -> None:
    raw_root = inventory_path.parent / "raw"
    for record in records:
        arrangement_id = str(record["arrangement_id"])
        page_file = record.get("page_file")
        if page_file is not None:
            page_path = raw_root / str(page_file)
            if _sha256_file(page_path) != record.get("page_sha256"):
                raise MupConversionError(
                    f"Page hash drift for inventory record {arrangement_id!r}."
                )
            declaration = str(record.get("page_rights_declaration", ""))
            if (
                record.get("rights_basis") == "individual_page_declaration"
                and declaration
                and declaration.removeprefix("Copyright: ").encode("utf-8")
                not in page_path.read_bytes()
            ):
                raise MupConversionError(
                    f"Page rights declaration drift for {arrangement_id!r}."
                )
        if record.get("disposition") != "pending_conversion":
            continue
        source_path = source_root / str(record["source_file"])
        if _sha256_file(source_path) != record.get("source_sha256"):
            raise MupConversionError(
                f"Mup source hash drift for inventory record {arrangement_id!r}."
            )


def convert_inventory(
    *,
    inventory_path: Path,
    source_root: Path,
    output_dir: Path,
    mup_executable: Path,
    conversion_report: Path,
) -> dict[str, object]:
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    if inventory.get("schema_version") != 2:
        raise MupConversionError("Bulk inventory must use schema version 2.")
    records = list(_manifest_records(inventory_path))
    _validate_inventory_artifacts(
        inventory_path=inventory_path,
        source_root=source_root,
        records=records,
    )

    report_records: list[dict[str, object]] = []
    for record in records:
        arrangement_id = str(record["arrangement_id"])
        result: dict[str, object] = {
            "arrangement_id": arrangement_id,
            "work_id": record["work_id"],
            "title": record.get("page_title") or record["title"],
            "index_title": record["title"],
            "arrangement_label": record.get("arrangement_label", ""),
            "inventory_disposition": record["disposition"],
        }
        if record.get("disposition") != "pending_conversion":
            result.update(
                disposition=record["disposition"],
                hold_reason=record.get("hold_reason", ""),
            )
            report_records.append(result)
            continue

        output_name = f"{arrangement_id}.musicxml"
        output_path = output_dir / output_name
        try:
            parsed = convert_source(
                source_path=source_root / str(record["source_file"]),
                output_path=output_path,
                mup_executable=mup_executable,
                lyricist=str(record.get("lyricist", "")),
                composer=str(record.get("composer", "")),
                expected_title=None,
            )
        except Exception as exc:  # One unsupported arrangement must not abort all.
            result.update(
                disposition="conversion_hold",
                hold_reason=str(exc),
                error_type=type(exc).__name__,
            )
        else:
            result.update(
                disposition="eligible",
                output_file=output_name,
                output_sha256=_sha256_file(output_path),
                source_title=parsed.title,
                source_title_matches_page=bool(
                    _normalized_title_variants(parsed.title)
                    & _normalized_title_variants(
                        str(record.get("page_title") or record["title"])
                    )
                ),
                source_fifths=parsed.fifths,
                source_mode=parsed.mode,
                time_signature=parsed.time_signature,
                measure_count=len(parsed.measures),
            )
        report_records.append(result)

    summary: dict[str, int] = {}
    for record in report_records:
        disposition = str(record["disposition"])
        summary[disposition] = summary.get(disposition, 0) + 1
    report: dict[str, object] = {
        "schema_version": 1,
        "dataset_id": inventory["dataset_id"],
        "inventory_sha256": _sha256_file(inventory_path),
        "converter": {
            "name": CONVERTER_NAME,
            "version": CONVERTER_VERSION,
            "mup_version": _mup_version(mup_executable),
        },
        "summary": dict(sorted(summary.items())),
        "records": report_records,
    }
    conversion_report.parent.mkdir(parents=True, exist_ok=True)
    conversion_report.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--mup-executable", required=True, type=Path)
    parser.add_argument("--conversion-report", type=Path)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if manifest.get("schema_version") == 2:
        report_path = args.conversion_report or (
            args.output_dir.parent / "conversion.json"
        )
        report = convert_inventory(
            inventory_path=args.manifest,
            source_root=args.source_dir,
            output_dir=args.output_dir,
            mup_executable=args.mup_executable,
            conversion_report=report_path,
        )
        print(
            f"Processed {len(report['records'])} HymnsToGod arrangements: "
            f"{report['summary']}."
        )
        return 0

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
