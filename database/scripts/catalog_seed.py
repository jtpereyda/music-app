#!/usr/bin/env python3
"""Render idempotent SQL that mirrors the canonical JSON catalog into Neon."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG = REPOSITORY_ROOT / "catalog" / "catalog.json"


def _literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _jsonb(value: Any) -> str:
    return _literal(json.dumps(value, ensure_ascii=False, separators=(",", ":"))) + "::jsonb"


def _text_array(values: list[str]) -> str:
    return "ARRAY[" + ",".join(_literal(value) for value in values) + "]::text[]"


def render_seed(catalog_path: Path = DEFAULT_CATALOG) -> str:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    revision = int(catalog["catalog_revision"])
    statements = ["BEGIN;"]

    for item in catalog["items"]:
        score = item["score"]
        original_key = item["original_key"]
        source = item["source"]
        rights = item["rights"]
        lyrics = item["lyrics"]
        source_reference = source.get("x_reference") or source.get(
            "record_reference"
        )
        if not isinstance(source_reference, str) or not source_reference:
            raise ValueError(
                f"Catalog item {item['id']!r} has no source record reference."
            )
        values = [
            _literal(item["id"]),
            str(revision),
            _literal(item["title"]),
            _literal(score["path"]),
            _literal(score["sha256"]),
            _literal(score["media_type"]),
            _literal(original_key["name"]),
            _literal(original_key["mode"]),
            str(original_key["fifths"]),
            _text_array(item["available_lines"]),
            _literal(lyrics["scope"]),
            _literal(rights["status"]),
            _literal(source["collection_id"]),
            _literal(source["artifact_sha256"]),
            str(source["record_ordinal"]),
            _literal(source_reference),
            _jsonb(source),
            _jsonb(rights),
            _jsonb(lyrics),
        ]
        statements.append(
            """
INSERT INTO app.catalog_hymns (
    id,
    catalog_revision,
    title,
    score_path,
    score_sha256,
    score_media_type,
    original_key_name,
    original_key_mode,
    original_key_fifths,
    available_lines,
    lyrics_scope,
    source_rights_status,
    source_collection_id,
    source_artifact_sha256,
    source_record_ordinal,
    source_x_reference,
    source_payload,
    rights_payload,
    lyrics_payload
)
VALUES (
    %s
)
ON CONFLICT (id) DO UPDATE SET
    catalog_revision = EXCLUDED.catalog_revision,
    title = EXCLUDED.title,
    score_path = EXCLUDED.score_path,
    score_sha256 = EXCLUDED.score_sha256,
    score_media_type = EXCLUDED.score_media_type,
    original_key_name = EXCLUDED.original_key_name,
    original_key_mode = EXCLUDED.original_key_mode,
    original_key_fifths = EXCLUDED.original_key_fifths,
    available_lines = EXCLUDED.available_lines,
    lyrics_scope = EXCLUDED.lyrics_scope,
    source_rights_status = EXCLUDED.source_rights_status,
    source_collection_id = EXCLUDED.source_collection_id,
    source_artifact_sha256 = EXCLUDED.source_artifact_sha256,
    source_record_ordinal = EXCLUDED.source_record_ordinal,
    source_x_reference = EXCLUDED.source_x_reference,
    source_payload = EXCLUDED.source_payload,
    rights_payload = EXCLUDED.rights_payload,
    lyrics_payload = EXCLUDED.lyrics_payload,
    updated_at = now();
""".strip()
            % ",\n    ".join(values)
        )

    statements.append(
        """
INSERT INTO app.rights_reviews (hymn_id, component)
SELECT id, component
FROM app.catalog_hymns
CROSS JOIN (
    VALUES ('text'), ('translation'), ('tune'), ('setting')
) AS components(component)
ON CONFLICT (hymn_id, component) DO NOTHING;
""".strip()
    )
    statements.append("COMMIT;")
    return "\n\n".join(statements) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--catalog",
        type=Path,
        default=DEFAULT_CATALOG,
        help="Path to the canonical catalog JSON.",
    )
    args = parser.parse_args()
    print(render_seed(args.catalog), end="")


if __name__ == "__main__":
    main()
