from __future__ import annotations

import hashlib
import ast
from collections import Counter, defaultdict
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
from typing import Any

from hymn_ingest import __version__
from hymn_ingest.abc_inventory import write_json
from hymn_ingest.musicxml_validation import validate_musicxml


class ConversionConfigurationError(ValueError):
    """Raised when the inventory or converter configuration is inconsistent."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _trim_stderr(data: bytes, limit: int = 8_000) -> str:
    text = data.decode("utf-8", errors="replace").strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit]}\n... truncated ..."


UNHANDLED_DECORATIONS_RE = re.compile(
    r"unhandled note decorations:\s*(\[.*\])",
    re.IGNORECASE,
)
MAPPING_LOSS_RE = re.compile(
    r"(?:dropped?|ignored|skipped?|unhandled|unsupported).*\bmappings?\b"
    r"|\bmappings?\b.*(?:dropped?|ignored|skipped?|unhandled|unsupported)",
    re.IGNORECASE,
)
EMPTY_VOICE_RE = re.compile(r"\bempty (?:abc )?voices?\b", re.IGNORECASE)
ROUTINE_PREFIXES = (
    "decoded from ",
    "done in ",
    "not a valid staff redirection:",
    "skipped i-field:",
    "skipped header:",
)


def _classify_converter_line(line: str) -> dict[str, Any]:
    message = line.strip()
    if message.startswith("--"):
        message = message[2:].strip()
    decoration_match = UNHANDLED_DECORATIONS_RE.search(message)
    if decoration_match:
        decorations: list[str] = []
        try:
            parsed = ast.literal_eval(decoration_match.group(1))
            if isinstance(parsed, list):
                decorations = [str(value) for value in parsed]
        except (SyntaxError, ValueError):
            pass
        return {
            "code": "unhandled_note_decoration",
            "items": decorations,
            "message": message,
            "severity": "cleanup",
        }
    if MAPPING_LOSS_RE.search(message):
        return {
            "code": "dropped_mapping",
            "message": message,
            "severity": "cleanup",
        }
    if EMPTY_VOICE_RE.search(message):
        return {
            "code": "empty_voice",
            "message": message,
            "severity": "cleanup",
        }
    if message.lower().startswith(ROUTINE_PREFIXES):
        return {
            "code": "converter_info",
            "message": message,
            "severity": "info",
        }
    if re.search(r"\b(?:error|warning|unhandled|dropped?|empty)\b", message, re.IGNORECASE):
        return {
            "code": "unclassified_converter_warning",
            "message": message,
            "severity": "review",
        }
    return {
        "code": "converter_info",
        "message": message,
        "severity": "info",
    }


def classify_converter_stderr(data: bytes) -> list[dict[str, Any]]:
    text = _trim_stderr(data)
    if not text:
        return []
    grouped: dict[tuple[str, str, str, tuple[str, ...]], dict[str, Any]] = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        diagnostic = _classify_converter_line(line)
        key = (
            diagnostic["code"],
            diagnostic["severity"],
            diagnostic["message"],
            tuple(diagnostic.get("items", [])),
        )
        if key not in grouped:
            grouped[key] = {**diagnostic, "count": 0}
        grouped[key]["count"] += 1
    return list(grouped.values())


def _relative(path: Path, base: Path) -> str:
    return os.path.relpath(path, base)


def convert_inventory(
    *,
    inventory_path: Path,
    converter_path: Path,
    converter_version: str,
    output_dir: Path,
    report_path: Path,
    converter_python: Path | None = None,
    timeout_seconds: float = 60.0,
) -> dict[str, Any]:
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    if inventory.get("schema_version") not in {1, 2} or not isinstance(
        inventory.get("tunes"), list
    ):
        raise ConversionConfigurationError("Unsupported or malformed inventory report.")
    if not converter_path.is_file():
        raise ConversionConfigurationError(f"Converter does not exist: {converter_path}")

    python_path = converter_python or Path(sys.executable)
    split_root = (
        inventory_path.parent / str(inventory.get("split_directory", ""))
    ).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    for tune in inventory["tunes"]:
        source_path = split_root / tune["file"]
        output_path = output_dir / f"{Path(tune['file']).stem}.musicxml"
        command = [str(python_path), str(converter_path), str(source_path)]
        started = time.perf_counter()
        return_code: int | None = None
        stdout = b""
        stderr = b""
        launch_error = ""

        try:
            process = subprocess.run(
                command,
                capture_output=True,
                check=False,
                cwd=source_path.parent,
                timeout=timeout_seconds,
            )
            return_code = process.returncode
            stdout = process.stdout
            stderr = process.stderr
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or b""
            stderr = exc.stderr or b""
            launch_error = f"Timed out after {timeout_seconds:g} seconds."
        except OSError as exc:
            launch_error = str(exc)

        elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
        validation = validate_musicxml(stdout)
        status = "succeeded"
        errors: list[dict[str, str]] = list(validation.errors)
        warnings: list[dict[str, str]] = list(validation.warnings)

        converter_diagnostics = classify_converter_stderr(stderr)
        warnings.extend(
            {
                key: value
                for key, value in diagnostic.items()
                if key != "severity"
            }
            for diagnostic in converter_diagnostics
            if diagnostic["severity"] in {"cleanup", "review"}
        )
        if launch_error:
            status = "failed"
            errors.insert(0, {"code": "converter_launch_error", "message": launch_error})
        elif return_code != 0:
            status = "failed"
            errors.insert(
                0,
                {
                    "code": "converter_exit_nonzero",
                    "message": f"Converter exited with status {return_code}.",
                },
            )
        elif not validation.valid:
            status = "invalid"

        output_sha256 = ""
        if stdout:
            output_path.write_bytes(stdout)
            output_sha256 = hashlib.sha256(stdout).hexdigest()

        results.append(
            {
                "clean": status == "succeeded" and not warnings,
                "cleanup_required": status == "succeeded" and bool(warnings),
                "converter_diagnostics": converter_diagnostics,
                "elapsed_ms": elapsed_ms,
                "errors": errors,
                "input_file": tune["file"],
                "input_sha256": tune["sha256"],
                "musicxml_file": (
                    _relative(output_path, report_path.parent) if stdout else None
                ),
                "musicxml_sha256": output_sha256 or None,
                "ordinal": tune["ordinal"],
                "reference": tune["reference"],
                "return_code": return_code,
                "stats": validation.stats,
                "status": status,
                "title": tune["primary_title"],
                "warnings": warnings,
            }
        )

    succeeded = sum(result["status"] == "succeeded" for result in results)
    invalid = sum(result["status"] == "invalid" for result in results)
    failed = sum(result["status"] == "failed" for result in results)
    clean = sum(bool(result["clean"]) for result in results)
    cleanup_required = sum(bool(result["cleanup_required"]) for result in results)
    total = len(results)
    diagnostic_occurrences: Counter[str] = Counter()
    tunes_with_diagnostic: Counter[str] = Counter()
    cleanup_marker_occurrences: Counter[str] = Counter()
    cleanup_marker_tunes: defaultdict[str, set[int]] = defaultdict(set)
    for result in results:
        seen_codes: set[str] = set()
        for diagnostic in result["converter_diagnostics"]:
            code = diagnostic["code"]
            diagnostic_occurrences[code] += diagnostic["count"]
            seen_codes.add(code)
            if code == "unhandled_note_decoration":
                for item in diagnostic.get("items", []):
                    cleanup_marker_occurrences[item] += diagnostic["count"]
                    cleanup_marker_tunes[item].add(result["ordinal"])
        tunes_with_diagnostic.update(seen_codes)

    report: dict[str, Any] = {
        "converter": {
            "declared_version": converter_version,
            "path": _relative(converter_path, report_path.parent),
            "python": str(python_path),
            "sha256": _sha256_file(converter_path),
        },
        "generator": {
            "name": "hymn_ingest",
            "version": __version__,
        },
        "inventory": {
            "path": _relative(inventory_path, report_path.parent),
            "sha256": _sha256_file(inventory_path),
        },
        "runtime": {
            "implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
        },
        "schema_version": 1,
        "summary": {
            "clean": clean,
            "clean_rate": clean / total if total else 0.0,
            "cleanup_marker_occurrences": dict(sorted(cleanup_marker_occurrences.items())),
            "cleanup_marker_tunes": {
                item: len(ordinals)
                for item, ordinals in sorted(cleanup_marker_tunes.items())
            },
            "cleanup_required": cleanup_required,
            "diagnostic_occurrences": dict(sorted(diagnostic_occurrences.items())),
            "failed": failed,
            "invalid": invalid,
            "succeeded": succeeded,
            "success_rate": succeeded / total if total else 0.0,
            "total": total,
            "tunes_with_diagnostic": dict(sorted(tunes_with_diagnostic.items())),
        },
        "tunes": results,
    }
    write_json(report_path, report)
    return report
