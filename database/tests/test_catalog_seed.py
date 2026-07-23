from __future__ import annotations

import json
from pathlib import Path

from database.scripts.catalog_seed import DEFAULT_CATALOG, render_seed


def test_seed_contains_every_catalog_id() -> None:
    catalog = json.loads(DEFAULT_CATALOG.read_text(encoding="utf-8"))
    sql = render_seed()

    assert sql.count("INSERT INTO app.catalog_hymns") == len(catalog["items"])
    for item in catalog["items"]:
        assert f"'{item['id']}'" in sql
    assert "'hymns-to-god-public-domain-usa'" in sql
    assert "'great-is-thy-faithfulness'" in sql


def test_seed_is_idempotent_and_does_not_override_publication_status() -> None:
    sql = render_seed()

    assert "ON CONFLICT (id) DO UPDATE" in sql
    assert "publication_status = EXCLUDED.publication_status" not in sql
    assert "ON CONFLICT (hymn_id, component) DO NOTHING" in sql
    assert "SELECT id, component" in sql


def test_seed_escapes_single_quotes(tmp_path: Path) -> None:
    catalog = json.loads(DEFAULT_CATALOG.read_text(encoding="utf-8"))
    catalog["items"][0]["title"] = "Guide Me, O Thou Traveler's Friend"
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(catalog), encoding="utf-8")

    assert "Traveler''s Friend" in render_seed(path)
