from __future__ import annotations

import copy
from dataclasses import dataclass
import hashlib
from io import BytesIO
import json
from pathlib import Path
from threading import Lock
from typing import Any, Iterable

import cairosvg
from music21 import (
    clef,
    converter,
    instrument,
    interval,
    key,
    metadata,
    pitch,
    stream,
    tempo,
)
from pypdf import PdfReader, PdfWriter
import verovio

from hymn_render import __version__


LINE_NAMES = ("satb", "soprano", "alto", "tenor", "bass")
PART_INDEX = {"soprano": 0, "alto": 1, "tenor": 2, "bass": 3}
OCTAVE_PLACEMENTS = ("auto", "original", "up", "down")
OCTAVE_ALGORITHM_VERSION = "staff-position-majority-v1"
CLEF_FACTORIES = {
    "treble": clef.TrebleClef,
    "bass": clef.BassClef,
    "alto": clef.AltoClef,
    "tenor": clef.TenorClef,
    "treble-8vb": clef.Treble8vbClef,
}
PAGE_SIZES = {
    "letter": {
        # Slightly smaller virtual canvas makes Verovio paginate dense
        # five-verse SATB scores instead of squeezing a fourth system below
        # the physical page boundary. Cairo maps each page to exact Letter.
        "verovio_width": 2100,
        "verovio_height": 2718,
        "css_width": 816.0,
        "css_height": 1056.0,
    },
    "a4": {
        "verovio_width": 2100,
        "verovio_height": 2970,
        "css_width": 793.7008,
        "css_height": 1122.5197,
    },
}
_VEROVIO_TOOLKIT: verovio.toolkit | None = None
_VEROVIO_LOCK = Lock()


class RenderError(ValueError):
    """Raised when a requested transform cannot be performed safely."""


@dataclass(frozen=True)
class TransformResult:
    score: stream.Score
    selected_line: str
    source_key: str
    target_key: str
    interval_name: str
    clef_name: str
    octave_requested: str
    octave_resolved: int
    octave_algorithm_version: str
    pitches_before: tuple[str, ...]
    pitches_after_selection: tuple[str, ...]
    pitches_after_key_transposition: tuple[str, ...]
    pitches_after_transform: tuple[str, ...]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pitch_fingerprint(score: stream.Score) -> tuple[str, ...]:
    """Return ordered spelled pitches; clef changes cannot alter this value."""
    values: list[str] = []
    for element in score.recurse().notes:
        element_pitches: Iterable[pitch.Pitch]
        if hasattr(element, "pitches"):
            element_pitches = element.pitches
        else:
            element_pitches = (element.pitch,)
        values.extend(item.nameWithOctave for item in element_pitches)
    return tuple(values)


def _first_key(score: stream.Score) -> key.Key:
    keys = list(score.recurse().getElementsByClass(key.Key))
    if keys:
        return keys[0]
    signatures = list(score.recurse().getElementsByClass(key.KeySignature))
    if signatures:
        return signatures[0].asKey()
    analyzed = score.analyze("key")
    if isinstance(analyzed, key.Key):
        return analyzed
    raise RenderError("Could not determine the source key.")


def _target_key(value: str, source: key.Key) -> key.Key:
    normalized = value.strip()
    if not normalized:
        return source
    lower = normalized.lower()
    if lower.endswith(" major") or lower.endswith(" minor"):
        tonic_name, mode = normalized.rsplit(maxsplit=1)
        return key.Key(tonic_name, mode.lower())
    return key.Key(normalized, source.mode)


def _nearest_transposition(source: key.Key, destination: key.Key) -> interval.Interval:
    """Choose the enharmonically correct target tonic in the nearest octave."""
    source_tonic = copy.deepcopy(source.tonic)
    source_octave = source_tonic.octave or 4
    candidates: list[interval.Interval] = []
    for octave in (source_octave - 1, source_octave, source_octave + 1):
        target_tonic = copy.deepcopy(destination.tonic)
        target_tonic.octave = octave
        candidates.append(interval.Interval(source_tonic, target_tonic))
    return min(candidates, key=lambda candidate: (abs(candidate.semitones), candidate.semitones))


def _ledger_lines(staff_position: int) -> int:
    """Return ledger-line count for a diatonic position on a five-line staff."""
    if staff_position < 0:
        return (-staff_position) // 2
    if staff_position > 8:
        return (staff_position - 8) // 2
    return 0


