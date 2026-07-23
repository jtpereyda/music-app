import "server-only";

import {
  neon,
  type NeonQueryFunction,
} from "@neondatabase/serverless";
import { getGoogleSeoAccessToken } from "@/lib/google-seo.server";
import type { KeywordTargetRow } from "@/lib/keyword-targets";

type GscRow = {
  keys?: string[];
  clicks?: number;
  impressions?: number;
  ctr?: number;
  position?: number;
};

type UrlInspection = {
  inspectionResult?: {
    inspectionResultLink?: string;
    indexStatusResult?: {
      verdict?: string;
      robotsTxtState?: string;
      userCanonical?: string;
      googleCanonical?: string;
      lastCrawlTime?: string;
      coverageState?: string;
      indexingState?: string;
      pageFetchState?: string;
    };
  };
};

type Ga4Report = {
  rows?: Array<{
    dimensionValues?: Array<{ value?: string }>;
    metricValues?: Array<{ value?: string }>;
  }>;
};

type SnapshotResult = {
  ok: boolean;
  status: "succeeded" | "partial" | "failed";
  recordsWritten: number;
  message: string;
};

const externalRequestTimeoutMs = 15_000;

function dateDaysAgo(days: number): string {
  const date = new Date();
  date.setUTCHours(0, 0, 0, 0);
  date.setUTCDate(date.getUTCDate() - days);
  return date.toISOString().slice(0, 10);
}

function targetOrigin(): string {
  const configured = process.env.SITE_URL ?? "https://transposify.com";
  const withProtocol = configured.startsWith("http")
    ? configured
    : `https://${configured}`;
  return new URL(withProtocol).origin;
}

function uniqueTargets(rows: KeywordTargetRow[]) {
  const keywordMappings = new Map<string, { keyword: string; targetPath: string }>();
  const targetPaths = new Set<string>();
  for (const row of rows) {
    const key = `${row.keyword}\u0000${row.targetPath}`;
    keywordMappings.set(key, { keyword: row.keyword, targetPath: row.targetPath });
    targetPaths.add(row.targetPath);
  }
  return {
    keywordMappings: [...keywordMappings.values()],
    targetPaths: [...targetPaths],
  };
}

function decodeHtmlEntities(value: string): string {
  const namedEntities: Record<string, string> = {
    amp: "&",
    apos: "'",
    gt: ">",
    lt: "<",
    nbsp: " ",
    quot: '"',
  };
  return value.replace(
    /&(#x[\da-f]+|#\d+|[a-z]+);/gi,
    (entity, code: string) => {
      if (code.startsWith("#x")) {
        return String.fromCodePoint(Number.parseInt(code.slice(2), 16));
      }
      if (code.startsWith("#")) {
        return String.fromCodePoint(Number.parseInt(code.slice(1), 10));
      }
      return namedEntities[code.toLowerCase()] ?? entity;
    },
  );
}

function cleanHtmlText(value: string | undefined): string | null {
  if (!value) return null;
  const text = decodeHtmlEntities(
    value
      .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, " ")
      .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, " ")
      .replace(/<!--[\s\S]*?-->/g, " ")
      .replace(/<[^>]+>/g, " "),
  )
    .replace(/\s+/g, " ")
    .trim();
  return text || null;
}

function extractAttribute(tag: string, name: string): string | null {
  const match = tag.match(
    new RegExp(`\\b${name}\\s*=\\s*(?:\"([^\"]*)\"|'([^']*)')`, "i"),
  );
  return cleanHtmlText(match?.[1] ?? match?.[2]);
}

function extractSeoCopy(html: string) {
  const title = cleanHtmlText(
    html.match(/<title\b[^>]*>([\s\S]*?)<\/title>/i)?.[1],
  );
  const metaDescriptionTag = html
    .match(/<meta\b[^>]*>/gi)
    ?.find(
      (tag) => extractAttribute(tag, "name")?.toLowerCase() === "description",
    );
  const h1Match = html.match(/<h1\b[^>]*>([\s\S]*?)<\/h1>/i);
  const h1 = cleanHtmlText(h1Match?.[1]);
  const afterH1 = h1Match?.index === undefined
    ? html
    : html.slice(h1Match.index + h1Match[0].length);
  const firstParagraph = cleanHtmlText(
    afterH1.match(/<p\b[^>]*>([\s\S]*?)<\/p>/i)?.[1],
  );

  return {
    title,
    metaDescription: metaDescriptionTag
      ? extractAttribute(metaDescriptionTag, "content")
      : null,
    h1,
    firstParagraph,
  };
}

