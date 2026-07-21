from __future__ import annotations

from pathlib import Path

import pytest
from music21 import clef, key, meter, metadata, note, stream
from pypdf import PdfReader

from hymn_render.core import (
    OCTAVE_ALGORITHM_VERSION,
    RenderError,
    _octave_score,
    pitch_fingerprint,
    render_svg_pages,
    run_pipeline,
    svg_pages_to_pdf,
    transform_musicxml,
    write_musicxml,
)


VOICE_PITCHES = (
    ("C5", "D5"),
    ("A4", "B4"),
    ("E4", "F4"),
    ("C3", "D3"),
)


def write_satb_fixture(path: Path) -> None:
    score = stream.Score()
    score.metadata = metadata.Metadata()
    score.metadata.title = "Synthetic SATB"
    for staff_index, staff_clef in enumerate((clef.TrebleClef(), clef.BassClef())):
        part = stream.Part()
        measure = stream.Measure(number=1)
        measure.insert(0, staff_clef)
        measure.insert(0, key.Key("C"))
        measure.insert(0, meter.TimeSignature("4/4"))
        for voice_index in range(2):
            voice = stream.Voice(id=str(voice_index + 1))
            for value in VOICE_PITCHES[staff_index * 2 + voice_index]:
                voice.append(note.Note(value, quarterLength=2))
            measure.insert(0, voice)
        part.append(measure)
        score.append(part)
    score.write("musicxml", fp=str(path))


def test_line_selection_maps_satb_order(tmp_path: Path) -> None:
    source = tmp_path / "source.musicxml"
    write_satb_fixture(source)
    for name, expected in zip(
        ("soprano", "alto", "tenor", "bass"), VOICE_PITCHES, strict=True
    ):
        result = transform_musicxml(source, line_name=name)
        assert result.pitches_after_transform == expected


def test_clef_change_is_pitch_invariant(tmp_path: Path) -> None:
    source = tmp_path / "source.musicxml"
    write_satb_fixture(source)
    result = transform_musicxml(source, line_name="soprano", clef_name="bass")
    assert result.pitches_after_selection == result.pitches_after_transform
    assert isinstance(
        next(iter(result.score.recurse().getElementsByClass(clef.Clef))),
        clef.BassClef,
    )


def test_transposition_changes_pitches_and_key(tmp_path: Path) -> None:
    source = tmp_path / "source.musicxml"
    write_satb_fixture(source)
    result = transform_musicxml(
        source, line_name="bass", target_key_name="D", clef_name="treble"
    )
    assert result.source_key == "C major"
    assert result.target_key == "D major"
    assert result.pitches_after_transform == ("D3", "E3")
    assert result.interval_name == "M2"


def test_transposition_uses_nearest_target_octave(tmp_path: Path) -> None:
    source = tmp_path / "source.musicxml"
    write_satb_fixture(source)
    result = transform_musicxml(source, line_name="alto", target_key_name="B-")
    assert result.interval_name == "M-2"
    assert result.pitches_after_transform == ("G4", "A4")


def test_explicit_target_mode_parses(tmp_path: Path) -> None:
    source = tmp_path / "source.musicxml"
    write_satb_fixture(source)
    result = transform_musicxml(source, line_name="soprano", target_key_name="D major")
    assert result.target_key == "D major"
    assert result.pitches_after_transform == ("D5", "E5")


def test_auto_octave_uses_final_key_and_effective_bass_clef(tmp_path: Path) -> None:
    source = tmp_path / "source.musicxml"
    write_satb_fixture(source)
    result = transform_musicxml(
        source,
        line_name="soprano",
        target_key_name="D",
        clef_name="bass",
        octave_placement="auto",
    )
    assert result.target_key == "D major"
    assert result.pitches_after_key_transposition == ("D5", "E5")
    assert result.pitches_after_transform == ("D4", "E4")
    assert result.octave_requested == "auto"
    assert result.octave_resolved == -1
    assert result.octave_algorithm_version == OCTAVE_ALGORITHM_VERSION