def _effective_clef(
    element: Any,
    *,
    requested_clef: clef.Clef | None,
) -> clef.Clef:
    if requested_clef is not None:
        return requested_clef
    contextual = element.getContextByClass(clef.Clef)
    if isinstance(contextual, clef.Clef):
        return contextual
    raise RenderError("Could not determine the effective clef for octave placement.")


def _staff_positions(
    score: stream.Score,
    *,
    clef_name: str,
    octave_shift: int,
) -> tuple[int, ...]:
    requested_clef = (
        CLEF_FACTORIES[clef_name]() if clef_name != "original" else None
    )
    positions: list[int] = []
    for element in score.recurse().notes:
        effective_clef = _effective_clef(
            element,
            requested_clef=requested_clef,
        )
        element_pitches: Iterable[pitch.Pitch]
        if hasattr(element, "pitches"):
            element_pitches = element.pitches
        else:
            element_pitches = (element.pitch,)
        # Clef.lowestLine already incorporates octaveChange. In particular,
        # Treble8vbClef must not receive a second manual octave adjustment.
        positions.extend(
            item.diatonicNoteNum
            + (7 * octave_shift)
            - effective_clef.lowestLine
            for item in element_pitches
        )
    return tuple(positions)


def _octave_score(positions: tuple[int, ...], octave_shift: int) -> tuple[int, ...]:
    """Score staff fit while preventing a single outlier from moving a line."""
    if not positions:
        return (0, 0, 0, 0, 0, 0, 0)
    ledger_counts = tuple(_ledger_lines(position) for position in positions)
    ordered_ledgers = sorted(ledger_counts)
    midpoint = len(ordered_ledgers) // 2
    median_ledger = (
        ordered_ledgers[midpoint]
        if len(ordered_ledgers) % 2
        else ordered_ledgers[midpoint - 1] + ordered_ledgers[midpoint]
    )
    # Capping each note's contribution makes the repeated-note majority more
    # important than a single malformed or unusually remote pitch.
    ledger_burden = sum(min(count, 4) ** 2 for count in ledger_counts)
    outside_preferred = sum(count > 1 for count in ledger_counts)
    center_burden = sum(min(abs(position - 4), 12) for position in positions)
    return (
        median_ledger,
        ledger_burden,
        outside_preferred,
        min(max(ledger_counts), 4),
        center_burden,
        0 if octave_shift == 0 else 1,
        abs(octave_shift),
    )


def _resolve_octave_shift(
    score: stream.Score,
    *,
    line_name: str,
    clef_name: str,
    octave_placement: str,
) -> int:
    if octave_placement not in OCTAVE_PLACEMENTS:
        raise RenderError(
            f"Unknown octave placement {octave_placement!r}; choose from "
            f"{OCTAVE_PLACEMENTS}."
        )
    if line_name == "satb":
        if octave_placement in {"up", "down"}:
            raise RenderError(
                "Explicit octave shifts are available only for individual lines."
            )
        return 0
    if octave_placement == "original":
        return 0
    if octave_placement == "up":
        return 1
    if octave_placement == "down":
        return -1

    candidates = (-1, 0, 1)
    scored = [
        (
            _octave_score(
                _staff_positions(
                    score,
                    clef_name=clef_name,
                    octave_shift=candidate,
                ),
                candidate,
            ),
            candidate,
        )
        for candidate in candidates
    ]
    # The final candidate value is a deterministic last resort. Exact musical
    # ties are resolved to zero by the explicit rank in _octave_score.
    return min(scored, key=lambda item: (item[0], abs(item[1]), item[1]))[1]


def _remove_elements(score: stream.Score, element_type: type[Any]) -> None:
    for existing in list(score.recurse().getElementsByClass(element_type)):
        if existing.activeSite is not None:
            existing.activeSite.remove(existing)


def _prepare_engraving(score: stream.Score, line_name: str) -> None:
    # The source's generic MIDI-piano instrument leaks into one staff label.
    # Tempo glyphs render through an embedded SMuFL webfont that CairoSVG does
    # not consume reliably, so the print view intentionally omits them.
    _remove_elements(score, instrument.Instrument)
    _remove_elements(score, tempo.MetronomeMark)
    if score.metadata is not None and score.metadata.title:
        # music21 otherwise writes the input filename as movement-title, which
        # Verovio prefers over the correct work-title in its page header.
        score.metadata.movementName = score.metadata.title
    if line_name == "satb":
        for part in score.parts:
            part.partName = ""
            part.partAbbreviation = ""
    else:
        part = score.parts[0]
        part.partName = line_name.title()
        part.partAbbreviation = line_name[0].upper()


