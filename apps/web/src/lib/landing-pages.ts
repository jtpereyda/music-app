import {
  clefOptions,
  keys,
  octavePlacementOptions,
  outputOptions,
  pageSizes,
  type Clef,
  type EditionConfig,
  type Hymn,
  type OctavePlacement,
  type OutputPart,
  type PageSize,
  type TargetKey,
} from "@/lib/catalog";

export const priorityHymnSlugs = [
  "it-is-well-with-my-soul",
  "come-thou-fount-of-every-blessing",
  "blessed-assurance",
  "amazing-grace",
  "o-for-a-thousand-tongues",
  "beneath-the-cross-of-jesus",
] as const;

const landingTuneNames: Readonly<Record<string, string>> = {
  "amazing-grace": "NEW BRITAIN",
  "beneath-the-cross-of-jesus": "ST. CHRISTOPHER",
  "blessed-assurance": "ASSURANCE",
  "come-thou-fount-of-every-blessing": "NETTLETON",
  "it-is-well-with-my-soul": "VILLE DU HAVRE",
  "o-for-a-thousand-tongues": "AZMON",
};

export interface CuratedPreset {
  hymnSlug: string;
  slug: string;
  kind: "key" | "instrument";
  shortLabel: string;
  title: string;
  heading: string;
  eyebrow: string;
  intro: string;
  edition: EditionConfig;
}

export const curatedPresets: readonly CuratedPreset[] = [
  {
    hymnSlug: "it-is-well-with-my-soul",
    slug: "key-of-c",
    kind: "key",
    shortLabel: "Key of C",
    title: "It Is Well with My Soul Sheet Music in C — SATB & Any Clef",
    heading: "It Is Well with My Soul sheet music in C major",
    eyebrow: "VILLE DU HAVRE · key of C",
    intro:
      "Open a printable SATB edition of the traditional VILLE DU HAVRE tune in C major, then isolate any hymn voice or choose the clef that fits your musician.",
    edition: {
      targetKey: "c-major",
      outputPart: "satb",
      clef: "original",
      octavePlacement: "original",
      pageSize: "letter",
    },
  },
  {
    hymnSlug: "it-is-well-with-my-soul",
    slug: "key-of-g",
    kind: "key",
    shortLabel: "Key of G",
    title: "It Is Well with My Soul Sheet Music in G — SATB & Any Clef",
    heading: "It Is Well with My Soul sheet music in G major",
    eyebrow: "VILLE DU HAVRE · key of G",
    intro:
      "Open a printable SATB edition of the traditional VILLE DU HAVRE tune in G major, with selectable soprano, alto, tenor, and bass lines below.",
    edition: {
      targetKey: "g-major",
      outputPart: "satb",
      clef: "original",
      octavePlacement: "original",
      pageSize: "letter",
    },
  },
  {
    hymnSlug: "it-is-well-with-my-soul",
    slug: "key-of-d",
    kind: "key",
    shortLabel: "Key of D",
    title: "It Is Well with My Soul Sheet Music in D — SATB & Any Clef",
    heading: "It Is Well with My Soul sheet music in D major",
    eyebrow: "VILLE DU HAVRE · key of D",
    intro:
      "Open a printable SATB edition of the traditional VILLE DU HAVRE tune in D major, then tailor the voice, clef, register, and page size.",
    edition: {
      targetKey: "d-major",
      outputPart: "satb",
      clef: "original",
      octavePlacement: "original",
      pageSize: "letter",
    },
  },
  {
    hymnSlug: "amazing-grace",
    slug: "key-of-c",
    kind: "key",
    shortLabel: "Key of C",
    title: "Amazing Grace Sheet Music in C — SATB & Any Clef",
    heading: "Amazing Grace sheet music in C major",
    eyebrow: "NEW BRITAIN · key of C",
    intro:
      "Open a printable SATB edition of Amazing Grace to the traditional NEW BRITAIN tune in C major, with every hymn voice and clef available below.",
    edition: {
      targetKey: "c-major",
      outputPart: "satb",
      clef: "original",
      octavePlacement: "original",
      pageSize: "letter",
    },
  },
  {
    hymnSlug: "blessed-assurance",
    slug: "key-of-c",
    kind: "key",
    shortLabel: "Key of C",
    title: "Blessed Assurance Sheet Music in C — SATB & Any Clef",
    heading: "Blessed Assurance sheet music in C major",
    eyebrow: "ASSURANCE · key of C",
    intro:
      "Open a printable SATB edition of Blessed Assurance in C major, then choose a single hymn voice, clef, or pitch register without leaving the page.",
    edition: {
      targetKey: "c-major",
      outputPart: "satb",
      clef: "original",
      octavePlacement: "original",
      pageSize: "letter",
    },
  },
  {
    hymnSlug: "come-thou-fount-of-every-blessing",
    slug: "key-of-c",
    kind: "key",
    shortLabel: "Key of C",
    title: "Come Thou Fount Sheet Music in C — SATB & Any Clef",
    heading: "Come Thou Fount sheet music in C major",
    eyebrow: "NETTLETON · key of C",
    intro:
      "Open a printable SATB edition of Come Thou Fount of Every Blessing to the NETTLETON tune in C major, with selectable parts and clefs.",
    edition: {
      targetKey: "c-major",
      outputPart: "satb",
      clef: "original",
      octavePlacement: "original",
      pageSize: "letter",
    },
  },
  {
    hymnSlug: "amazing-grace",
    slug: "cello",
    kind: "instrument",
    shortLabel: "Cello melody part",
    title: "Amazing Grace Cello Sheet Music — Free Melody Part",
    heading: "Amazing Grace sheet music for cello",
    eyebrow: "Cello melody part · bass clef · G major",
    intro:
      "Play the traditional NEW BRITAIN melody in G major from a clean bass-clef cello part. This is a configurable hymn melody part, not a cello-and-piano arrangement.",
    edition: {
      targetKey: "g-major",
      outputPart: "soprano",
      clef: "bass",
      octavePlacement: "auto",
      pageSize: "letter",
    },
  },
  {
    hymnSlug: "amazing-grace",
    slug: "trombone",
    kind: "instrument",
    shortLabel: "Trombone melody part",
    title: "Amazing Grace Trombone Sheet Music — Bass Clef Melody",
    heading: "Amazing Grace sheet music for trombone",
    eyebrow: "Trombone melody part · bass clef · concert B-flat",
    intro:
      "Play the traditional NEW BRITAIN melody in concert B-flat major from a clean bass-clef trombone part. Change the key or register instantly if another range fits better.",
    edition: {
      targetKey: "b-flat-major",
      outputPart: "soprano",
      clef: "bass",
      octavePlacement: "auto",
      pageSize: "letter",
    },
  },
];

