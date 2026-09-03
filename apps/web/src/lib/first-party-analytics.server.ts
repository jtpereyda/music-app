import "server-only";

import { neon } from "@neondatabase/serverless";

export type FirstPartyAnalyticsSummary = {
  connected: boolean;
  pageViews28d: number;
  sessions28d: number;
  topPages28d: Array<{
    path: string;
    pageViews: number;
    sessions: number;
  }>;
  viewsPerSession28d: number | null;
};

type TotalsRow = {
  page_views: string | number;
  sessions: string | number;
};

type TopPageRow = {
  path: string;
  page_views: string | number;
  sessions: string | number;
};

const emptySummary: FirstPartyAnalyticsSummary = {
  connected: false,
  pageViews28d: 0,
  sessions28d: 0,
  topPages28d: [],
  viewsPerSession28d: null,
};

function numeric(value: string | number): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

export async function recordFirstPartyPageView({
  path,
  referrerHost,
  sessionId,
}: {
  path: string;
  referrerHost: string | null;
  sessionId: string;
}): Promise<void> {
  const databaseUrl = process.env.DATABASE_URL;
  if (!databaseUrl) return;

  try {
    const sql = neon(databaseUrl);
    await sql`
      WITH current_session AS (
        INSERT INTO app.analytics_sessions (
          id,
          landing_path,
          referrer_host
        )
        VALUES (
          ${sessionId},
          ${path},
          ${referrerHost}
        )
        ON CONFLICT (id) DO UPDATE
        SET last_seen_at = greatest(
          app.analytics_sessions.last_seen_at,
          now()
        )
        RETURNING id
      )
      INSERT INTO app.analytics_page_views (
        session_id,
        path
      )
      SELECT
        id,
        ${path}
      FROM current_session
    `;
  } catch (error) {
    const kind = error instanceof Error ? error.name : "UnknownError";
    console.warn(`[analytics] Page-view write failed (${kind}).`);
  }
}

export async function getFirstPartyAnalyticsSummary(): Promise<FirstPartyAnalyticsSummary> {
  const databaseUrl = process.env.DATABASE_URL;
  if (!databaseUrl) return emptySummary;

  try {
    const sql = neon(databaseUrl);
    const [totalsResult, topPagesResult] = await Promise.all([
      sql`
        SELECT
          count(*)::integer AS page_views,
          count(DISTINCT session_id)::integer AS sessions
        FROM app.analytics_page_views
        WHERE viewed_at >= now() - interval '28 days'
      `,
      sql`
        SELECT
          path,
          count(*)::integer AS page_views,
          count(DISTINCT session_id)::integer AS sessions
        FROM app.analytics_page_views
        WHERE viewed_at >= now() - interval '28 days'
        GROUP BY path
        ORDER BY page_views DESC, path
        LIMIT 8
      `,
    ]);
    const totals = (totalsResult as unknown as TotalsRow[])[0];
    const pageViews28d = totals ? numeric(totals.page_views) : 0;
    const sessions28d = totals ? numeric(totals.sessions) : 0;

    return {
      connected: true,
      pageViews28d,
      sessions28d,
      topPages28d: (topPagesResult as unknown as TopPageRow[]).map((row) => ({
        path: row.path,
        pageViews: numeric(row.page_views),
        sessions: numeric(row.sessions),
      })),
      viewsPerSession28d:
        sessions28d > 0 ? pageViews28d / sessions28d : null,
    };
  } catch (error) {
    const kind = error instanceof Error ? error.name : "UnknownError";
    console.warn(`[analytics] Summary read failed (${kind}).`);
    return emptySummary;
  }
}
