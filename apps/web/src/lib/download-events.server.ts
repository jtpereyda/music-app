import "server-only";

import { neon } from "@neondatabase/serverless";
import {
  clefOptions,
  keys,
  outputOptions,
  pageSizes,
} from "@/lib/catalog";

const validKeys = new Set<string>(keys.map((item) => item.value));
const validLines = new Set<string>(outputOptions.map((item) => item.value));
const validClefs = new Set<string>(clefOptions.map((item) => item.value));
const validPageSizes = new Set<string>(pageSizes.map((item) => item.value));

export async function recordDownloadEvent({
  durationMs,
  hymnId,
  outputBytes,
  outcome,
  parameters,
  requestId,
}: {
  durationMs: number;
  hymnId: string;
  outputBytes: number | null;
  outcome: "succeeded" | "failed";
  parameters: URLSearchParams;
  requestId: string;
}): Promise<void> {
  const databaseUrl = process.env.DATABASE_URL;
  if (!databaseUrl) return;
  const targetKey = parameters.get("key");
  const line = parameters.get("line") ?? "satb";
  const clef = parameters.get("clef") ?? "original";
  const pageSize = parameters.get("page_size") ?? "letter";
  if (
    !targetKey ||
    !validKeys.has(targetKey) ||
    !validLines.has(line) ||
    !validClefs.has(clef) ||
    !validPageSizes.has(pageSize)
  ) {
    return;
  }

  try {
    const sql = neon(databaseUrl);
    await sql`
      INSERT INTO app.download_events (
        request_id,
        hymn_id,
        target_key,
        line,
        clef,
        page_size,
        outcome,
        output_bytes,
        render_duration_ms
      )
      VALUES (
        ${requestId},
        ${hymnId},
        ${targetKey},
        ${line},
        ${clef},
        ${pageSize},
        ${outcome},
        ${outputBytes},
        ${Math.max(0, Math.round(durationMs))}
      )
      ON CONFLICT (request_id) DO NOTHING
    `;
  } catch (error) {
    const kind = error instanceof Error ? error.name : "UnknownError";
    console.warn(`[downloads] Event write failed (${kind}).`);
  }
}
