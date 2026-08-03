from __future__ import annotations

import hashlib

from fastapi import FastAPI, HTTPException, Query, Response

from render_service import __version__
from render_service.catalog import (
    CatalogConfigurationError,
    CatalogSourceUnavailable,
    HymnCatalog,
    UnknownHymnId,
)
from render_service.models import (
    CatalogResponse,
    ClefChoice,
    HealthResponse,
    HymnRecord,
    KeyChoice,
    OctavePlacement,
    PageSize,
    RenderChoices,
    RenderLine,
    RenderParameters,
)
from render_service.renderer import PipelineRenderer, Renderer


def _artifact_headers(
    *,
    data: bytes,
    score_id: str,
    page_count: int,
    disposition: str,
    octave_requested: str,
    octave_resolved: int,
    octave_algorithm_version: str,
) -> dict[str, str]:
    return {
        "Cache-Control": "private, max-age=0, must-revalidate",
        "Content-Disposition": disposition,
        "ETag": f'"{hashlib.sha256(data).hexdigest()}"',
        "X-Score-Id": score_id,
        "X-Hymn-Id": score_id,
        "X-Octave-Algorithm": octave_algorithm_version,
        "X-Octave-Placement": octave_requested,
        "X-Octave-Shift": str(octave_resolved),
        "X-Page-Count": str(page_count),
    }