def _select_line(score: stream.Score, line_name: str) -> stream.Score:
    if line_name == "satb":
        return copy.deepcopy(score)
    voiced = score.voicesToParts()
    if len(voiced.parts) < 4:
        raise RenderError(
            f"Expected four SATB voices, but voicesToParts() returned "
            f"{len(voiced.parts)}."
        )
    selected = copy.deepcopy(voiced.parts[PART_INDEX[line_name]])
    result = stream.Score()
    if score.metadata is not None:
        result.metadata = copy.deepcopy(score.metadata)
    else:
        result.metadata = metadata.Metadata()
    result.insert(0, selected)
    return result


def _replace_clefs(score: stream.Score, clef_name: str) -> None:
    if clef_name == "original":
        return
    factory = CLEF_FACTORIES[clef_name]
    for part in score.parts:
        for existing in list(part.recurse().getElementsByClass(clef.Clef)):
            if existing.activeSite is not None:
                existing.activeSite.remove(existing)
        measures = list(part.getElementsByClass(stream.Measure))
        if measures:
            measures[0].insert(0, factory())
        else:
            part.insert(0, factory())


def transform_musicxml(
    input_path: Path,
    *,
    line_name: str = "satb",
    target_key_name: str | None = None,
    clef_name: str = "original",
    octave_placement: str = "original",
) -> TransformResult:
    if line_name not in LINE_NAMES:
        raise RenderError(f"Unknown line {line_name!r}; choose from {LINE_NAMES}.")
    if clef_name != "original" and clef_name not in CLEF_FACTORIES:
        raise RenderError(
            f"Unknown clef {clef_name!r}; choose original or "
            f"{tuple(CLEF_FACTORIES)}."
        )
    if octave_placement not in OCTAVE_PLACEMENTS:
        raise RenderError(
            f"Unknown octave placement {octave_placement!r}; choose from "
            f"{OCTAVE_PLACEMENTS}."
        )

    parsed = converter.parse(str(input_path))
    if not isinstance(parsed, stream.Score):
        raise RenderError("MusicXML input did not parse as a score.")

    source_key = _first_key(parsed)
    all_pitches = pitch_fingerprint(parsed)
    selected = _select_line(parsed, line_name)
    selected_pitches = pitch_fingerprint(selected)

    destination_key = (
        _target_key(target_key_name, source_key)
        if target_key_name is not None
        else source_key
    )
    transposition = _nearest_transposition(source_key, destination_key)
    if transposition.semitones:
        selected.transpose(transposition, inPlace=True)

    after_key_transposition = pitch_fingerprint(selected)
    octave_shift = _resolve_octave_shift(
        selected,
        line_name=line_name,
        clef_name=clef_name,
        octave_placement=octave_placement,
    )
    if octave_shift:
        selected.transpose(interval.Interval(octave_shift * 12), inPlace=True)

    before_clef_change = pitch_fingerprint(selected)
    _replace_clefs(selected, clef_name)
    after_clef_change = pitch_fingerprint(selected)
    if before_clef_change != after_clef_change:
        raise RenderError("Clef replacement unexpectedly changed sounding pitches.")
    _prepare_engraving(selected, line_name)

    return TransformResult(
        score=selected,
        selected_line=line_name,
        source_key=source_key.name,
        target_key=destination_key.name,
        interval_name=transposition.directedName,
        clef_name=clef_name,
        octave_requested=octave_placement,
        octave_resolved=octave_shift,
        octave_algorithm_version=OCTAVE_ALGORITHM_VERSION,
        pitches_before=all_pitches,
        pitches_after_selection=selected_pitches,
        pitches_after_key_transposition=after_key_transposition,
        pitches_after_transform=after_clef_change,
    )


