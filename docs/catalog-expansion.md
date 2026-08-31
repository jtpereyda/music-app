# Catalog expansion

## Catalog revision 8

The implemented catalog contains 2,226 scores:

- 870 public-domain hymn arrangements from the pinned Open Hymnal,
  HymnsToGod, and Timeless Truths sources; and
- 1,356 CC0 classical art-song scores from the indexed OpenScore Lieder corpus.

All existing hymn IDs and hymn-specific landing pages remain stable. The
catalog, edition builder, search UI, render routes, and database constraints
now distinguish generic scores from hymns. Hymns retain SATB and individual
voice options. Art songs expose the complete encoded score so voice and piano
transpose together.

Revision 8 adds `Nothing Between` from Timeless Truths. The source page marks
the edition public domain and exposes MusicXML directly. A pinned, versioned
normalizer converts the Sibelius two-staff dyads into four semantic SATB voices,
maps the four positional lyric rows to stable verse IDs, and retains both the
American and British first-line spellings as search aliases.

## OpenScore Lieder result

The import pins repository commit
`6b2dc542ce2e8aa4b78c8ee62103b210efc07015` and verifies the downloaded archive
against SHA-256
`e925dd89f9dc2ac16f2aff49470d2c1f2dec9977bb4059172cbcbc7a4b98958c`.
The repository contains 1,462 MXL files, but the ingest boundary is the 1,356
rows in its score metadata table. All 1,356 indexed rows promote; the 106
unindexed files are reported and excluded.

The MXL artifacts are copied byte-for-byte. Each item records its MuseScore
score ID, actual path at the pinned commit, source URL, work and arrangement
identity, source hash, composer, lyricist, collection, ensemble, lyrics scope,
and original key. Stable filename IDs safely reconcile several upstream folder
renames without treating folder text as musical identity.

## Mode-preserving transposition

Major and minor scores use the same transposition operation. The UI offers only
destination keys with the source mode, and the shared renderer rejects explicit
major-to-minor or minor-to-major requests. OpenScore MusicXML does not always
declare whether a signature represents the relative major or minor. The import
therefore records explicit upstream modes when present and otherwise applies a
versioned pitch-profile inference. That catalog key is passed to the renderer
as the source-key authority.

## Arrangement identity

The schema retains separate `work_id` and `arrangement_id` fields. This already
supports multiple HymnsToGod settings of one hymn and allows later OpenScore
sources to add another edition without overwriting an existing catalog route.
The present Lieder snapshot has one promoted arrangement for each indexed
MuseScore score ID.

## Next expansion candidates

The next useful tranche is non-vocal classical material with similarly strong
machine-readable licensing and source identity. A focused pilot from CC0
OpenScore Orchestra would test orchestral or melody-only score shapes without
weakening the current fail-closed ingest boundary. Bach chorales remain a
curation project rather than a bulk import because known conversions require
musical correction.
