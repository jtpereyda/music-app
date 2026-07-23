from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


HYMN_ID_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class RenderLine(StrEnum):
    SATB = "satb"
    SOPRANO = "soprano"
    ALTO = "alto"
    TENOR = "tenor"
    BASS = "bass"


class ClefChoice(StrEnum):
    ORIGINAL = "original"
    TREBLE = "treble"
    BASS = "bass"
    ALTO = "alto"
    TENOR = "tenor"
    TREBLE_8VB = "treble-8vb"


class PageSize(StrEnum):
    LETTER = "letter"
    A4 = "a4"


class OctavePlacement(StrEnum):
    AUTO = "auto"
    ORIGINAL = "original"
    UP = "up"
    DOWN = "down"


class KeyChoice(StrEnum):
    ORIGINAL = "original"

    C_FLAT_MAJOR = "c-flat-major"
    G_FLAT_MAJOR = "g-flat-major"
    D_FLAT_MAJOR = "d-flat-major"
    A_FLAT_MAJOR = "a-flat-major"
    E_FLAT_MAJOR = "e-flat-major"
    B_FLAT_MAJOR = "b-flat-major"
    F_MAJOR = "f-major"
    C_MAJOR = "c-major"
    G_MAJOR = "g-major"
    D_MAJOR = "d-major"
    A_MAJOR = "a-major"
    E_MAJOR = "e-major"
    B_MAJOR = "b-major"
    F_SHARP_MAJOR = "f-sharp-major"
    C_SHARP_MAJOR = "c-sharp-major"

    A_FLAT_MINOR = "a-flat-minor"
    E_FLAT_MINOR = "e-flat-minor"
    B_FLAT_MINOR = "b-flat-minor"
    F_MINOR = "f-minor"
    C_MINOR = "c-minor"
    G_MINOR = "g-minor"
    D_MINOR = "d-minor"
    A_MINOR = "a-minor"
    E_MINOR = "e-minor"
    B_MINOR = "b-minor"
    F_SHARP_MINOR = "f-sharp-minor"
    C_SHARP_MINOR = "c-sharp-minor"
    G_SHARP_MINOR = "g-sharp-minor"
    D_SHARP_MINOR = "d-sharp-minor"
    A_SHARP_MINOR = "a-sharp-minor"


KEY_TO_MUSIC21: dict[KeyChoice, str | None] = {
    KeyChoice.ORIGINAL: None,
    KeyChoice.C_FLAT_MAJOR: "C- major",
    KeyChoice.G_FLAT_MAJOR: "G- major",
    KeyChoice.D_FLAT_MAJOR: "D- major",
    KeyChoice.A_FLAT_MAJOR: "A- major",
    KeyChoice.E_FLAT_MAJOR: "E- major",
    KeyChoice.B_FLAT_MAJOR: "B- major",
    KeyChoice.F_MAJOR: "F major",
    KeyChoice.C_MAJOR: "C major",
    KeyChoice.G_MAJOR: "G major",
    KeyChoice.D_MAJOR: "D major",
    KeyChoice.A_MAJOR: "A major",
    KeyChoice.E_MAJOR: "E major",
    KeyChoice.B_MAJOR: "B major",
    KeyChoice.F_SHARP_MAJOR: "F# major",
    KeyChoice.C_SHARP_MAJOR: "C# major",
    KeyChoice.A_FLAT_MINOR: "A- minor",
    KeyChoice.E_FLAT_MINOR: "E- minor",
    KeyChoice.B_FLAT_MINOR: "B- minor",
    KeyChoice.F_MINOR: "F minor",
    KeyChoice.C_MINOR: "C minor",
    KeyChoice.G_MINOR: "G minor",
    KeyChoice.D_MINOR: "D minor",
    KeyChoice.A_MINOR: "A minor",
    KeyChoice.E_MINOR: "E minor",
    KeyChoice.B_MINOR: "B minor",
    KeyChoice.F_SHARP_MINOR: "F# minor",
    KeyChoice.C_SHARP_MINOR: "C# minor",
    KeyChoice.G_SHARP_MINOR: "G# minor",
    KeyChoice.D_SHARP_MINOR: "D# minor",
    KeyChoice.A_SHARP_MINOR: "A# minor",
}


class HymnRecord(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(pattern=HYMN_ID_PATTERN)
    title: str
    available: bool
    original_key: str | None = None
    available_lines: list[str]
    lyrics_scope: str | None = None
    rights_status: str | None = None


class RenderChoices(BaseModel):
    keys: list[str]
    lines: list[str]
    clefs: list[str]
    octaves: list[str]
    page_sizes: list[str]


class CatalogResponse(BaseModel):
    hymns: list[HymnRecord]
    render_choices: RenderChoices


class HealthResponse(BaseModel):
    status: str
    catalog_entries: int
    catalog_sources_available: int


class RenderParameters(BaseModel):
    hymn_id: str = Field(pattern=HYMN_ID_PATTERN)
    key: KeyChoice
    line: RenderLine
    clef: ClefChoice
    octave: OctavePlacement
    page_size: PageSize