def write_musicxml(result: TransformResult, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.score.write("musicxml", fp=str(output_path))


def render_svg_pages(
    musicxml_path: Path,
    output_dir: Path,
    *,
    page_size: str = "letter",
) -> tuple[list[Path], dict[str, Any]]:
    if page_size not in PAGE_SIZES:
        raise RenderError(f"Unknown page size {page_size!r}.")
    size = PAGE_SIZES[page_size]
    options = {
        "adjustPageHeight": False,
        "adjustPageWidth": False,
        "breaks": "auto",
        "footer": "none",
        "header": "auto",
        "lyricWordSpace": 2.2,
        "pageHeight": size["verovio_height"],
        "pageMarginBottom": 80,
        "pageMarginLeft": 80,
        "pageMarginRight": 80,
        "pageMarginTop": 80,
        "pageWidth": size["verovio_width"],
        "scale": 40,
        "svgViewBox": True,
        "xmlIdSeed": 1,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for stale_page in output_dir.glob("page-*.svg"):
        stale_page.unlink()
    pages: list[Path] = []
    global _VEROVIO_TOOLKIT
    with _VEROVIO_LOCK:
        # The Python binding can release its process-global font resources
        # when short-lived toolkit instances are destroyed. A long-lived,
        # serialized toolkit is also safer for concurrent HTTP render calls.
        if _VEROVIO_TOOLKIT is None:
            _VEROVIO_TOOLKIT = verovio.toolkit()
        toolkit = _VEROVIO_TOOLKIT
        toolkit.resetOptions()
        if not toolkit.setOptions(options):
            raise RenderError("Verovio rejected the render options.")
        if not toolkit.loadFile(str(musicxml_path)):
            raise RenderError("Verovio could not load the transformed MusicXML.")
        for page_number in range(1, toolkit.getPageCount() + 1):
            path = output_dir / f"page-{page_number:03d}.svg"
            path.write_text(toolkit.renderToSVG(page_number), encoding="utf-8")
            pages.append(path)
        toolkit_version = toolkit.getVersion()
    if not pages:
        raise RenderError("Verovio produced no pages.")
    return pages, {
        "options": options,
        "page_count": len(pages),
        "page_size": page_size,
        "verovio_version": toolkit_version,
    }


def svg_pages_to_pdf(
    svg_paths: list[Path],
    output_path: Path,
    *,
    page_size: str = "letter",
) -> None:
    if page_size not in PAGE_SIZES:
        raise RenderError(f"Unknown page size {page_size!r}.")
    if not svg_paths:
        raise RenderError("Cannot create a PDF without SVG pages.")
    size = PAGE_SIZES[page_size]
    writer = PdfWriter()
    for svg_path in svg_paths:
        page_pdf = cairosvg.svg2pdf(
            bytestring=svg_path.read_bytes(),
            output_width=size["css_width"],
            output_height=size["css_height"],
        )
        reader = PdfReader(BytesIO(page_pdf))
        if len(reader.pages) != 1:
            raise RenderError(f"Expected one PDF page for {svg_path.name}.")
        writer.add_page(reader.pages[0])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as output:
        writer.write(output)


def run_pipeline(
    input_path: Path,
    output_dir: Path,
    *,
    line_name: str = "satb",
    target_key_name: str | None = None,
    clef_name: str = "original",
    octave_placement: str = "original",
    page_size: str = "letter",
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    transformed_path = output_dir / "score.musicxml"
    pdf_path = output_dir / "score.pdf"

    result = transform_musicxml(
        input_path,
        line_name=line_name,
        target_key_name=target_key_name,
        clef_name=clef_name,
        octave_placement=octave_placement,
    )
    write_musicxml(result, transformed_path)
    svg_paths, render_metadata = render_svg_pages(
        transformed_path, output_dir, page_size=page_size
    )
    svg_pages_to_pdf(svg_paths, pdf_path, page_size=page_size)

    manifest = {
        "generator": {"name": "hymn_render", "version": __version__},
        "input": {"path": str(input_path), "sha256": sha256_file(input_path)},
        "output": {
            "musicxml": {
                "path": transformed_path.name,
                "sha256": sha256_file(transformed_path),
            },
            "pdf": {"path": pdf_path.name, "sha256": sha256_file(pdf_path)},
            "svg_pages": [
                {"path": path.name, "sha256": sha256_file(path)}
                for path in svg_paths
            ],
        },
        "render": render_metadata,
        "transform": {
            "clef": result.clef_name,
            "clef_pitch_invariant": True,
            "interval": result.interval_name,
            "line": result.selected_line,
            "octave_algorithm_version": result.octave_algorithm_version,
            "octave_requested": result.octave_requested,
            "octave_resolved": result.octave_resolved,
            "pitch_count_after_selection": len(result.pitches_after_selection),
            "pitch_count_after_transform": len(result.pitches_after_transform),
            "pitch_fingerprint_after_selection": hashlib.sha256(
                "\n".join(result.pitches_after_selection).encode()
            ).hexdigest(),
            "pitch_fingerprint_after_transform": hashlib.sha256(
                "\n".join(result.pitches_after_transform).encode()
            ).hexdigest(),
            "source_key": result.source_key,
            "target_key": result.target_key,
        },
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest
