import { generatedCatalogItems } from "@/lib/catalog.generated";

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
  { value: "a-flat-minor", label: "A♭ minor" },
  { value: "e-flat-minor", label: "E♭ minor" },
  { value: "b-flat-minor", label: "B♭ minor" },
  { value: "f-minor", label: "F minor" },
  { value: "c-minor", label: "C minor" },
  { value: "g-minor", label: "G minor" },
  { value: "d-minor", label: "D minor" },
  { value: "a-minor", label: "A minor" },
  { value: "e-minor", label: "E minor" },
  { value: "b-minor", label: "B minor" },
  { value: "f-sharp-minor", label: "F♯ minor" },
  { value: "c-sharp-minor", label: "C♯ minor" },
  { value: "g-sharp-minor", label: "G♯ minor" },
  { value: "d-sharp-minor", label: "D♯ minor" },
  { value: "a-sharp-minor", label: "A♯ minor" },
] as const;

export const outputOptions = [
  { value: "score", label: "Full score", shortLabel: "Score" },
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
export type KeyMode = "major" | "minor";
export type OutputPart = (typeof outputOptions)[number]["value"];
export type Clef = (typeof clefOptions)[number]["value"];
export type OctavePlacement = (typeof octavePlacementOptions)[number]["value"];
export type PageSize = (typeof pageSizes)[number]["value"];
export type ContentType = "hymn" | "art_song";

export interface EditionConfig {
  targetKey: TargetKey;
  outputPart: OutputPart;
  clef: Clef;
  octavePlacement: OctavePlacement;
  pageSize: PageSize;
}

export interface CatalogItem {
  id: string;
  slug: string;
  contentType: ContentType;
  workId: string;
  arrangementId: string;
  arrangementLabel: string;
  title: string;
  textAuthor: string;
  tuneName: string;
  meter: string;
  composer: string;
  lyricist: string;
  collectionTitle: string;
  ensemble: string;
  searchTerms: readonly string[];
  originalKey: TargetKey;
  sourceLabel: string;
  availableLines: readonly OutputPart[];
  lyricsAvailableFor: readonly OutputPart[];
  catalogRevision: number;
  scoreSha256: string;
  rightsStatus: string;
  publicationStatus: string;
}

// Backward-compatible type name for hymn-specific landing-page modules.
export type Hymn = CatalogItem;

export const catalogItems: readonly CatalogItem[] = generatedCatalogItems
  .map((item) => ({
    ...item,
    contentType: item.contentType as ContentType,
    originalKey: item.originalKey as TargetKey,
    availableLines: item.availableLines as readonly OutputPart[],
    lyricsAvailableFor: item.lyricsAvailableFor as readonly OutputPart[],
  }))
  .sort(
    (left, right) =>
      left.title.localeCompare(right.title) ||
      left.composer.localeCompare(right.composer) ||
      left.id.localeCompare(right.id),
  );

export const hymns: readonly Hymn[] = catalogItems.filter(
  (item) => item.contentType === "hymn",
);

export const artSongs: readonly CatalogItem[] = catalogItems.filter(
  (item) => item.contentType === "art_song",
);

export function getHymnBySlug(slug: string): Hymn | undefined {
  return hymns.find((hymn) => hymn.slug === slug);
}

export function getDefaultOutput(item: CatalogItem): OutputPart {
  return item.availableLines.includes("score") ? "score" : "satb";
}

export function getContentTypeLabel(contentType: ContentType): string {
  return contentType === "art_song" ? "Art song" : "Hymn";
}

export function getKeyLabel(value: TargetKey): string {
  return keys.find((key) => key.value === value)?.label ?? value;
}

export function getKeyMode(value: TargetKey): KeyMode {
  return value.endsWith("-minor") ? "minor" : "major";
}

export function getKeysForMode(mode: KeyMode) {
  return keys.filter((key) => key.value.endsWith(`-${mode}`));
}

export function getOctavePlacementLabel(value: OctavePlacement): string {
  return (
    octavePlacementOptions.find((option) => option.value === value)?.label ?? value
  );
}
