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

export type FirstPartyAnalyticsSession = {
  durationSeconds: number;
  id: string;
  landingPath: string;
  lastSeenAt: string;
  pageViews: number;
  referrerHost: string | null;
  startedAt: string;
  uniquePages: number;
};

export type FirstPartyAnalyticsSessionList = {
  connected: boolean;
  page: number;
  pageSize: number;
  sessions: FirstPartyAnalyticsSession[];
  totalPages: number;
  totalSessions: number;
};

export type FirstPartyAnalyticsPage = {
  firstViewedAt: string;
  lastViewedAt: string;
  pageViews: number;
  path: string;
  sessions: number;
  viewsPerSession: number;
};

export type FirstPartyAnalyticsPageList = {
  connected: boolean;
  page: number;
  pageSize: number;
  pages: FirstPartyAnalyticsPage[];
  totalPages: number;
  totalPaths: number;
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

type CountRow = {
  total: string | number;
};

type SessionRow = {
  duration_seconds: string | number;
  id: string;
  landing_path: string;
  last_seen_at: string;
  page_views: string | number;
  referrer_host: string | null;
  started_at: string;
  unique_pages: string | number;
};

type PageRow = {
  first_viewed_at: string;
  last_viewed_at: string;
  page_views: string | number;
  path: string;
  sessions: string | number;
  views_per_session: string | number;
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

function pagination(page: number, pageSize: number) {
  const resolvedPage = Number.isFinite(page)
    ? Math.max(1, Math.floor(page))
    : 1;
  const resolvedPageSize = Number.isFinite(pageSize)
    ? Math.min(100, Math.max(10, Math.floor(pageSize)))
    : 50;

  return {
    offset: (resolvedPage - 1) * resolvedPageSize,
    page: resolvedPage,
    pageSize: resolvedPageSize,
  };
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

export async function getFirstPartyAnalyticsSessions({
  page = 1,
  pageSize = 50,
  path,
}: {
  page?: number;
  pageSize?: number;
  path?: string;
} = {}): Promise<FirstPartyAnalyticsSessionList> {
  const resolved = pagination(page, pageSize);
  const empty: FirstPartyAnalyticsSessionList = {
    connected: false,
    page: resolved.page,
    pageSize: resolved.pageSize,
    sessions: [],
    totalPages: 1,
    totalSessions: 0,
  };
  const databaseUrl = process.env.DATABASE_URL;
  if (!databaseUrl) return empty;

  const pathFilter = path?.trim() || null;

  try {
    const sql = neon(databaseUrl);
    const [countResult, sessionsResult] = await Promise.all([
      sql`
        SELECT count(*)::integer AS total
        FROM app.analytics_sessions AS sessions
        WHERE sessions.last_seen_at >= now() - interval '28 days'
          AND (
            ${pathFilter}::text IS NULL
            OR EXISTS (
              SELECT 1
              FROM app.analytics_page_views AS filtered_views
              WHERE filtered_views.session_id = sessions.id
                AND filtered_views.path = ${pathFilter}::text
            )
          )
      `,
      sql`
        SELECT
          sessions.id::text,
          sessions.landing_path,
          sessions.referrer_host,
          sessions.started_at::text,
          sessions.last_seen_at::text,
          count(page_views.id)::integer AS page_views,
          count(DISTINCT page_views.path)::integer AS unique_pages,
          greatest(
            0,
            extract(epoch FROM (
              sessions.last_seen_at - sessions.started_at
            ))
          )::integer AS duration_seconds
        FROM app.analytics_sessions AS sessions
        LEFT JOIN app.analytics_page_views AS page_views
          ON page_views.session_id = sessions.id
        WHERE sessions.last_seen_at >= now() - interval '28 days'
          AND (
            ${pathFilter}::text IS NULL
            OR EXISTS (
              SELECT 1
              FROM app.analytics_page_views AS filtered_views
              WHERE filtered_views.session_id = sessions.id
                AND filtered_views.path = ${pathFilter}::text
            )
          )
        GROUP BY sessions.id
        ORDER BY sessions.started_at DESC, sessions.id DESC
        LIMIT ${resolved.pageSize}
        OFFSET ${resolved.offset}
      `,
    ]);
    const count = (countResult as unknown as CountRow[])[0];
    const totalSessions = count ? numeric(count.total) : 0;

    return {
      connected: true,
      page: resolved.page,
      pageSize: resolved.pageSize,
      sessions: (sessionsResult as unknown as SessionRow[]).map((row) => ({
        durationSeconds: numeric(row.duration_seconds),
        id: row.id,
        landingPath: row.landing_path,
        lastSeenAt: row.last_seen_at,
        pageViews: numeric(row.page_views),
        referrerHost: row.referrer_host,
        startedAt: row.started_at,
        uniquePages: numeric(row.unique_pages),
      })),
      totalPages: Math.max(1, Math.ceil(totalSessions / resolved.pageSize)),
      totalSessions,
    };
  } catch (error) {
    const kind = error instanceof Error ? error.name : "UnknownError";
    console.warn(`[analytics] Session list read failed (${kind}).`);
    return empty;
  }
}

export async function getFirstPartyAnalyticsPages({
  page = 1,
  pageSize = 50,
  path,
  query,
}: {
  page?: number;
  pageSize?: number;
  path?: string;
  query?: string;
} = {}): Promise<FirstPartyAnalyticsPageList> {
  const resolved = pagination(page, pageSize);
  const empty: FirstPartyAnalyticsPageList = {
    connected: false,
    page: resolved.page,
    pageSize: resolved.pageSize,
    pages: [],
    totalPages: 1,
    totalPaths: 0,
  };
  const databaseUrl = process.env.DATABASE_URL;
  if (!databaseUrl) return empty;

  const pathFilter = path?.trim() || null;
  const queryFilter = pathFilter ? null : query?.trim() || null;

  try {
    const sql = neon(databaseUrl);
    const [countResult, pagesResult] = await Promise.all([
      sql`
        SELECT count(DISTINCT path)::integer AS total
        FROM app.analytics_page_views
        WHERE viewed_at >= now() - interval '28 days'
          AND (${pathFilter}::text IS NULL OR path = ${pathFilter}::text)
          AND (
            ${queryFilter}::text IS NULL
            OR path ILIKE '%' || ${queryFilter}::text || '%'
          )
      `,
      sql`
        SELECT
          path,
          count(*)::integer AS page_views,
          count(DISTINCT session_id)::integer AS sessions,
          round(
            count(*)::numeric / nullif(count(DISTINCT session_id), 0),
            2
          ) AS views_per_session,
          min(viewed_at)::text AS first_viewed_at,
          max(viewed_at)::text AS last_viewed_at
        FROM app.analytics_page_views
        WHERE viewed_at >= now() - interval '28 days'
          AND (${pathFilter}::text IS NULL OR path = ${pathFilter}::text)
          AND (
            ${queryFilter}::text IS NULL
            OR path ILIKE '%' || ${queryFilter}::text || '%'
          )
        GROUP BY path
        ORDER BY page_views DESC, path
        LIMIT ${resolved.pageSize}
        OFFSET ${resolved.offset}
      `,
    ]);
    const count = (countResult as unknown as CountRow[])[0];
    const totalPaths = count ? numeric(count.total) : 0;

    return {
      connected: true,
      page: resolved.page,
      pageSize: resolved.pageSize,
      pages: (pagesResult as unknown as PageRow[]).map((row) => ({
        firstViewedAt: row.first_viewed_at,
        lastViewedAt: row.last_viewed_at,
        pageViews: numeric(row.page_views),
        path: row.path,
        sessions: numeric(row.sessions),
        viewsPerSession: numeric(row.views_per_session),
      })),
      totalPages: Math.max(1, Math.ceil(totalPaths / resolved.pageSize)),
      totalPaths,
    };
  } catch (error) {
    const kind = error instanceof Error ? error.name : "UnknownError";
    console.warn(`[analytics] Page list read failed (${kind}).`);
    return empty;
  }
}