async function fetchJson<T>(
  url: string,
  accessToken: string,
  body: Record<string, unknown>,
): Promise<T> {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      authorization: `Bearer ${accessToken}`,
      "content-type": "application/json",
    },
    body: JSON.stringify(body),
    cache: "no-store",
    signal: AbortSignal.timeout(externalRequestTimeoutMs),
  });
  const payload = (await response.json()) as T & {
    error?: { message?: string };
  };
  if (!response.ok) {
    throw new Error(payload.error?.message ?? `Google API returned ${response.status}.`);
  }
  return payload;
}

async function runSiteChecks(
  sql: NeonQueryFunction<false, false>,
  paths: string[],
): Promise<number> {
  const origin = targetOrigin();
  const today = dateDaysAgo(0);
  const results = await Promise.all(
    paths.map(async (targetPath) => {
      let status: number | null = null;
      let isLive = false;
      let finalUrl: string | null = null;
      let seoCopy = {
        title: null as string | null,
        metaDescription: null as string | null,
        h1: null as string | null,
        firstParagraph: null as string | null,
      };
      try {
        const response = await fetch(new URL(targetPath, origin), {
          method: "GET",
          redirect: "follow",
          cache: "no-store",
          headers: { "user-agent": "Transposify SEO monitor/1.0" },
          signal: AbortSignal.timeout(externalRequestTimeoutMs),
        });
        status = response.status;
        finalUrl = response.url;
        isLive = response.status >= 200 && response.status < 400;
        seoCopy = extractSeoCopy(await response.text());
      } catch {
        // The failed check is still recorded so it remains visible in history.
      }
      return { finalUrl, isLive, seoCopy, status, targetPath };
    }),
  );
  const queries = results.map(
    ({ finalUrl, isLive, seoCopy, status, targetPath }) => sql`
        INSERT INTO app.seo_page_snapshots (
          snapshot_date,
          target_path,
          source,
          http_status,
          is_live,
          metadata,
          collected_at
        )
        VALUES (
          ${today},
          ${targetPath},
          'site_check',
          ${status},
          ${isLive},
          ${JSON.stringify({ finalUrl, ...seoCopy })}::jsonb,
          now()
        )
        ON CONFLICT (snapshot_date, target_path, source) DO UPDATE SET
          http_status = excluded.http_status,
          is_live = excluded.is_live,
          metadata = excluded.metadata,
          collected_at = now()
      `,
  );
  await sql.transaction(queries);
  return queries.length;
}

function gscDates(): string[] {
  return [dateDaysAgo(4), dateDaysAgo(3), dateDaysAgo(2)];
}

