# Open Hymnal source audit

Audit date: 2026-07-20 UTC

## Outcome

The Open Hymnal source is usable for a technical ingest/render spike after a
strict rights filter, but it is not yet approved as production catalog
provenance.

The project currently publishes two official resources labeled `2014.06`:

- a combined ABC file with **293 score records**
- a split-file ZIP with **306 ABC files/records**

Those numbers count score/arrangement records, not unique hymns or tunes. The
combined file has 281 unique primary `T:` values and 371 total `T:` fields,
because alternate titles and multiple settings are present.

The two official payloads are mutable and disagree. Both were last modified by
the server in March 2017. The combined file contains a score marked “2017
Revision”; the split ZIP contains five “2015 Revision” files and one “2017
Revision” file. Therefore, `2014.06` is a product label, not a trustworthy
immutable release identifier.

## Canonical source and accessibility

The canonical project homepage, not a search result or derivative:

- <http://openhymnal.org/>
- <http://openhymnal.org/copying.html>

The homepage itself links these official source payloads:

- <http://openhymnal.org/OpenHymnal2014.06.abc>
- <http://openhymnal.org/OpenHymnal2014.06-abc.zip>

Observed on 2026-07-20 UTC:

| Resource | Result | Relevant response metadata |
| --- | --- | --- |
| Project homepage | HTTP 200 | Last-Modified 2026-07-11 |
| Copying page | HTTP 200 | Last-Modified 2026-07-11 |
| Combined ABC | HTTP 200 | `text/plain`, 1,932,541 bytes, Last-Modified 2017-03-18 |
| Split ABC ZIP | HTTP 200 | `application/zip`, 991,298 bytes, Last-Modified 2017-03-18 |
| Official PDF | HTTP 200 | `application/pdf`, 7,902,986 bytes, Last-Modified 2017-03-18 |
| HTTPS on `openhymnal.org` and `www.openhymnal.org` | Failed verification | certificate subject does not match either hostname |
| HTTP on `www.openhymnal.org` | HTTP 404 | the working host is the no-`www` HTTP origin |

The canonical source can therefore be fetched, but only over unauthenticated
HTTP. The checked-in files are quarantined, hash-pinned snapshots: they must
never be silently refreshed or treated as authenticated release artifacts.

No complete HTTPS ABC mirror with independently verifiable provenance was
located. A PDF mirror at
<https://openscriptures.net/wp-content/uploads/2021/04/OpenHymnal2014.06.pdf>
is byte-identical to the current official PDF:

```text
SHA-256 9fa0f21f2845e1ba50c1986402fe82526247524000b3a6a3979d6ca6e625f0a5
size    7,902,986 bytes
```

That corroborates the printable companion, not the ABC source bytes.
ABCNotation/John Chambers hosts some individual Open Hymnal transcriptions, and
Michael Eskin publishes a derivative subset, but neither is a complete,
authenticated mirror of this source archive.

## Stored raw artifacts

| Artifact | SHA-256 | Size |
| --- | --- | --- |
| `data/open-hymnal/raw/OpenHymnal2014.06.abc` | `f75551ce21cfe9439545f3c0d97b4e737a4689ca4c4594a5a51f76fb164daa46` | 1,932,541 bytes |
| `data/open-hymnal/raw/OpenHymnal2014.06-abc.zip` | `407ec5ab7ec6b27f698245c3b4b2c7bea1488fabbb56f7ff190849e11fe472cd` | 991,298 bytes |

The ZIP passed `unzip -t`. The combined file is ISO-8859 text rather than UTF-8,
so ingestion must decode it explicitly and preserve the original bytes.

## Inventory and rights counts

| Metric | Combined ABC | Split ZIP |
| --- | ---: | ---: |
| ABC records/files | 293 | 306 |
| Total `T:` fields | 371 | 388 |
| Exact `C: copyright: public domain.` candidates | 275 | 285 |
| Clearly restricted/non-PD | 17 | 20 |
| Ambiguous/manual review | 1 | 1 |

