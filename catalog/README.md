# Technical-preview catalog

This directory contains 869 untransposed canonical MusicXML scores selected for
technical pipeline work from three pinned source collections. The Open Hymnal
2014.06 combined ABC contributes 269 records, its disagreeing split ZIP
contributes eight compatible records absent from the combined file, and
HymnsToGod contributes 592 public-domain arrangements.
Every included record has:

- source-specific public-domain evidence: either an exact Open Hymnal
  declaration beginning `copyright: public domain.` or a HymnsToGod
  public-domain index/page classification, with explicit contradictory page
  declarations held out;
- structurally valid converter output;
- two MusicXML parts and four voice locations; and
- lyrics on first-part voice 1.

The combined source has 293 records. Eighteen are held by the existing rights
gate, and six otherwise eligible records are held because they are genuinely
3-, 5-, 6-, or 7-voice arrangements rather than the four SATB lines expected by
the current selector. Seven compatible SATB records are admitted through a
versioned deterministic normalization: six split source dyads into independent
voice timelines, one drops a converter-created empty part, and one of the dyad
scores also aligns a converter-skipped lower-staff measure number by sequence.
The split ZIP
has 306 records and 285 exact-public-domain candidates; this revision selects
only the eight non-duplicate additions already compatible with the current
renderer. `import-report.json` separates the combined-source accounting from
the supplemental ZIP selection. The complete HymnsToGod audit found 593 index
pages representing 575 works and 594 musical arrangements. It promotes 592
arrangements. `I Surrender All` is held because its page says `Copyright:
Unknown - USA`; the `Amazing Grace` King David R setting is held because its
page substitutes a Choral Public Domain Library license for the index's normal
public-domain declaration.

The Open Hymnal scores were converted with pinned `abc2xml.py` version 268. The
HymnsToGod scores use the versioned `hymns-to-god-mup-satb` importer, with Mup
7.2 for macro expansion and a fail-closed notation parser for the expanded Mup
statements. `catalog.json` records the relevant source hashes and references,
work and arrangement identities, the exact MusicXML hash, and search/display
metadata. Converter-generated
encoding dates are normalized to the catalog revision date so rebuilding the
same pinned inputs is byte-stable.

The Open Hymnal converter report flags 274 included records for visual cleanup, primarily
because `sintro`/`eintro` decorations are not represented in MusicXML. This is
compatible with the catalog's technical-preview purpose, but it is not a claim
that the scores have completed engraving QA.

## Rights boundary

Every record preserves its source-specific public-domain declaration and raw
source hashes. All records currently share the catalog-wide technical status:

```text
technical_candidate_not_production_approved
```

The HymnsToGod `Public Domain - USA` page declaration is sufficient for this
project's ingest gate; CC0 is not required. The uniform status remains in place
because the catalog also includes the separately qualified Open Hymnal records.

## Musical shape

Every catalog score contains two parts and four semantic voice locations
corresponding to SATB. Divisi passages remain chords inside the relevant
semantic part, so no printed harmony is discarded. The
catalog advertises full SATB plus individually extractable S, A, T, and B
lines. Catalog-supported lyric extraction is intentionally limited to the
soprano voice. The canonical “It Is Well With My Soul” source also contains six
verse-1 syllables on a bass entrance; those incidental source elements are
preserved in MusicXML but are not advertised as general bass-line lyric
availability.

The MusicXML files are canonical, untransposed converter output. Do not
overwrite them with derived keys, clefs, preview layout, or PDF metadata.
Derived artifacts should reference the catalog item ID and canonical score
hash.

## Validate

The validator uses only the Python standard library:

```bash
python3 scripts/validate_catalog.py
python3 -m unittest discover -s tests -v
```

It checks catalog invariants, stable IDs, rights status, source linkage, score
hashes, XML parseability, titles, original keys, four-voice shape, lyric scope,
verse IDs, and converter identity.

## Rebuild from the pinned source

Run the existing inventory and conversion stages described in
`spikes/ingest/README.md`. Prepare the pinned split-ZIP additions with the same
converter:

```bash
python3 catalog/scripts/prepare_open_hymnal_supplement.py \
  --converter /path/to/abc2xml.py \
  --output-root /path/to/build/supplement
```

Then promote the compatible audited candidates:

```bash
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

The promotion step regenerates `catalog.json`, `import-report.json`, canonical
scores, and `apps/web/src/lib/catalog.generated.ts`. It fails closed if pinned
source counts, hashes, rights counts, ZIP entry identities, or the expected
869-item result drift.
