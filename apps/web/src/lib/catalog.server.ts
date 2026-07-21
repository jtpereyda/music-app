import "server-only";

import { neon } from "@neondatabase/serverless";
import { cache } from "react";
import {
  hymns as staticHymns,
  keys,
  type Hymn,
  type OutputPart,
  type TargetKey,
} from "@/lib/catalog";

interface CatalogRow {
  id: string;
  catalog_revision: number;
  score_sha256: string;
  original_key_name: string;
  available_lines: string[];
  lyrics_scope: string;
  source_rights_status: string;
  publication_status: string;
}

export interface CatalogSnapshot {
  hymns: readonly Hymn[];
  source: "neon" | "static";
}

const lineMap: Readonly<Record<string, OutputPart>> = {
  SATB: "satb",
  S: "soprano",
  A: "alto",
  T: "tenor",
  B: "bass",
};
const supportedKeys = new Set<string>(keys.map((key) => key.value));

function keySlug(name: string): TargetKey {
  const slug = name.toLocaleLowerCase().replaceAll(" ", "-");
  if (!supportedKeys.has(slug)) {
    throw new Error("Catalog returned an unsupported original key.");
  }
  return slug as TargetKey;
}

function lines(values: string[]): readonly OutputPart[] {
  const mapped = values.map((value) => lineMap[value]);
  if (mapped.some((value) => value === undefined) || mapped.length === 0) {
    throw new Error("Catalog returned unsupported music lines.");
  }
  return mapped;
}

export function mergeCatalogRows(rows: CatalogRow[]): readonly Hymn[] {
  if (rows.length !== staticHymns.length) {
    throw new Error("Database catalog is incomplete.");
  }
  const rowById = new Map(rows.map((row) => [row.id, row]));
  if (rowById.size !== rows.length) {
    throw new Error("Database catalog contains duplicate hymn ids.");
  }

  return staticHymns.map((hymn) => {
    const row = rowById.get(hymn.id);
    if (!row || row.score_sha256 !== hymn.scoreSha256) {
      throw new Error("Database catalog does not match canonical score hashes.");
    }
    if (row.catalog_revision < hymn.catalogRevision) {
      throw new Error("Database catalog revision is older than the application.");
    }

    const availableLines = lines(row.available_lines);
    const lyricsAvailableFor: readonly OutputPart[] =
      row.lyrics_scope === "soprano_only"
        ? ["satb", "soprano"]
        : row.lyrics_scope === "all_lines"
          ? availableLines
          : [];

    return {
      ...hymn,
      originalKey: keySlug(row.original_key_name),
      availableLines,
      lyricsAvailableFor,
      catalogRevision: row.catalog_revision,
      rightsStatus: row.source_rights_status,
      publicationStatus: row.publication_status,
    };
  });
}

export const getCatalogSnapshot = cache(async (): Promise<CatalogSnapshot> => {
  if (process.env.CATALOG_SOURCE !== "neon") {
    return { hymns: staticHymns, source: "static" };
  }

  const databaseUrl = process.env.DATABASE_URL;
  if (!databaseUrl) {
    console.warn("[catalog] DATABASE_URL is unavailable; using static catalog.");
    return { hymns: staticHymns, source: "static" };
  }

  try {
    const sql = neon(databaseUrl);
    const result = await sql`
      SELECT
        id,
        catalog_revision,
        score_sha256,
        original_key_name,
        available_lines,
        lyrics_scope,
        source_rights_status,
        publication_status
      FROM app.catalog_hymns
      ORDER BY id
    `;
    return {
      hymns: mergeCatalogRows(result as unknown as CatalogRow[]),
      source: "neon",
    };
  } catch (error) {
    const kind = error instanceof Error ? error.name : "UnknownError";
    console.warn(`[catalog] Neon read failed (${kind}); using static catalog.`);
    return { hymns: staticHymns, source: "static" };
  }
});

export function renderApiConfigured(): boolean {
  return Boolean(
    process.env.RENDER_API_URL ?? process.env.NEXT_PUBLIC_RENDER_API_URL,
  );
}