The combined file contains only 288 unique `X:` values: `X: 1` is reused six
times. `X:` is not a stable identifier. Use the pinned artifact hash plus entry
filename (ZIP) or record ordinal (combined file), then assign an internal ID.

The machine-readable restricted and ambiguous lists are in
`data/open-hymnal/manifest.json`.

## Rights filtering rule

The canonical copying page states that:

1. the project evaluates U.S. copyright only;
2. melody, setting/harmony, original words, and translation have separate
   copyright status;
3. most, but not all, hymns are public domain in all components;
4. each score and ABC file carries its own terms; and
5. the database comes with no guarantee.

This means the collection-level wording “freely distributable” is not a
collection-wide commercial adaptation license.

Use this high-precision ingest gate:

1. Split the source into record-local ABC units and retain every `C:`, `S:`,
   `%OHCOMPOSER`, `%OHARRANGER`, `%OHAUTHOR`, and `%OHTRANSLATOR` field.
2. A record may enter the **technical PD candidate** set only when its local
   declaration begins exactly with `C: copyright: public domain.` and no other
   local line asserts a copyright, permission-only use, worship-only use,
   no-alteration condition, required notice, “all rights reserved,” or an
   unresolved third-party license.
3. Hold every non-exact declaration for manual review. Do not attempt to strip
   lyrics or harmony automatically: the product must know exactly which
   component remains and whether the resulting use is authorized.
4. Hold `Twas In The Moon of Wintertime` even though its music and lyrics are
   labeled PD. Its setting is described only as “CPDL” with an obsolete link;
   the ABC does not state a license, version, or grant.
5. Exclude the other held records from the commercial/transposition path. Their
   notices typically permit Christian-worship reproduction only if unaltered,
   with the notice retained, and reserve all other rights. Transposition and
   rearrangement are alterations.
6. Treat the 275/285 exact declarations only as candidates. Before production,
   independently substantiate the first-publication country/date and status of
   text, translation, melody, and setting. Store the evidence and reviewer
   decision per component.

The public-domain data-file statement on the copying page does not override the
record-local rights of the hymn components or third-party material.

## Execution recommendation

For Spike B, use the split ZIP because it gives one file per score, but pin the
exact SHA-256 above and initially process only the 285 exact-declaration
candidates. Report conversion metrics against that pinned candidate set, not
“all Open Hymnal hymns.”

For a production catalog, the current blockers are:

- no authenticated HTTPS transport, upstream checksum, signed release, or
  immutable versioned archive;
- disagreement between the two official `2014.06` source payloads; and
- missing independent per-component publication evidence.

The first two do not block an offline technical conversion spike. All three
block treating the upstream label as sufficient production provenance.

## Verification commands

Run from the repository root:

```sh
shasum -a 256 \
  data/open-hymnal/raw/OpenHymnal2014.06.abc \
  data/open-hymnal/raw/OpenHymnal2014.06-abc.zip

wc -c -l data/open-hymnal/raw/OpenHymnal2014.06.abc
unzip -t data/open-hymnal/raw/OpenHymnal2014.06-abc.zip
unzip -Z1 data/open-hymnal/raw/OpenHymnal2014.06-abc.zip \
  | LC_ALL=C rg -c '\.abc$'

LC_ALL=C rg -c '^X:' data/open-hymnal/raw/OpenHymnal2014.06.abc
LC_ALL=C rg -c '^T:' data/open-hymnal/raw/OpenHymnal2014.06.abc
LC_ALL=C rg -c '^C: copyright: public domain\.' \
  data/open-hymnal/raw/OpenHymnal2014.06.abc

unzip -p data/open-hymnal/raw/OpenHymnal2014.06-abc.zip '*.abc' \
  | LC_ALL=C rg -c '^X:'
unzip -p data/open-hymnal/raw/OpenHymnal2014.06-abc.zip '*.abc' \
  | LC_ALL=C rg -c '^C: copyright: public domain\.'
unzip -p data/open-hymnal/raw/OpenHymnal2014.06-abc.zip '*.abc' \
  | LC_ALL=C rg -c '2015 Revision|2017 Revision'

jq empty data/open-hymnal/manifest.json
```
