# Technical-preview catalog

This directory contains 2,226 untransposed canonical scores selected for
technical pipeline work from five pinned source collections:

- 269 hymns from the Open Hymnal 2014.06 combined ABC;
- eight compatible, non-duplicate hymns from its split ZIP;
- 592 public-domain HymnsToGod arrangements;
- one Public Domain Mark edition from Timeless Truths; and
- 1,356 CC0 voice-and-piano scores indexed by OpenScore Lieder.

The first four collections provide 870 hymns. OpenScore Lieder provides 1,356
classical art songs. The catalog preserves each source record, canonical score
hash, display metadata, rights declaration, original key and mode, work ID, and
arrangement ID.

## Source and eligibility boundaries

Open Hymnal records must carry an exact declaration beginning `copyright:
public domain.` HymnsToGod records are eligible when the individual page says
`Public Domain - USA`; CC0 is not required for that collection. Contradictory
individual-page declarations remain held out.

The OpenScore Lieder import is pinned to commit
`6b2dc542ce2e8aa4b78c8ee62103b210efc07015` and archive SHA-256
`e925dd89f9dc2ac16f2aff49470d2c1f2dec9977bb4059172cbcbc7a4b98958c`.
Its repository-wide license is Creative Commons Zero 1.0 Universal. The import
promotes all 1,356 rows in `data/scores.tsv`; 106 additional MXL files are
reported but deliberately excluded because they lack an indexed metadata row.
Stable MuseScore IDs reconcile metadata paths with upstream folder renames.

The complete HymnsToGod audit found 593 index pages representing 575 works and
594 arrangements. It promotes 592 arrangements. `I Surrender All` is held
because its page says `Copyright: Unknown - USA`; the `Amazing Grace` King
David R setting is held because its page substitutes a Choral Public Domain
Library license for the index's normal public-domain declaration.

The Timeless Truths addition is `Nothing Between`, an SATB arrangement credited
to F. A. Clark. Its record page and MusicXML identify the score as public
domain, and the page links the Creative Commons Public Domain Mark 1.0. The
pinned Sibelius MusicXML uses a deterministic normalization to split two-staff
dyads into four semantic voices, repair positional lyric-row identifiers, and
remove source-page credits that do not fit the product renderer.

The Open Hymnal combined source has 293 records. Eighteen are rights holds and
six are structural holds because they contain 3, 5, 6, or 7 voices instead of
the four lines expected by the hymn part selector. Seven compatible SATB
records use an audited, versioned deterministic normalization. The converter
report flags 274 included records for visual cleanup, chiefly because
`sintro`/`eintro` decorations are not represented in MusicXML.

## Rights boundary

Every record preserves its source-specific rights declaration and source
hashes. All records currently share the catalog-wide technical status:

```text
technical_candidate_not_production_approved
```

This is a technical ingest and rendering gate, not a claim that every score
has completed independent production rights and engraving review.

## Musical shape

Hymns contain two parts and four semantic voice locations corresponding to
SATB. The catalog advertises full SATB plus individually extractable S, A, T,
and B lines. Catalog-supported lyric extraction is limited to the soprano
voice. Divisi notes remain chords inside the relevant semantic part.

OpenScore Lieder entries advertise one `SCORE` output. The renderer keeps the
voice, piano, and any other encoded parts together, preserving original clefs
and registers while transposing every part by the same interval. A score in a
minor key therefore remains minor after transposition; mode conversion is not
part of the feature. When upstream MusicXML omits its mode, the import records a
deterministic relative-major/minor pitch-profile inference, which the renderer
uses as the source-key authority.

The `.musicxml` and `.mxl` files are canonical, untransposed source artifacts.
Do not overwrite them with derived keys, clefs, preview layout, or PDF
metadata. Derived artifacts should reference the catalog item ID and canonical
score hash.

## Validate

The standard-library validator checks catalog invariants, stable IDs, rights
status, source linkage, score hashes, compressed and uncompressed MusicXML,
titles, keys and modes, advertised output shape, lyric scope, verse IDs, and
converter identity:

```bash
python3 catalog/scripts/validate_catalog.py
```

The full tests also exercise the converters and require the notation
dependencies installed from `spikes/render`:

```bash
python3 -m unittest discover -s catalog/tests -v
```

## Rebuild from the pinned sources

Run the Open Hymnal inventory and conversion stages described in
`spikes/ingest/README.md`, prepare the split-ZIP additions, convert the
HymnsToGod sources, and build the 869-hymn base catalog:

```bash
python3 catalog/scripts/prepare_open_hymnal_supplement.py \
  --converter /path/to/abc2xml.py \
  --output-root /path/to/build/supplement

python3 catalog/scripts/convert_hymns_to_god_mup.py \
  --manifest data/hymns-to-god/manifest.json \
  --source-dir data/hymns-to-god/raw \
  --mup-executable /path/to/mup \
  --output-dir /path/to/build/hymns-to-god/musicxml \
  --conversion-report /path/to/build/hymns-to-god/conversion.json

python3 catalog/scripts/build_open_hymnal_catalog.py \
  --inventory /path/to/build/inventory.json \
  --conversion /path/to/build/conversion.json \
  --musicxml-dir /path/to/build/musicxml \
  --supplement-inventory /path/to/build/supplement/inventory.json \
  --supplement-conversion /path/to/build/supplement/conversion.json \
  --supplement-musicxml-dir /path/to/build/supplement/musicxml \
  --hymns-to-god-musicxml-dir /path/to/build/hymns-to-god/musicxml \
  --hymns-to-god-conversion /path/to/build/hymns-to-god/conversion.json
```

Then extract the pinned OpenScore Lieder archive and apply the deterministic
second-stage import:

```bash
curl -fL \
  https://github.com/OpenScore/Lieder/archive/6b2dc542ce2e8aa4b78c8ee62103b210efc07015.zip \
  --output /tmp/OpenScore-Lieder-6b2dc542.zip

bsdtar -xf /tmp/OpenScore-Lieder-6b2dc542.zip -C /tmp

python3 catalog/scripts/import_openscore_lieder.py \
  --source-root /tmp/Lieder-6b2dc542ce2e8aa4b78c8ee62103b210efc07015

python3 catalog/scripts/import_timeless_truths.py
```

The promotion stages regenerate `catalog.json`, `import-report.json`,
canonical scores, the source manifests, and
`apps/web/src/lib/catalog.generated.ts`. They fail closed if pinned source
counts, hashes, rights gates, record identities, or the expected 870-hymn,
1,356-art-song, and 2,226-total results drift.
