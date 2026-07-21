from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Protocol

from render_service.models import (
    KEY_TO_MUSIC21,
    RenderParameters,
)


@dataclass(frozen=True)
class RenderBundle:
    svg_pages: tuple[bytes, ...]
    pdf: bytes
    manifest: dict[str, Any]


class Renderer(Protocol):
    def render(self, source: Path, parameters: RenderParameters) -> RenderBundle: ...


class PipelineRenderer:
    """Thin adapter around the shared hymn_render semantic pipeline."""

    def render(self, source: Path, parameters: RenderParameters) -> RenderBundle:
        # Import lazily so health/catalog endpoints do not load the relatively
        # heavy notation toolchain, and HTTP tests can inject a small fake.
        from hymn_render.core import run_pipeline

        with TemporaryDirectory(prefix="hymn-render-api-") as temporary:
            output_dir = Path(temporary)
            run_pipeline(
                source,
                output_dir,
                line_name=parameters.line.value,
                target_key_name=KEY_TO_MUSIC21[parameters.key],
                clef_name=parameters.clef.value,
                octave_placement=parameters.octave.value,
                page_size=parameters.page_size.value,
            )
            manifest = json.loads(
                (output_dir / "manifest.json").read_text(encoding="utf-8")
            )
            svg_pages = tuple(
                path.read_bytes() for path in sorted(output_dir.glob("page-*.svg"))
            )
            return RenderBundle(
                svg_pages=svg_pages,
                pdf=(output_dir / "score.pdf").read_bytes(),
                manifest=manifest,
            )
