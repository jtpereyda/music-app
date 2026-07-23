# Catalog expansion

## Catalog revision 5

The implemented catalog contains 290 score records:

- 269 compatible records from the pinned combined ABC source; and
- eight compatible, non-duplicate records from the pinned split ZIP; and
- 13 records from the first HymnsToGod public-domain tranche.

The Open Hymnal portion recovers seven of the former structural holds with an audited,
versioned SATB normalizer. It splits combined dyad notation into two aligned
voice timelines for six records, removes one empty converter-created part, and
repairs one skipped lower-staff measure number by aligning the existing measure
sequence.
The six remaining holds are genuinely non-SATB arrangements with 3, 5, 6, or 7
voices. Supporting those would require generalized part selection rather than
guessing which musical lines to discard. Two remaining split-ZIP additions
also need generalized part handling.

## HymnsToGod source policy

For this project, an item in the HymnsToGod public-domain collection whose
individual page says `Public Domain - USA` is eligible for catalog ingestion.
CC0 is not required. The importer must still preserve the evidence behind that
decision:

- the individual hymn page and source-file URLs;
- the displayed public-domain declaration;
- retrieval time and raw source hash;
- credited lyricist, composer, arranger, and tune name; and
- every transformation hash through canonical MusicXML.

Creative Commons and conditional-copyright sections remain separate inputs and
must not enter through the public-domain path.

The source list is:
<https://hymnstogod.org/Hymns-PD/ZZ-CompletePDHymnList.html>

## First HymnsToGod tranche result

The first audit covered 17 high-recognition titles from the source's
public-domain index.

Thirteen passed both the rights and SATB structure gates:

1. Are You Washed in the Blood?
2. At Calvary
3. Count Your Blessings
4. Great Is Thy Faithfulness
5. Have Thine Own Way, Lord
6. Higher Ground
7. More About Jesus
8. Near the Cross
9. Praise Him! Praise Him!
10. Rejoice, the Lord Is King
11. 'Tis So Sweet to Trust in Jesus
12. When We All Get to Heaven
13. Wonderful Words of Life

`I Surrender All` is a rights hold: it appears in the complete public-domain
index, but its individual page says `Copyright: Unknown - USA`. `Softly and
Tenderly`, `Stand Up, Stand Up for Jesus!`, and `There Is Power in the Blood`
are structure holds because their arrangements contain more than four
principal musical lines.

The importer uses the editable Mup source. Official Mup 7.2 expands macros, and
the versioned parser reads notation directly from the expanded statements.
MIDI was used as an independent pitch-sequence check, not as an interchange
format, because ordinary Mup spaces are collapsed in MIDI. Every imported
source-track pitch sequence matched the Mup-generated MIDI. All 13 imported
scores also rendered successfully as SATB PDFs.

## Ingest acceptance checks

Each candidate passes:

1. source-page classification as `Public Domain - USA`;
2. deterministic MUP download and raw hash capture;
3. conversion to parseable, untransposed MusicXML;
4. explicit part, staff, voice, key, and lyric inventory;
5. render checks for the full score and every advertised extracted line; and
6. a rendered-page visual check.

## Mode-preserving transposition

The transposition pipeline now supports major and minor source scores using the
same operation. Tonic-only destinations inherit the source mode. The API and
web app expose 15 conventional destinations for each mode, filter the selector
to the score's mode, and reject explicit major-to-minor or minor-to-major
requests. No mode-conversion feature is implied.

## Non-hymn sequence

After generalized score metadata and arbitrary output parts are available:

1. pilot 20–30 CC0 OpenScore Orchestra melody scores as `Classical Themes`;
2. pilot voice-and-piano transposition with OpenScore Lieder; and
3. curate corrected Bach chorales rather than bulk-importing the known
   accidental-conversion errors.