async function runSearchConsoleKeywords(
  sql: NeonQueryFunction<false, false>,
  accessToken: string,
  mappings: { keyword: string; targetPath: string }[],
): Promise<number> {
  const siteUrl = process.env.GOOGLE_SEARCH_CONSOLE_SITE_URL;
  if (!siteUrl) return 0;
  const dates = gscDates();
  const endpoint = `https://www.googleapis.com/webmasters/v3/sites/${encodeURIComponent(siteUrl)}/searchAnalytics/query`;
  const queryCache = new Map<string, Promise<GscRow[]>>();

  for (const { keyword } of mappings) {
    if (queryCache.has(keyword)) continue;
    queryCache.set(
      keyword,
      fetchJson<{ rows?: GscRow[] }>(endpoint, accessToken, {
        startDate: dates[0],
        endDate: dates.at(-1),
        dimensions: ["date", "page"],
        dimensionFilterGroups: [
          {
            filters: [
              { dimension: "query", expression: keyword, operator: "equals" },
              { dimension: "country", expression: "usa", operator: "equals" },
            ],
          },
        ],
        dataState: "final",
        rowLimit: 250,
      }).then((response) => response.rows ?? []),
    );
  }

  const rowsByKeyword = new Map<string, GscRow[]>();
  for (const [keyword, promise] of queryCache) {
    rowsByKeyword.set(keyword, await promise);
  }

  const writes = [];
  for (const { keyword, targetPath } of mappings) {
    const rows = rowsByKeyword.get(keyword) ?? [];
    for (const date of dates) {
      const dailyRows = rows.filter((row) => row.keys?.[0] === date);
      const clicks = dailyRows.reduce((total, row) => total + (row.clicks ?? 0), 0);
      const impressions = dailyRows.reduce(
        (total, row) => total + (row.impressions ?? 0),
        0,
      );
      const weightedPosition = dailyRows.reduce(
        (total, row) => total + (row.position ?? 0) * (row.impressions ?? 0),
        0,
      );
      const rankingRow = dailyRows.toSorted(
        (left, right) =>
          (right.impressions ?? 0) - (left.impressions ?? 0) ||
          (left.position ?? Number.POSITIVE_INFINITY) -
            (right.position ?? Number.POSITIVE_INFINITY),
      )[0];
      const position =
        impressions > 0
          ? weightedPosition / impressions
          : rankingRow?.position ?? null;
      const rankingUrl = rankingRow?.keys?.[1] ?? null;
      writes.push(sql`
        INSERT INTO app.seo_keyword_snapshots (
          snapshot_date,
          keyword,
          target_path,
          source,
          country,
          device,
          ranking_url,
          clicks,
          impressions,
          ctr,
          average_position,
          metadata,
          collected_at
        )
        VALUES (
          ${date},
          ${keyword},
          ${targetPath},
          'google_search_console',
          'US',
          'all',
          ${rankingUrl},
          ${clicks},
          ${impressions},
          ${impressions > 0 ? clicks / impressions : null},
          ${position},
          ${JSON.stringify({ siteUrl })}::jsonb,
          now()
        )
        ON CONFLICT (
          snapshot_date,
          keyword,
          target_path,
          source,
          country,
          device
        ) DO UPDATE SET
          ranking_url = excluded.ranking_url,
          clicks = excluded.clicks,
          impressions = excluded.impressions,
          ctr = excluded.ctr,
          average_position = excluded.average_position,
          metadata = excluded.metadata,
          collected_at = now()
      `);
    }
  }
  if (writes.length > 0) await sql.transaction(writes);
  return writes.length;
}

async function runUrlInspection(
  sql: NeonQueryFunction<false, false>,
  accessToken: string,
  paths: string[],
): Promise<number> {
  const siteUrl = process.env.GOOGLE_SEARCH_CONSOLE_SITE_URL;
  if (!siteUrl) return 0;
  const origin = targetOrigin();
  const today = dateDaysAgo(0);
  const inspections = await Promise.all(
    paths.map(async (targetPath) => {
      const response = await fetchJson<UrlInspection>(
        "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect",
        accessToken,
        { inspectionUrl: new URL(targetPath, origin).toString(), siteUrl },
      );
      return {
        inspectionResultLink:
          response.inspectionResult?.inspectionResultLink ?? null,
        status: response.inspectionResult?.indexStatusResult,
        targetPath,
      };
    }),
  );
  const writes = inspections.map(
    ({ inspectionResultLink, status, targetPath }) => sql`
      INSERT INTO app.seo_page_snapshots (
        snapshot_date,
        target_path,
        source,
        index_verdict,
        robots_verdict,
        user_canonical,
        google_canonical,
        last_crawl_time,
        metadata,
        collected_at
      )
      VALUES (
        ${today},
        ${targetPath},
        'google_search_console',
        ${status?.verdict ?? null},
        ${status?.robotsTxtState ?? null},
        ${status?.userCanonical ?? null},
        ${status?.googleCanonical ?? null},
        ${status?.lastCrawlTime ?? null},
        ${JSON.stringify({
          coverageState: status?.coverageState,
          indexingState: status?.indexingState,
          pageFetchState: status?.pageFetchState,
          inspectionResultLink,
        })}::jsonb,
        now()
      )
      ON CONFLICT (snapshot_date, target_path, source) DO UPDATE SET
        index_verdict = excluded.index_verdict,
        robots_verdict = excluded.robots_verdict,
        user_canonical = excluded.user_canonical,
        google_canonical = excluded.google_canonical,
        last_crawl_time = excluded.last_crawl_time,
        metadata = excluded.metadata,
        collected_at = now()
    `,
  );
  if (writes.length > 0) await sql.transaction(writes);
  return writes.length;
}