def create_app(
    *,
    catalog: HymnCatalog | None = None,
    renderer: Renderer | None = None,
) -> FastAPI:
    service_catalog = catalog or HymnCatalog()
    service_renderer = renderer or PipelineRenderer()
    app = FastAPI(
        title="Score Render Service",
        version=__version__,
        description=(
            "Renders fixed-catalog MusicXML sources as SVG previews and PDFs."
        ),
    )

    @app.get("/health", response_model=HealthResponse, tags=["service"])
    def health() -> HealthResponse:
        entries = service_catalog.entries()
        available = sum(
            service_catalog.source_available(entry.hymn_id) for entry in entries
        )
        return HealthResponse(
            status="ok" if available == len(entries) else "degraded",
            catalog_entries=len(entries),
            catalog_sources_available=available,
        )

    @app.get("/v1/catalog", response_model=CatalogResponse, tags=["catalog"])
    def get_catalog() -> CatalogResponse:
        scores = [
            HymnRecord(
                id=entry.hymn_id,
                content_type=entry.content_type,
                title=entry.title,
                available=service_catalog.source_available(entry.hymn_id),
                original_key=entry.original_key,
                available_lines=list(entry.available_lines),
                lyrics_scope=entry.lyrics_scope,
                rights_status=entry.rights_status,
            )
            for entry in service_catalog.entries()
        ]
        return CatalogResponse(
            scores=scores,
            hymns=[score for score in scores if score.content_type == "hymn"],
            render_choices=RenderChoices(
                keys=[item.value for item in KeyChoice],
                lines=[item.value for item in RenderLine],
                clefs=[item.value for item in ClefChoice],
                octaves=[item.value for item in OctavePlacement],
                page_sizes=[item.value for item in PageSize],
            ),
        )

    def render_bundle(
        score_id: str,
        key: KeyChoice,
        line: RenderLine,
        clef: ClefChoice,
        octave: OctavePlacement,
        page_size: PageSize,
    ):
        try:
            entry = service_catalog.entry(score_id)
        except UnknownHymnId as exc:
            raise HTTPException(status_code=404, detail="Score not found.") from exc

        requested_line = {
            RenderLine.SCORE: "SCORE",
            RenderLine.SATB: "SATB",
            RenderLine.SOPRANO: "S",
            RenderLine.ALTO: "A",
            RenderLine.TENOR: "T",
            RenderLine.BASS: "B",
        }[line]
        if requested_line not in entry.available_lines:
            raise HTTPException(
                status_code=422,
                detail=f"{line.value!r} is not available for this score.",
            )
        if line in {RenderLine.SCORE, RenderLine.SATB} and octave in {
            OctavePlacement.UP,
            OctavePlacement.DOWN,
        }:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Explicit octave shifts are available only for individual lines."
                ),
            )
        if line == RenderLine.SCORE and clef != ClefChoice.ORIGINAL:
            raise HTTPException(
                status_code=422,
                detail="Full scores preserve their original clefs.",
            )
        try:
            source = service_catalog.resolve_source(score_id)
        except CatalogSourceUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except CatalogConfigurationError as exc:
            raise HTTPException(
                status_code=500, detail="The server catalog is misconfigured."
            ) from exc

        parameters = RenderParameters(
            hymn_id=score_id,
            source_key_name=entry.original_key,
            key=key,
            line=line,
            clef=clef,
            octave=octave,
            page_size=page_size,
        )
        try:
            return service_renderer.render(source, parameters)
        except ValueError as exc:
            # hymn_render.RenderError is a ValueError. This is a semantic
            # rejection of a validly shaped request, not an arbitrary 500.
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get(
        "/v1/hymns/{score_id}/preview.svg",
        response_class=Response,
        responses={200: {"content": {"image/svg+xml": {}}}},
        tags=["render"],
        include_in_schema=False,
    )
    @app.get(
        "/v1/scores/{score_id}/preview.svg",
        response_class=Response,
        responses={200: {"content": {"image/svg+xml": {}}}},
        tags=["render"],
    )
    def preview_svg(
        score_id: str,
        key: KeyChoice = Query(KeyChoice.ORIGINAL),
        line: RenderLine = Query(RenderLine.SATB),
        clef: ClefChoice = Query(ClefChoice.ORIGINAL),
        octave: OctavePlacement = Query(OctavePlacement.ORIGINAL),
        page_size: PageSize = Query(PageSize.LETTER),
        page: int = Query(1, ge=1),
    ) -> Response:
        bundle = render_bundle(score_id, key, line, clef, octave, page_size)
        if page > len(bundle.svg_pages):
            raise HTTPException(
                status_code=404,
                detail=f"Rendered score has {len(bundle.svg_pages)} page(s).",
            )
        svg = bundle.svg_pages[page - 1]
        transform = bundle.manifest["transform"]
        return Response(
            content=svg,
            media_type="image/svg+xml",
            headers=_artifact_headers(
                data=svg,
                score_id=score_id,
                page_count=len(bundle.svg_pages),
                octave_requested=transform["octave_requested"],
                octave_resolved=transform["octave_resolved"],
                octave_algorithm_version=transform["octave_algorithm_version"],
                disposition=(
                    f'inline; filename="{score_id}-{line.value}-'
                    f'{octave.value}-page-{page:03d}.svg"'
                ),
            ),
        )

    @app.get(
        "/v1/hymns/{score_id}/score.pdf",
        response_class=Response,
        responses={200: {"content": {"application/pdf": {}}}},
        tags=["render"],
        include_in_schema=False,
    )
    @app.get(
        "/v1/scores/{score_id}/score.pdf",
        response_class=Response,
        responses={200: {"content": {"application/pdf": {}}}},
        tags=["render"],
    )
    def download_pdf(
        score_id: str,
        key: KeyChoice = Query(KeyChoice.ORIGINAL),
        line: RenderLine = Query(RenderLine.SATB),
        clef: ClefChoice = Query(ClefChoice.ORIGINAL),
        octave: OctavePlacement = Query(OctavePlacement.ORIGINAL),
        page_size: PageSize = Query(PageSize.LETTER),
    ) -> Response:
        bundle = render_bundle(score_id, key, line, clef, octave, page_size)
        transform = bundle.manifest["transform"]
        return Response(
            content=bundle.pdf,
            media_type="application/pdf",
            headers=_artifact_headers(
                data=bundle.pdf,
                score_id=score_id,
                page_count=len(bundle.svg_pages),
                octave_requested=transform["octave_requested"],
                octave_resolved=transform["octave_resolved"],
                octave_algorithm_version=transform["octave_algorithm_version"],
                disposition=(
                    f'attachment; filename="{score_id}-{line.value}-'
                    f'{key.value}-{octave.value}.pdf"'
                ),
            ),
        )

    return app


app = create_app()