def test_manual_octave_shift_is_exact_and_does_not_change_target_key(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.musicxml"
    write_satb_fixture(source)
    up = transform_musicxml(
        source,
        line_name="bass",
        target_key_name="D",
        octave_placement="up",
    )
    down = transform_musicxml(
        source,
        line_name="soprano",
        target_key_name="D",
        octave_placement="down",
    )
    assert up.target_key == down.target_key == "D major"
    assert up.pitches_after_key_transposition == ("D3", "E3")
    assert up.pitches_after_transform == ("D4", "E4")
    assert up.octave_resolved == 1
    assert down.pitches_after_key_transposition == ("D5", "E5")
    assert down.pitches_after_transform == ("D4", "E4")
    assert down.octave_resolved == -1


def test_auto_octave_ties_to_zero_and_treble_8vb_is_not_double_shifted(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.musicxml"
    write_satb_fixture(source)
    result = transform_musicxml(
        source,
        line_name="tenor",
        clef_name="treble-8vb",
        octave_placement="auto",
    )
    assert result.pitches_after_key_transposition == ("E4", "F4")
    assert result.pitches_after_transform == ("E4", "F4")
    assert result.octave_resolved == 0


def test_satb_auto_preserves_register_and_manual_shift_is_rejected(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.musicxml"
    write_satb_fixture(source)
    automatic = transform_musicxml(source, octave_placement="auto")
    assert automatic.octave_resolved == 0
    assert automatic.pitches_after_selection == automatic.pitches_after_transform
    with pytest.raises(RenderError, match="individual lines"):
        transform_musicxml(source, octave_placement="up")


def test_auto_octave_scoring_follows_the_note_majority() -> None:
    # Four staff notes should outweigh one extreme outlier. Each candidate is
    # the same line moved by an exact diatonic octave.
    original_positions = (0, 1, 2, 3, 20)
    scored = [
        (
            _octave_score(
                tuple(position + (7 * shift) for position in original_positions),
                shift,
            ),
            shift,
        )
        for shift in (-1, 0, 1)
    ]
    assert min(scored, key=lambda item: (item[0], abs(item[1]), item[1]))[1] == 0


def test_pipeline_manifest_records_octave_decision(tmp_path: Path) -> None:
    source = tmp_path / "source.musicxml"
    write_satb_fixture(source)
    manifest = run_pipeline(
        source,
        tmp_path / "output",
        line_name="soprano",
        clef_name="bass",
        octave_placement="auto",
    )
    assert manifest["transform"]["octave_requested"] == "auto"
    assert manifest["transform"]["octave_resolved"] == -1
    assert (
        manifest["transform"]["octave_algorithm_version"]
        == OCTAVE_ALGORITHM_VERSION
    )


def test_verovio_svg_and_letter_pdf(tmp_path: Path) -> None:
    source = tmp_path / "source.musicxml"
    transformed = tmp_path / "transformed.musicxml"
    write_satb_fixture(source)
    result = transform_musicxml(source, line_name="satb")
    write_musicxml(result, transformed)
    svg_paths, render_metadata = render_svg_pages(
        transformed, tmp_path / "svg", page_size="letter"
    )
    assert render_metadata["page_count"] == len(svg_paths) >= 1
    assert all("<svg " in path.read_text(encoding="utf-8") for path in svg_paths)
    pdf = tmp_path / "score.pdf"
    svg_pages_to_pdf(svg_paths, pdf, page_size="letter")
    reader = PdfReader(pdf)
    assert len(reader.pages) == len(svg_paths)
    first = reader.pages[0]
    assert round(float(first.mediabox.width)) == 612
    assert round(float(first.mediabox.height)) == 792
    assert "Transposify" in first.extract_text()
    assert "hymn-transposer.vercel.app" in first.extract_text()
    assert first["/Annots"][0].get_object()["/A"]["/URI"] == (
        "https://hymn-transposer.vercel.app"
    )
    assert reader.metadata.creator == "Transposify"


def test_pipeline_manifest_records_pdf_footer(tmp_path: Path) -> None:
    source = tmp_path / "source.musicxml"
    write_satb_fixture(source)
    manifest = run_pipeline(source, tmp_path / "output")

    assert manifest["render"]["options"]["pageMarginBottom"] == 110
    assert manifest["render"]["pdf_footer"] == {
        "brand": "Transposify",
        "site_label": "hymn-transposer.vercel.app",
        "site_url": "https://hymn-transposer.vercel.app",
        "style": "transposify-v1",
    }


def test_verovio_can_render_repeatedly_in_one_process(tmp_path: Path) -> None:
    source = tmp_path / "source.musicxml"
    transformed = tmp_path / "transformed.musicxml"
    write_satb_fixture(source)
    write_musicxml(transform_musicxml(source), transformed)
    first, _ = render_svg_pages(transformed, tmp_path / "first")
    second, _ = render_svg_pages(transformed, tmp_path / "second")
    assert first[0].read_text(encoding="utf-8").startswith("<svg")
    assert second[0].read_text(encoding="utf-8").startswith("<svg")