export async function runIndexingInspection(
  rows: KeywordTargetRow[],
): Promise<SnapshotResult> {
  const databaseUrl = process.env.DATABASE_URL;
  if (!databaseUrl) {
    return {
      ok: false,
      status: "failed",
      recordsWritten: 0,
      message: "DATABASE_URL is not configured.",
    };
  }
  if (!process.env.GOOGLE_SEARCH_CONSOLE_SITE_URL) {
    return {
      ok: false,
      status: "failed",
      recordsWritten: 0,
      message: "Search Console property is not configured.",
    };
  }

  const sql = neon(databaseUrl);
  const today = dateDaysAgo(0);
  const runRows = await sql`
    INSERT INTO app.seo_sync_runs (
      source,
      status,
      range_start,
      range_end
    )
    VALUES ('google_search_console', 'running', ${today}, ${today})
    RETURNING id
  `;
  const runId = String((runRows as unknown as { id: string }[])[0].id);
  const { targetPaths } = uniqueTargets(rows);

  try {
    const accessToken = await getGoogleSeoAccessToken();
    if (!accessToken) {
      throw new Error("Google credentials are not configured.");
    }
    const recordsWritten = await runUrlInspection(sql, accessToken, targetPaths);
    const message = `Checked Google indexing status for ${recordsWritten} target pages.`;
    await sql`
      UPDATE app.seo_sync_runs
      SET
        status = 'succeeded',
        records_written = ${recordsWritten},
        message = ${message},
        finished_at = now()
      WHERE id = ${runId}
    `;
    return {
      ok: true,
      status: "succeeded",
      recordsWritten,
      message,
    };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Unknown URL Inspection error.";
    await sql`
      UPDATE app.seo_sync_runs
      SET
        status = 'failed',
        message = ${message},
        finished_at = now()
      WHERE id = ${runId}
    `;
    return {
      ok: false,
      status: "failed",
      recordsWritten: 0,
      message,
    };
  }
}

async function runGoogleAnalytics(
  sql: NeonQueryFunction<false, false>,
  accessToken: string,
  paths: string[],
): Promise<number> {
  const propertyId = process.env.GOOGLE_ANALYTICS_PROPERTY_ID;
  if (!propertyId) return 0;
  const dates = gscDates();
  const report = await fetchJson<Ga4Report>(
    `https://analyticsdata.googleapis.com/v1beta/properties/${encodeURIComponent(propertyId)}:runReport`,
    accessToken,
    {
      dateRanges: [{ startDate: dates[0], endDate: dates.at(-1) }],
      dimensions: [{ name: "date" }, { name: "landingPage" }],
      metrics: [
        { name: "sessions" },
        { name: "activeUsers" },
        { name: "keyEvents" },
      ],
      dimensionFilter: {
        andGroup: {
          expressions: [
            {
              filter: {
                fieldName: "sessionDefaultChannelGroup",
                stringFilter: { matchType: "EXACT", value: "Organic Search" },
              },
            },
            {
              filter: {
                fieldName: "country",
                stringFilter: { matchType: "EXACT", value: "United States" },
              },
            },
          ],
        },
      },
      limit: "10000",
    },
  );
  const metrics = new Map<
    string,
    { sessions: number; users: number; keyEvents: number }
  >();
  for (const row of report.rows ?? []) {
    const rawDate = row.dimensionValues?.[0]?.value;
    const landingPage = row.dimensionValues?.[1]?.value;
    if (!rawDate || !landingPage || rawDate.length !== 8) continue;
    const date = `${rawDate.slice(0, 4)}-${rawDate.slice(4, 6)}-${rawDate.slice(6)}`;
    let pathname: string;
    try {
      pathname = new URL(landingPage, targetOrigin()).pathname;
    } catch {
      continue;
    }
    metrics.set(`${date}\u0000${pathname}`, {
      sessions: Number(row.metricValues?.[0]?.value ?? 0),
      users: Number(row.metricValues?.[1]?.value ?? 0),
      keyEvents: Number(row.metricValues?.[2]?.value ?? 0),
    });
  }

  const writes = [];
  for (const date of dates) {
    for (const targetPath of paths) {
      const value = metrics.get(`${date}\u0000${targetPath}`) ?? {
        sessions: 0,
        users: 0,
        keyEvents: 0,
      };
      writes.push(sql`
        INSERT INTO app.seo_page_snapshots (
          snapshot_date,
          target_path,
          source,
          organic_sessions,
          organic_users,
          key_events,
          metadata,
          collected_at
        )
        VALUES (
          ${date},
          ${targetPath},
          'google_analytics',
          ${value.sessions},
          ${value.users},
          ${value.keyEvents},
          ${JSON.stringify({ propertyId })}::jsonb,
          now()
        )
        ON CONFLICT (snapshot_date, target_path, source) DO UPDATE SET
          organic_sessions = excluded.organic_sessions,
          organic_users = excluded.organic_users,
          key_events = excluded.key_events,
          metadata = excluded.metadata,
          collected_at = now()
      `);
    }
  }
  if (writes.length > 0) await sql.transaction(writes);
  return writes.length;
}

