# Transposify

Technical-preview web app for producing practical editions from structured
music data. Its first live use case is a hymn transposer: a user chooses one of
262 catalog hymns, a target key, full SATB or an individual S/A/T/B line, a
display clef, automatic or manual octave placement, and US Letter or A4 output.
The app then engraves a live SVG preview and a print-sized PDF.

## What is canonical

MusicXML under `catalog/scores` is the canonical music representation. It
contains notes, rhythms, voices, key signatures, lyrics, and other notation
semantics. SVG and PDF are derived output only: they are not parsed back into
notes. A PDF-only input would require optical music recognition plus human
correction.

All 262 records are explicitly marked
`technical_candidate_not_production_approved`. The source and conversion are
appropriate for product development, but production publication still requires
independent rights evidence for each text, translation, tune, and setting.

## Architecture

- `catalog/`: generated 262-hymn catalog and canonical MusicXML
- `spikes/ingest/`: reproducible ABC inventory and MusicXML conversion
- `spikes/render/`: MusicXML line selection, transposition, clef
  representation, SVG engraving, and PDF generation
- `services/render/`: FastAPI catalog and render endpoints
- `apps/web/`: Transposify homepage, hymn use-case pages, live preview, and
  checked download proxy
- `output/pdf/`: visually verified sample editions
- `docs/phase-0-report.md`: spike results and launch recommendation

## Run locally

Python 3.12+ and Node.js 20.9+ are required.

```bash
python -m venv .venv
.venv/bin/python -m pip install -e spikes/render -e 'services/render[test]'
.venv/bin/uvicorn render_service.app:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```bash
cd apps/web
npm install
cp .env.example .env.local
npm run dev
```

Open <http://127.0.0.1:3000>. API documentation is available at
<http://127.0.0.1:8000/docs>.

## Verify

```bash
PYTHONPATH=spikes/ingest .venv/bin/python -m pytest -q spikes/ingest/tests
PYTHONPATH=spikes/render .venv/bin/python -m pytest -q spikes/render/tests
PYTHONPATH=services/render:spikes/render \
  .venv/bin/python -m pytest -q services/render/tests
.venv/bin/python catalog/scripts/validate_catalog.py
.venv/bin/python -m pytest -q catalog/tests

cd apps/web
npm run typecheck
npm run lint
npm run build
npm audit
```

See `services/render/README.md` for the HTTP contract and deployment caveats.
