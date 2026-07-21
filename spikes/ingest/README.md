# Open Hymnal ABC ingestion spike

This directory inventories a multi-tune ABC file, writes one deterministic ABC
fixture per tune, converts each tune with Willem Vree's `abc2xml.py`, validates
the resulting MusicXML structurally, and emits machine-readable JSON reports.
It is deliberately independent of the product application.

## Scope and reproducibility

- Python runtime: 3.12 or 3.13 (the spike itself uses only the standard library).
- ABC converter: `abc2xml.py` release **268**, downloaded from the author's
  versioned archive.
- No global packages or executables are installed.
- Every report records SHA-256 digests for the source ABC, split tune, converter
  script, and generated MusicXML.
- JSON output is stable apart from measured conversion time and runtime version.

`converter.lock.json` pins both reviewed SHA-256 values:

- archive: `7beb1483e1a5c1f744a1faff71dda8f6cd68e1e9c75ab5b44eeeadc30754461f`
- script: `76cd2c5c4fc44b28ab2ce923f196d23d09b93fcefa8cfa90a10754d38e15b56e`

The installer refuses either an archive or extracted script that does not match
the lock.

## Install the pinned converter locally

From `spikes/ingest`:

```bash
mkdir -p .downloads
curl --fail --location \
  https://wim.vree.org/svgParse/abc2xml.py-268.zip \
  --output .downloads/abc2xml.py-268.zip

python3.12 scripts/install_abc2xml.py \
  --archive .downloads/abc2xml.py-268.zip \
  --destination .tools/abc2xml-268
```

This extracts only `abc2xml.py` and writes
`.tools/abc2xml-268/INSTALL-METADATA.json`. Nothing is installed outside this
directory. Review the recorded archive digest before treating the conversion
as a frozen production input.

Official converter documentation:
<https://wim.vree.org/svgParse/abc2xml.html>

## Inventory and split a multi-tune file

```bash
python3.12 scripts/inventory_abc.py \
  --input /path/to/OpenHymnal2014.06.abc \
  --split-dir build/abc \
  --report build/inventory.json
```

For the official collection, use its source lock:

```bash
python3.12 scripts/inventory_abc.py \
  --input /path/to/OpenHymnal2014.06.abc \
  --source-lock source.lock.json \
  --split-dir build/abc \
  --report build/inventory.json
```

The official raw file is Windows-1252/Latin-1 rather than UTF-8. The lock pins
its 1,932,541 raw bytes and SHA-256
`f75551ce21cfe9439545f3c0d97b4e737a4689ca4c4594a5a51f76fb164daa46`.
After decoding and encoding as UTF-8, it is 1,932,713 bytes with SHA-256
`9837dd05429a2f442982fc7dc01c94664e214318d1ca04859d8c797b9bf30517`.
Inventory reports preserve both identities and record the declared encoding.

For an unpinned source, pass `--source-encoding windows-1252` explicitly.

The splitter:

- treats each line beginning with `X:` as a tune boundary;
- copies the global preamble before the first `X:` into every split file;
- parses header fields through the first `K:` line;
- generates stable ordinal/reference/title filenames;
- reports duplicate references, missing titles/keys, and `%%abc-include`
  directives that may require additional source files.

The source line range in the report refers to the original multi-tune file,
excluding the copied global preamble.

## Convert and validate every tune

```bash
python3.12 scripts/convert_abc.py \
  --inventory build/inventory.json \
  --converter .tools/abc2xml-268/abc2xml.py \
  --converter-version 268 \
  --output-dir build/musicxml \
  --report build/conversion.json \
  --fail-on-error
```

`abc2xml.py` writes MusicXML to standard output when no `-o` option is passed.
The conversion runner invokes it once per already-split tune, captures stderr,
and continues after individual failures. The report distinguishes:

- `succeeded`: exit code zero and structurally valid MusicXML;
- `invalid`: exit code zero but invalid or empty MusicXML;
- `failed`: converter error, timeout, or launch failure.

Converter stderr is classified line by line. Decode/timing messages and skipped
layout directives remain recorded as `info`, but do not make a tune unclean.
Unhandled note decorations, dropped mappings, empty voices, validator warnings,
and unclassified warnings set `cleanup_required` and make the tune non-clean.
The report aggregates diagnostic occurrence counts, affected-tune counts, and
unhandled decoration names.

Validation checks the MusicXML root, part list, parts, measures, notes, note
payloads, and required durations. It also reports semantic counts for parts,
staves, voices, measures, notes, rests, lyrics/verse identifiers, key
signatures, and time signatures. These checks identify likely cleanup work;
they do not prove musical or engraving fidelity.

## Observed full-collection result

The pinned collection contains 293 tunes. With pinned converter 268:

- 293/293 converted to structurally valid MusicXML.
- 293/293 emitted stderr, mostly routine decode and skipped layout information.
- 291 `sintro` and 291 `eintro` unhandled-decoration occurrences affected
  290 tunes each.
- 143 `invertedfermata` occurrences affected 48 tunes.
- Three unhandled `()` markers affected two tunes.
- Four dropped multi-staff mappings affected two tunes, three empty-voice
  warnings affected three tunes, and one tune reported a lyric-extend error.
- Under the severity-aware definition, 2 tunes are clean and 291 require
  cleanup or review despite all 293 being structurally valid.

The decoration diagnostics are fidelity-impacting cleanup flags even though the
MusicXML is structurally valid. They must be visually assessed or translated
before those tunes are considered production-clean.

## Run tests

```bash
python3.12 -m unittest discover -s tests -v
```

The tests use a small, self-contained multi-tune ABC fixture and a fake
converter. The real converter and network access are not required.
