# Phase 0 spike report

Date: 2026-07-20 UTC

## Decision

**Proceed with a curated MVP; do not bulk-publish the full source catalog yet.**

The core technical path works:

1. ingest ABC into semantic MusicXML;
2. retain full SATB or select soprano, alto, tenor, or bass;
3. transpose the actual pitches and key signature;
4. change the displayed clef without changing pitches;
5. render every page to SVG with Verovio; and
6. convert the exact SVG pages to print-sized PDF.

MusicXML is the canonical database representation. The pinned ABC is retained
as import evidence. SVG and PDF are disposable output formats. They should not
be parsed back into notes: PDF discards notation semantics, and renderer SVG
structure is not a stable musical interchange format. A PDF-only source would
require optical music recognition and human correction.

The two constraints on an automated full-catalog launch are source provenance
and conversion fidelity, not the basic transpose/render mechanics.

## Data and rights spike

The official Open Hymnal resources are hash-pinned under
`data/open-hymnal/raw`, with a machine-readable rights manifest and full audit
in `docs/source-audit.md`.

- combined source: 293 records, 275 exact-PD-declaration candidates;
- split ZIP: 306 files, 285 exact-PD-declaration candidates;
- 20 split entries are restricted and one is ambiguous;
- the two resources share the label `2014.06` but contain different, mutable
  payloads with later revisions; and
- official ABC downloads are available only over unauthenticated HTTP.

These snapshots are acceptable for an offline technical spike. They are not
sufficient production provenance by themselves. Each production score still
needs evidence for text, translation, melody, and setting/harmonization.

## Bulk ingestion result

The pinned `abc2xml.py` release 268 converted all 293 records from the combined
source:

- 293 structurally valid MusicXML files;
- 0 invalid files;
- 0 converter failures;
- 2 clean under the strict fidelity-warning definition; and
- 291 requiring visual review or marker cleanup.

The gap between structural and clean success is dominated by source-specific
decorations:

- `sintro`: 291 occurrences, 290 affected tunes;
- `eintro`: 291 occurrences, 290 affected tunes;
- `invertedfermata`: 143 occurrences, 48 affected tunes;
- four dropped multi-staff mappings across two tunes;
- three empty-voice warnings; and
- one lyric-extend warning.

The intro markers describe engraving details rather than notes, so they do not
invalidate the catalog data. They do prevent a claim that all 293 scores are
production-clean without visual review or explicit marker translation.

## Transformation contract

The rendering spike enforces these separate operations:

- `line`: `satb`, `soprano`, `alto`, `tenor`, or `bass`;
- `target key`: transposes sounding pitches and the key signature using the
  nearest correctly spelled interval;
- `clef`: `original`, `treble`, `bass`, `alto`, `tenor`, or `treble-8vb`;
- clef replacement is pitch-invariant; and
- every output records hashes and pitch fingerprints in `manifest.json`.

The Open Hymnal conversion yields two staves and four voices in S, A, T, B
order. The spike rejects individual-line extraction when four voices are not
present rather than guessing.

Lyrics are attached to the soprano voice in this source. Soprano extraction
therefore keeps lyrics; alto, tenor, and bass extraction currently produces
note-only parts. Automatically copying soprano lyrics to another rhythmic line
would be musically unsafe. The MVP should present this behavior explicitly,
with lyric alignment treated as a separate catalog-cleanup feature.

## Render quality sample

Seven variants across six exact-PD-declaration candidates were rendered to
single-page US Letter PDFs and visually inspected after rasterizing with
Poppler:

| Hymn | Output | Result |
| --- | --- | --- |
| O For A Thousand Tongues | SATB, D major, original clefs | Pass |
| O For A Thousand Tongues | bass line, D major, bass clef | Pass; note-only |
| Amazing Grace | soprano line, D major, bass clef | Pass; lyrics retained |
| Beneath The Cross Of Jesus | SATB, F major | Pass; five stacked verses |
| Blessed Assurance | SATB, E-flat major | Pass; refrain and three verses |
| It Is Well With My Soul | SATB, G major | Pass; five verses and refrain |
| Come Thou Fount Of Every Blessing | alto line, B-flat major, alto clef | Pass; note-only |

The first visual pass exposed three issues that machine validation did not:

- a tempo-note glyph was missing during SVG-to-PDF conversion;
- a generic MIDI piano name appeared as a staff label; and
- dense five-verse pages could overflow the physical Letter boundary.

The print pipeline now omits non-portable tempo glyphs, removes generic MIDI
labels, preserves the real hymn title, increases inter-word lyric spacing, and
uses a Letter layout that keeps dense sample scores within the physical page.

## Verification

- ingestion tests: 12 passed;
- render/transform tests: 7 passed;
- real transformed scores reparsed with their requested keys and clefs;
- every sample manifest page count matches its SVG and PDF page counts;
- every PDF is exactly 612 x 792 points; and
- all seven final PDFs were rendered to PNG and visually inspected.

## Next implementation step

Build the product around MusicXML rather than around SVG/PDF:

- curated, provenance-approved catalog records point to immutable MusicXML;
- the web UI offers hymn, key, SATB line, clef, and page-size controls;
- Verovio SVG is the live preview;
- the Python renderer produces the download PDF and semantic manifest; and
- catalog promotion requires both rights approval and a visual-render QA flag.
