# Render service

FastAPI wrapper around the shared `spikes/render/hymn_render` pipeline. The
service does not parse SVG or PDF to recover notes. It looks up a fixed
MusicXML catalog entry, applies the requested semantic transform once through
`hymn_render`, and returns a derived SVG preview or PDF.

## API

- `GET /health`
- `GET /v1/catalog`
- `GET /v1/scores/{score_id}/preview.svg`
- `GET /v1/scores/{score_id}/score.pdf`

Both render routes accept strictly enumerated `key`, `line`, `clef`, `octave`,
and `page_size` query parameters. `octave` accepts `auto`, `original`, `up`, or
`down`; the default is `original` for backward compatibility. Auto placement
is available for isolated voices and evaluates the selected clef after key
transposition. Full SATB preserves its voicing and rejects manual octave
shifts. A `score` request keeps all parts, original clefs, and original
registers together; this is the supported layout for voice-and-piano art songs.
The SVG route also accepts a one-based `page`. OpenAPI documents the
complete choices at `/docs`; `/v1/catalog` returns them for a frontend without
duplicating constants. Its `scores` field contains the complete catalog and its
legacy `hymns` field remains a hymn-only subset. The API offers `original`, 15 conventional major keys,
and 15 conventional minor keys. The web selector shows only destinations whose
mode matches the source score, and the shared renderer rejects an explicit
major-to-minor or minor-to-major request. A minor score therefore transposes
among minor keys exactly as a major score transposes among major keys.

Example:

```bash
curl \
  'http://127.0.0.1:8000/v1/scores/amazing-grace/preview.svg?key=d-major&line=soprano&clef=bass&octave=auto&page_size=letter' \
  --output amazing-grace-soprano-bass-auto.svg

curl \
  'http://127.0.0.1:8000/v1/scores/amazing-grace/score.pdf?key=d-major&line=soprano&clef=bass&octave=auto&page_size=letter' \
  --output amazing-grace-soprano-bass-auto.pdf
```

Score IDs and score paths load from the canonical repository
`catalog/catalog.json`; the service accepts exactly the IDs present in that
catalog. No request parameter is ever interpreted as a filesystem path.
`HYMNS_CATALOG_PATH` can select another copy of the same catalog, and
`HYMNS_CATALOG_ROOT` can select the root beneath which its fixed score paths
resolve. The root defaults to the catalog file's directory. Resolution rejects
paths that escape that root and verifies each MusicXML file against its
cataloged SHA-256. The catalog endpoint marks missing or mismatched sources
unavailable and render requests for them return HTTP 503.

The former `/v1/hymns/{score_id}/...` paths remain available as undocumented
compatibility aliases for existing clients.

## Local run and test

The semantic pipeline remains a separate local package so API code cannot
silently diverge from the CLI. The requirements file links that package from
the monorepo:

```bash
python -m pip install -r requirements.txt
python -m pip install -e '.[test]' --no-deps
uvicorn render_service.app:app --reload
pytest -q
```

## Vercel

The renderer is the standalone `hymn-transposer-renderer` Vercel project,
rooted at the repository root. `Dockerfile.vercel` packages this service, the
shared rendering pipeline, and the canonical catalog. The root `vercel.json`
declares just this service and routes all project traffic to it. The Vercel
project's custom **Ignored Build Step** skips deployments when none of those
inputs changed, so web-only preview commits do not create container images.

The separate web project is rooted at `apps/web` and receives this project's
stable production URL as the server-only `RENDER_API_URL`. Browser requests
stay same-origin through the checked Next.js proxy.

The canonical records remain technical candidates, not a production rights
allowlist. The full notation stack (`music21`, Verovio, CairoSVG, and pypdf)
is packaged in `Dockerfile.vercel` so Cairo and font dependencies remain
deterministic.
