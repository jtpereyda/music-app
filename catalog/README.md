# Technical-preview catalog

This directory contains 262 untransposed canonical MusicXML scores selected for
technical pipeline work from the pinned Open Hymnal 2014.06 combined ABC file.
Every included record has:

- an exact source declaration beginning `copyright: public domain.`;
- structurally valid converter output;
- two MusicXML parts and four voice locations; and
- lyrics on first-part voice 1.

The source has 293 records. Eighteen are held by the existing rights gate, and
13 otherwise eligible records are held because their staff/voice structure is
not compatible with the current SATB line selector. `import-report.json`
accounts for every source record and names each hold.

The scores were converted with pinned `abc2xml.py` version 268. `catalog.json`
records the normalized source collection hash, per-tune ABC artifact hash,
source ordinal and `X:` reference, exact MusicXML hash, and search/display
metadata. Converter-generated encoding dates are normalized to the catalog
revision date so rebuilding the same pinned inputs is byte-stable.

The converter report flags 260 included records for visual cleanup, primarily
because `sintro`/`eintro` decorations are not represented in MusicXML. This is
compatible with the catalog's technical-preview purpose, but it is not a claim
that the scores have completed engraving QA.

## Rights boundary

Every record preserves an exact source declaration beginning `copyright:
public domain.` That is evidence from the source, not an independent legal
determination. All records intentionally have:

```text
technical_candidate_not_production_approved
```

This catalog is suitable for conversion, transposition, engraving, and preview
tests. It must not be treated as a production rights allowlist until text,
tune, setting, and any translation have been reviewed separately.

## Musical shape

Every catalog score contains two parts and four voice locations corresponding to SATB. The
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
`spikes/ingest/README.md`, then promote only the compatible audited candidates:

```bash
python3 catalog/scripts/build_open_hymnal_catalog.py \
  --inventory /path/to/build/inventory.json \
  --conversion /path/to/build/conversion.json \
  --musicxml-dir /path/to/build/musicxml
```

The promotion step regenerates `catalog.json`, `import-report.json`, canonical
scores, and `apps/web/src/lib/catalog.generated.ts`. It fails closed if pinned
source counts, hashes, rights counts, or the expected 262-item result drift.