export async function runSeoSnapshot(
  rows: KeywordTargetRow[],
): Promise<SnapshotResult> {
  const databaseUrl = process.env.DATABASE_URL;
  if (!databaseUrl) {
    return {
      ok: false,
      status: "failed",
      recordsWritten: 0,
      message: "DATABASE_URL is not configured.",
    };
  }
  const sql = neon(databaseUrl);
  const rangeStart = dateDaysAgo(4);
  const rangeEnd = dateDaysAgo(0);
  const runRows = await sql`
    INSERT INTO app.seo_sync_runs (
      source,
      status,
      range_start,
      range_end
    )
    VALUES ('daily', 'running', ${rangeStart}, ${rangeEnd})
    RETURNING id
  `;
  const runId = String((runRows as unknown as { id: string }[])[0].id);
  const { keywordMappings, targetPaths } = uniqueTargets(rows);
  let recordsWritten = 0;
  const completed: string[] = [];
  const failures: string[] = [];

  try {
    recordsWritten += await runSiteChecks(sql, targetPaths);
    completed.push("site checks");
    console.info(`[seo] Completed ${targetPaths.length} live-page checks.`);
  } catch (error) {
    failures.push(
      `site checks: ${error instanceof Error ? error.message : "unknown error"}`,
    );
  }

  let accessToken: string | null = null;
  try {
    accessToken = await getGoogleSeoAccessToken();
  } catch (error) {
    failures.push(
      `Google authentication: ${error instanceof Error ? error.message : "unknown error"}`,
    );
  }

  if (accessToken && process.env.GOOGLE_SEARCH_CONSOLE_SITE_URL) {
    try {
      recordsWritten += await runSearchConsoleKeywords(
        sql,
        accessToken,
        keywordMappings,
      );
      recordsWritten += await runUrlInspection(sql, accessToken, targetPaths);
      completed.push("Search Console");
      console.info(
        `[seo] Completed Search Console collection for ${keywordMappings.length} keyword mappings.`,
      );
    } catch (error) {
      failures.push(
        `Search Console: ${error instanceof Error ? error.message : "unknown error"}`,
      );
    }
  } else if (!process.env.GOOGLE_SEARCH_CONSOLE_SITE_URL) {
    failures.push("Search Console: property is not configured");
  } else if (!accessToken && failures.length === 0) {
    failures.push("Google credentials are not configured");
  }

  if (accessToken && process.env.GOOGLE_ANALYTICS_PROPERTY_ID) {
    try {
        recordsWritten += await runGoogleAnalytics(
          sql,
          accessToken,
          targetPaths,
        );
        completed.push("Google Analytics");
    } catch (error) {
      failures.push(
        `Google Analytics: ${error instanceof Error ? error.message : "unknown error"}`,
      );
    }
  }

  const status =
    failures.length === 0
      ? "succeeded"
      : completed.length > 0
        ? "partial"
        : "failed";
  const message = [
    completed.length > 0 ? `Completed ${completed.join(" and ")}.` : null,
    failures.length > 0 ? failures.join("; ") : null,
  ]
    .filter(Boolean)
    .join(" ");

  await sql`
    UPDATE app.seo_sync_runs
    SET
      status = ${status},
      records_written = ${recordsWritten},
      message = ${message},
      finished_at = now()
    WHERE id = ${runId}
  `;
  return {
    ok: status !== "failed",
    status,
    recordsWritten,
    message,
  };
}
