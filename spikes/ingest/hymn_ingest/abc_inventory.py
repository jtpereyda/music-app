from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import unicodedata

from hymn_ingest import __version__


REFERENCE_RE = re.compile(r"^X:[ \t]*(.*?)[ \t]*\r?\n?$")
HEADER_RE = re.compile(r"^([A-Za-z]):[ \t]*(.*?)[ \t]*\r?\n?$")
INCLUDE_RE = re.compile(r"^[ \t]*%%abc-include(?:[ \t]+|$)", re.IGNORECASE)


class ABCInventoryError(ValueError):
    """Raised when a source cannot be treated as a multi-tune ABC file."""


@dataclass(frozen=True)
class TuneBlock:
    ordinal: int
    source_line_start: int
    source_line_end: int
    preamble: str
    body: str
    headers: dict[str, list[str]]

    @property
    def text(self) -> str:
        return f"{self.preamble}{self.body}"

    @property
    def reference(self) -> str:
        values = self.headers.get("X", [])
        return values[0].strip() if values else ""

    @property
    def titles(self) -> list[str]:
        return [value.strip() for value in self.headers.get("T", []) if value.strip()]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _parse_headers(lines: list[str]) -> dict[str, list[str]]:
    headers: defaultdict[str, list[str]] = defaultdict(list)
    for line in lines:
        match = HEADER_RE.match(line)
        if not match:
            continue
        field, value = match.groups()
        field = field.upper()
        headers[field].append(value)
        if field == "K":
            break
    return dict(headers)


def split_tunes(text: str) -> tuple[str, list[TuneBlock]]:
    lines = text.splitlines(keepends=True)
    starts = [index for index, line in enumerate(lines) if REFERENCE_RE.match(line)]
    if not starts:
        raise ABCInventoryError("No tune boundary found; expected at least one line beginning with X:")

    preamble = "".join(lines[: starts[0]])
    tunes: list[TuneBlock] = []
    for offset, start in enumerate(starts):
        end = starts[offset + 1] if offset + 1 < len(starts) else len(lines)
        tune_lines = lines[start:end]
        tunes.append(
            TuneBlock(
                ordinal=offset + 1,
                source_line_start=start + 1,
                source_line_end=end,
                preamble=preamble,
                body="".join(tune_lines),
                headers=_parse_headers(tune_lines),
            )
        )
    return preamble, tunes


def _slug(value: str, *, fallback: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    return slug[:64] or fallback


def _warning(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def _tune_warnings(tune: TuneBlock, duplicate_references: set[str]) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    if not tune.reference:
        warnings.append(_warning("missing_reference", "The X: field is empty."))
    elif tune.reference in duplicate_references:
        warnings.append(
            _warning("duplicate_reference", f"X:{tune.reference} occurs more than once.")
        )
    if not tune.titles:
        warnings.append(_warning("missing_title", "No non-empty T: field was found before K:."))
    if not tune.headers.get("K"):
        warnings.append(_warning("missing_key", "No K: field was found in the ABC header."))
    if any(INCLUDE_RE.match(line) for line in tune.text.splitlines()):
        warnings.append(
            _warning(
                "abc_include",
                "Tune uses %%abc-include; referenced files are not copied by this spike.",
            )
        )
    return warnings


def build_inventory(
    *,
    input_path: Path,
    split_dir: Path,
    report_path: Path,
    source_encoding: str = "utf-8",
    expected_raw_bytes: int | None = None,
    expected_raw_sha256: str | None = None,
    expected_normalized_utf8_bytes: int | None = None,
    expected_normalized_utf8_sha256: str | None = None,
    expected_tune_count: int | None = None,
) -> dict[str, object]:
    source_bytes = input_path.read_bytes()
    try:
        source_text = source_bytes.decode(source_encoding)
    except LookupError as exc:
        raise ABCInventoryError(f"Unknown source encoding {source_encoding!r}.") from exc
    except UnicodeDecodeError as exc:
        raise ABCInventoryError(
            f"Source is not valid {source_encoding}: {exc}"
        ) from exc

    preamble, tunes = split_tunes(source_text)
    normalized_utf8_bytes = source_text.encode("utf-8")
    raw_sha256 = sha256_bytes(source_bytes)
    normalized_utf8_sha256 = sha256_bytes(normalized_utf8_bytes)
    expected_values = (
        ("raw byte count", expected_raw_bytes, len(source_bytes)),
        ("raw SHA-256", expected_raw_sha256, raw_sha256),
        (
            "normalized UTF-8 byte count",
            expected_normalized_utf8_bytes,
            len(normalized_utf8_bytes),
        ),
        (
            "normalized UTF-8 SHA-256",
            expected_normalized_utf8_sha256,
            normalized_utf8_sha256,
        ),
        ("tune count", expected_tune_count, len(tunes)),
    )
    for label, expected, actual in expected_values:
        if expected is not None and str(expected).lower() != str(actual).lower():
            raise ABCInventoryError(
                f"Source lock mismatch for {label}: expected {expected}, got {actual}."
            )

    reference_counts: defaultdict[str, int] = defaultdict(int)
    for tune in tunes:
        if tune.reference:
            reference_counts[tune.reference] += 1
    duplicate_references = {
        reference for reference, count in reference_counts.items() if count > 1
    }

    split_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, object]] = []

    for tune in tunes:
        primary_title = tune.titles[0] if tune.titles else ""
        reference_slug = _slug(tune.reference, fallback="no-reference")
        title_slug = _slug(primary_title, fallback="untitled")
        filename = f"{tune.ordinal:04d}-x{reference_slug}-{title_slug}.abc"
        output_path = split_dir / filename
        with output_path.open("w", encoding="utf-8", newline="") as output:
            output.write(tune.text)

        warnings = _tune_warnings(tune, duplicate_references)
        entries.append(
            {
                "composer": tune.headers.get("C", [""])[0],
                "file": filename,
                "headers": tune.headers,
                "key": tune.headers.get("K", [""])[0],
                "meter": tune.headers.get("M", [""])[0],
                "ordinal": tune.ordinal,
                "primary_title": primary_title,
                "reference": tune.reference,
                "sha256": sha256_bytes(tune.text.encode("utf-8")),
                "source_line_end": tune.source_line_end,
                "source_line_start": tune.source_line_start,
                "titles": tune.titles,
                "unit_note_length": tune.headers.get("L", [""])[0],
                "warnings": warnings,
            }
        )

    warning_count = sum(len(entry["warnings"]) for entry in entries)
    report = {
        "generator": {
            "name": "hymn_ingest",
            "version": __version__,
        },
        "preamble_sha256": sha256_bytes(preamble.encode("utf-8")),
        "schema_version": 2,
        "source": {
            "encoding": source_encoding,
            "normalized_utf8": {
                "bytes": len(normalized_utf8_bytes),
                "sha256": normalized_utf8_sha256,
            },
            "path": os.path.relpath(input_path, report_path.parent),
            "raw": {
                "bytes": len(source_bytes),
                "sha256": raw_sha256,
            },
        },
        "split_directory": os.path.relpath(split_dir, report_path.parent),
        "summary": {
            "duplicate_reference_count": len(duplicate_references),
            "tune_count": len(entries),
            "warning_count": warning_count,
        },
        "tunes": entries,
    }
    write_json(report_path, report)
    return report


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as output:
        json.dump(value, output, indent=2, sort_keys=True, ensure_ascii=False)
        output.write("\n")
