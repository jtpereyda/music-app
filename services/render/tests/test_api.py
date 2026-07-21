from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from render_service.app import create_app
from render_service.catalog import (
    CatalogConfigurationError,
    CatalogEntry,
    HymnCatalog,
)
from render_service.models import RenderParameters
from render_service.renderer import RenderBundle


class FakeRenderer:
    def __init__(self) -> None:
        self.calls: list[tuple[Path, RenderParameters]] = []

    def render(self, source: Path, parameters: RenderParameters) -> RenderBundle:
        self.calls.append((source, parameters))
        resolved = {"original": 0, "auto": 0, "up": 1, "down": -1}[
            parameters.octave.value
        ]
        return RenderBundle(
            svg_pages=(
                b'<svg xmlns="http://www.w3.org/2000/svg"><text>one</text></svg>',
                b'<svg xmlns="http://www.w3.org/2000/svg"><text>two</text></svg>',
            ),
            pdf=b"%PDF-1.7\nfake\n%%EOF\n",
            manifest={
                "render": {"page_count": 2},
                "transform": {
                    "octave_algorithm_version": "staff-position-majority-v1",
                    "octave_requested": parameters.octave.value,
                    "octave_resolved": resolved,
                },
            },
        )


def make_client(tmp_path: Path) -> tuple[TestClient, FakeRenderer]:
    source = tmp_path / "amazing.musicxml"
    source.write_text("<score-partwise/>", encoding="utf-8")
    catalog = HymnCatalog(
        root=tmp_path,
        entries=(
            CatalogEntry("amazing-grace", "Amazing Grace", source.name),
        ),
    )
    renderer = FakeRenderer()
    return TestClient(create_app(catalog=catalog, renderer=renderer)), renderer


def test_health_and_catalog_report_injected_source(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {
        "status": "ok",
        "catalog_entries": 1,
        "catalog_sources_available": 1,
    }

    catalog = client.get("/v1/catalog")
    assert catalog.status_code == 200
    payload = catalog.json()
    assert payload["hymns"] == [
        {
            "id": "amazing-grace",
            "title": "Amazing Grace",
            "available": True,
            "original_key": None,
            "available_lines": ["SATB", "S", "A", "T", "B"],
            "lyrics_scope": None,
            "rights_status": None,
        }
    ]
    assert payload["render_choices"]["lines"] == [
        "satb",
        "soprano",
        "alto",
        "tenor",
        "bass",
    ]
    assert "d-major" in payload["render_choices"]["keys"]
    assert payload["render_choices"]["octaves"] == [
        "auto",
        "original",
        "up",
        "down",
    ]


def test_svg_preview_passes_validated_options_and_page(tmp_path: Path) -> None:
    client, renderer = make_client(tmp_path)

    response = client.get(
        "/v1/hymns/amazing-grace/preview.svg",
        params={
            "key": "d-major",
            "line": "alto",
            "clef": "bass",
            "octave": "auto",
            "page_size": "a4",
            "page": 2,
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")
    assert response.headers["x-page-count"] == "2"
    assert response.headers["x-octave-placement"] == "auto"
    assert response.headers["x-octave-shift"] == "0"
    assert response.headers["x-octave-algorithm"] == "staff-position-majority-v1"
    assert b"<text>two</text>" in response.content
    assert len(renderer.calls) == 1
    source, parameters = renderer.calls[0]
    assert source.name == "amazing.musicxml"
    assert parameters.model_dump(mode="json") == {
        "hymn_id": "amazing-grace",
        "key": "d-major",
        "line": "alto",
        "clef": "bass",
        "octave": "auto",
        "page_size": "a4",
    }


def test_pdf_is_downloadable(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)

    response = client.get(
        "/v1/hymns/amazing-grace/score.pdf",
        params={"line": "bass", "key": "original"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].startswith("attachment;")
    assert response.headers["x-octave-placement"] == "original"
    assert response.headers["x-octave-shift"] == "0"
    assert response.content.startswith(b"%PDF")


def test_enum_validation_rejects_unknown_inputs(tmp_path: Path) -> None:
    client, renderer = make_client(tmp_path)

    bad_hymn = client.get("/v1/hymns/../../etc/passwd/score.pdf")
    unknown_hymn = client.get("/v1/hymns/not-in-the-catalog/score.pdf")
    bad_key = client.get(
        "/v1/hymns/amazing-grace/score.pdf", params={"key": "../../secret"}
    )
    bad_line = client.get(
        "/v1/hymns/amazing-grace/preview.svg", params={"line": "melody"}
    )
    bad_clef = client.get(
        "/v1/hymns/amazing-grace/preview.svg", params={"clef": "percussion"}
    )
    bad_page_size = client.get(
        "/v1/hymns/amazing-grace/score.pdf", params={"page_size": "legal"}
    )
    bad_octave = client.get(
        "/v1/hymns/amazing-grace/score.pdf", params={"octave": "two-up"}
    )

    assert bad_hymn.status_code in {404, 422}
    assert unknown_hymn.status_code == 404
    assert bad_key.status_code == 422
    assert bad_line.status_code == 422
    assert bad_clef.status_code == 422
    assert bad_page_size.status_code == 422
    assert bad_octave.status_code == 422
    assert renderer.calls == []


def test_satb_manual_octave_shift_is_rejected_before_render(tmp_path: Path) -> None:
    client, renderer = make_client(tmp_path)
    response = client.get(
        "/v1/hymns/amazing-grace/score.pdf",
        params={"line": "satb", "octave": "down"},
    )
    assert response.status_code == 422
    assert "individual lines" in response.json()["detail"]
    assert renderer.calls == []


def test_preview_page_bounds_are_checked(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    response = client.get(
        "/v1/hymns/amazing-grace/preview.svg", params={"page": 3}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Rendered score has 2 page(s)."


def test_missing_deployed_source_returns_503(tmp_path: Path) -> None:
    catalog = HymnCatalog(
        root=tmp_path,
        entries=(
            CatalogEntry(
                "amazing-grace", "Amazing Grace", "missing.musicxml"
            ),
        ),
    )
    renderer = FakeRenderer()
    client = TestClient(create_app(catalog=catalog, renderer=renderer))

    response = client.get("/v1/hymns/amazing-grace/score.pdf")

    assert response.status_code == 503
    assert "not deployed" in response.json()["detail"]
    assert renderer.calls == []


def test_catalog_paths_cannot_escape_root(tmp_path: Path) -> None:
    catalog = HymnCatalog(
        root=tmp_path,
        entries=(
            CatalogEntry("amazing-grace", "Amazing Grace", "../secret.xml"),
        ),
    )

    try:
        catalog.resolve_source("amazing-grace")
    except CatalogConfigurationError:
        pass
    else:
        raise AssertionError("Catalog traversal should have been rejected.")