export type EditionSearchParams = Readonly<
  Record<string, string | string[] | undefined>
>;

function singleValue(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export function defaultEdition(hymn: Hymn): EditionConfig {
  return {
    targetKey: hymn.originalKey,
    outputPart: "satb",
    clef: "original",
    octavePlacement: "original",
    pageSize: "letter",
  };
}

export function editionFromSearchParams(
  params: EditionSearchParams,
  fallback: EditionConfig,
): EditionConfig {
  const targetKey = singleValue(params.key);
  const outputPart = singleValue(params.line);
  const clef = singleValue(params.clef);
  const octavePlacement = singleValue(params.octave);
  const pageSize = singleValue(params.page_size);

  return {
    targetKey: keys.some((option) => option.value === targetKey)
      ? (targetKey as TargetKey)
      : fallback.targetKey,
    outputPart: outputOptions.some((option) => option.value === outputPart)
      ? (outputPart as OutputPart)
      : fallback.outputPart,
    clef: clefOptions.some((option) => option.value === clef)
      ? (clef as Clef)
      : fallback.clef,
    octavePlacement: octavePlacementOptions.some(
      (option) => option.value === octavePlacement,
    )
      ? (octavePlacement as OctavePlacement)
      : fallback.octavePlacement,
    pageSize: pageSizes.some((option) => option.value === pageSize)
      ? (pageSize as PageSize)
      : fallback.pageSize,
  };
}

export function getCuratedPreset(
  hymnSlug: string,
  presetSlug: string,
): CuratedPreset | undefined {
  return curatedPresets.find(
    (preset) =>
      preset.hymnSlug === hymnSlug && preset.slug === presetSlug,
  );
}

export function getPresetsForHymn(hymnSlug: string): readonly CuratedPreset[] {
  return curatedPresets.filter((preset) => preset.hymnSlug === hymnSlug);
}

export function getLandingTuneName(hymn: Hymn): string {
  return landingTuneNames[hymn.slug] ?? hymn.tuneName.toLocaleUpperCase();
}

export function isPriorityHymn(slug: string): boolean {
  return priorityHymnSlugs.some((candidate) => candidate === slug);
}
