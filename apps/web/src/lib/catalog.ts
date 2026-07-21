import { generatedHymns } from "@/lib/catalog.generated";

export const keys = [
  { value: "c-flat-major", label: "C♭ major" },
  { value: "g-flat-major", label: "G♭ major" },
  { value: "d-flat-major", label: "D♭ major" },
  { value: "a-flat-major", label: "A♭ major" },
  { value: "e-flat-major", label: "E♭ major" },
  { value: "b-flat-major", label: "B♭ major" },
  { value: "f-major", label: "F major" },
  { value: "c-major", label: "C major" },
  { value: "g-major", label: "G major" },
  { value: "d-major", label: "D major" },
  { value: "a-major", label: "A major" },
  { value: "e-major", label: "E major" },
  { value: "b-major", label: "B major" },
  { value: "f-sharp-major", label: "F♯ major" },
  { value: "c-sharp-major", label: "C♯ major" },
] as const;

export const outputOptions = [
  { value: "satb", label: "Full SATB", shortLabel: "SATB" },
  { value: "soprano", label: "Soprano line", shortLabel: "S" },
  { value: "alto", label: "Alto line", shortLabel: "A" },
  { value: "tenor", label: "Tenor line", shortLabel: "T" },
  { value: "bass", label: "Bass line", shortLabel: "B" },
] as const;

export const clefOptions = [
  { value: "original", label: "Original" },
  { value: "treble", label: "Treble" },
  { value: "bass", label: "Bass" },
  { value: "alto", label: "Alto" },
  { value: "tenor", label: "Tenor" },
  { value: "treble-8vb", label: "Treble 8vb" },
] as const;

export const octavePlacementOptions = [
  { value: "auto", label: "Auto", detail: "Best staff fit" },
  { value: "original", label: "Original", detail: "Keep register" },
  { value: "up", label: "Up 1 octave", detail: "Sound +12" },
  { value: "down", label: "Down 1 octave", detail: "Sound −12" },
] as const;

export const pageSizes = [
  { value: "letter", label: "US Letter", dimensions: "8.5 × 11 in" },
  { value: "a4", label: "A4", dimensions: "210 × 297 mm" },
] as const;

export type TargetKey = (typeof keys)[number]["value"];
export type OutputPart = (typeof outputOptions)[number]["value"];
export type Clef = (typeof clefOptions)[number]["value"];
export type OctavePlacement = (typeof octavePlacementOptions)[number]["value"];
export type PageSize = (typeof pageSizes)[number]["value"];

export interface EditionConfig {
  targetKey: TargetKey;
  outputPart: OutputPart;
  clef: Clef;
  octavePlacement: OctavePlacement;
  pageSize: PageSize;
}

export interface Hymn {
  id: string;
  slug: string;
  title: string;
  textAuthor: string;
  tuneName: string;
  meter: string;
  originalKey: TargetKey;
  sourceLabel: string;
  availableLines: readonly OutputPart[];
  lyricsAvailableFor: readonly OutputPart[];
  catalogRevision: number;
  scoreSha256: string;
  rightsStatus: string;
  publicationStatus: string;
}

const satbLines: readonly OutputPart[] = [
  "satb",
  "soprano",
  "alto",
  "tenor",
  "bass",
];

const sopranoLyrics: readonly OutputPart[] = ["satb", "soprano"];

export const hymns: readonly Hymn[] = generatedHymns.map((hymn) => ({
  ...hymn,
  originalKey: hymn.originalKey as TargetKey,
  sourceLabel: "Open Hymnal",
  availableLines: satbLines,
  lyricsAvailableFor: sopranoLyrics,
  catalogRevision: 2,
  rightsStatus: "technical_candidate_not_production_approved",
  publicationStatus: "technical_preview",
}));

export function getHymnBySlug(slug: string): Hymn | undefined {
  return hymns.find((hymn) => hymn.slug === slug);
}

export function getKeyLabel(value: TargetKey): string {
  return keys.find((key) => key.value === value)?.label ?? value;
}

export function getOctavePlacementLabel(value: OctavePlacement): string {
  return (
    octavePlacementOptions.find((option) => option.value === value)?.label ?? value
  );
}
