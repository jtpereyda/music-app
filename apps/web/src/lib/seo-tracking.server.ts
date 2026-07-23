import "server-only";

import { neon } from "@neondatabase/serverless";
import type {
  KeywordProgress,
  KeywordProgressStage,
  KeywordTargetRow,
  TargetPageIndexing,
  TargetPageSeo,
} from "@/lib/keyword-targets";

type KeywordSnapshotRow = {
  snapshot_date: string | Date;
  keyword: string;
  target_path: string;
  source: "google_search_console" | "ahrefs" | "manual";
  ranking_url: string | null;
  rank: string | number | null;
  clicks: string | number | null;
  impressions: string | number | null;
  average_position: string | number | null;
  collected_at: string | Date;
};

type PageSnapshotRow = {
  snapshot_date: string | Date;
  target_path: string;
  source: string;
  is_live: boolean | null;
  index_verdict: string | null;
  robots_verdict: string | null;
  user_canonical: string | null;
  google_canonical: string | null;
  last_crawl_time: string | Date | null;
  organic_sessions: string | number | null;
  key_events: string | number | null;
  metadata: unknown;
  collected_at: string | Date;
};

type SyncRunRow = {
  source: string;
  status: "running" | "succeeded" | "partial" | "failed";
  records_written: number;
  message: string | null;
  started_at: string | Date;
  finished_at: string | Date | null;
};

type DownloadTrendRow = {
  event_date: string | Date;
  downloads: string | number;
};

export type SeoTrendPoint = {
  startDate: string;
  label: string;
  impressions: number;
  clicks: number;
  organicSessions: number;
  keyEvents: number;
  downloads: number;
};

export type SeoTrackingSummary = {
  connected: boolean;
  stageCounts: Record<KeywordProgressStage, number>;
  clicks28d: number;
  impressions28d: number;
  organicSessions28d: number;
  keyEvents28d: number;
  trackedKeywords: number;
  lastSyncedAt: string | null;
  lastSyncStatus: SyncRunRow["status"] | null;
  lastSyncMessage: string | null;
  downloads28d: number;
};

export type TrackedKeywordDashboard = {
  rows: KeywordTargetRow[];
  summary: SeoTrackingSummary;
  trend: SeoTrendPoint[];
};

const stages: KeywordProgressStage[] = [
  "planned",
  "live",
  "indexed",
  "visible",
  "top20",
  "page1",
  "top3",
];

function numeric(value: string | number | null): number | null {
  if (value === null) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function isoDate(value: string | Date): string {
  return new Date(value).toISOString().slice(0, 10);
}

function isoTimestamp(value: string | Date): string {
  return new Date(value).toISOString();
}

function metadataObject(value: unknown): Record<string, unknown> {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value) as unknown;
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        return parsed as Record<string, unknown>;
      }
    } catch {
      return {};
    }
  }
  return {};
}

function metadataText(
  metadata: Record<string, unknown>,
  key: string,
): string | null {
  const value = metadata[key];
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function startOfDayDaysAgo(days: number): Date {
  const date = new Date();
  date.setUTCHours(0, 0, 0, 0);
  date.setUTCDate(date.getUTCDate() - days);
  return date;
}

function mondayFor(value: string | Date): string {
  const date = new Date(value);
  date.setUTCHours(0, 0, 0, 0);
  const daysSinceMonday = (date.getUTCDay() + 6) % 7;
  date.setUTCDate(date.getUTCDate() - daysSinceMonday);
  return date.toISOString().slice(0, 10);
}

function buildTrend(
  keywordSnapshots: KeywordSnapshotRow[],
  pageSnapshots: PageSnapshotRow[],
  downloadRows: DownloadTrendRow[],
): SeoTrendPoint[] {
  const currentMonday = new Date(`${mondayFor(new Date())}T00:00:00Z`);
  const points = new Map<string, SeoTrendPoint>();
  for (let offset = 11; offset >= 0; offset -= 1) {
    const date = new Date(currentMonday);
    date.setUTCDate(date.getUTCDate() - offset * 7);
    const startDate = date.toISOString().slice(0, 10);
    points.set(startDate, {
      startDate,
      label: new Intl.DateTimeFormat("en-US", {
        month: "short",
        day: "numeric",
        timeZone: "UTC",
      }).format(date),
      impressions: 0,
      clicks: 0,
      organicSessions: 0,
      keyEvents: 0,
      downloads: 0,
    });
  }

  const keywordDays = new Map<
    string,
    { clicks: number; impressions: number }
  >();
  for (const snapshot of keywordSnapshots) {
    if (snapshot.source !== "google_search_console") continue;
    const key = `${isoDate(snapshot.snapshot_date)}\u0000${snapshot.keyword}`;
    const value = {
      clicks: numeric(snapshot.clicks) ?? 0,
      impressions: numeric(snapshot.impressions) ?? 0,
    };
    const existing = keywordDays.get(key);
    if (!existing) {
      keywordDays.set(key, value);
    } else {
      existing.clicks = Math.max(existing.clicks, value.clicks);
      existing.impressions = Math.max(existing.impressions, value.impressions);
    }
  }
  for (const [key, value] of keywordDays) {
    const week = points.get(mondayFor(key.split("\u0000")[0]));
    if (!week) continue;
    week.clicks += value.clicks;
    week.impressions += value.impressions;
  }
  for (const snapshot of pageSnapshots) {
    if (snapshot.source !== "google_analytics") continue;
    const week = points.get(mondayFor(snapshot.snapshot_date));
    if (!week) continue;
    week.organicSessions += numeric(snapshot.organic_sessions) ?? 0;
    week.keyEvents += numeric(snapshot.key_events) ?? 0;
  }
  for (const row of downloadRows) {
    const week = points.get(mondayFor(row.event_date));
    if (week) week.downloads += numeric(row.downloads) ?? 0;
  }
  return [...points.values()];
}

function targetMatchesRankingUrl(
  rankingUrl: string | null,
  targetPath: string,
): boolean | null {
  if (!rankingUrl) return null;
  try {
    const rankingPath = new URL(rankingUrl).pathname.replace(/\/$/, "") || "/";
    const normalizedTarget = targetPath.replace(/\/$/, "") || "/";
    return rankingPath === normalizedTarget;
  } catch {
    return null;
  }
}

function stageFor({
  indexed,
  live,
  position,
  visible,
}: {
  indexed: boolean | null;
  live: boolean | null;
  position: number | null;
  visible: boolean;
}): KeywordProgressStage {
  if (position !== null && position <= 3) return "top3";
  if (position !== null && position <= 10) return "page1";
  if (position !== null && position <= 20) return "top20";
  if (visible || position !== null) return "visible";
  if (indexed) return "indexed";
  if (live) return "live";
  return "planned";
}

function latestPosition(
  snapshots: KeywordSnapshotRow[],
): { position: number | null; rankingUrl: string | null; date: Date | null } {
  const positioned = snapshots
    .map((snapshot) => ({
      date: new Date(snapshot.snapshot_date),
      position: numeric(snapshot.rank) ?? numeric(snapshot.average_position),
      rankingUrl: snapshot.ranking_url,
      source: snapshot.source,
    }))
    .filter((snapshot) => snapshot.position !== null)
    .sort((left, right) => {
      const dateDifference = right.date.getTime() - left.date.getTime();
      if (dateDifference !== 0) return dateDifference;
      return Number(right.source === "ahrefs") - Number(left.source === "ahrefs");
    });
  return positioned[0] ?? { position: null, rankingUrl: null, date: null };
}

function positionAtOrBefore(
  snapshots: KeywordSnapshotRow[],
  date: Date,
): number | null {
  const candidates = snapshots
    .map((snapshot) => ({
      date: new Date(snapshot.snapshot_date),
      position: numeric(snapshot.rank) ?? numeric(snapshot.average_position),
    }))
    .filter(
      (snapshot) =>
        snapshot.position !== null && snapshot.date.getTime() <= date.getTime(),
    )
    .sort((left, right) => right.date.getTime() - left.date.getTime());
  return candidates[0]?.position ?? null;
}

function emptyProgress(): KeywordProgress {
  return {
    stage: "planned",
    currentPosition: null,
    positionChange7d: null,
    positionChange28d: null,
    bestPosition: null,
    impressions28d: 0,
    clicks28d: 0,
    ctr28d: null,
    organicSessions28d: 0,
    keyEvents28d: 0,
    rankingUrl: null,
    rankingUrlMatchesTarget: null,
    indexed: null,
    live: null,
    lastUpdated: null,
  };
}

function progressForRow(
  row: KeywordTargetRow,
  keywordSnapshots: KeywordSnapshotRow[],
  pageSnapshots: PageSnapshotRow[],
): KeywordProgress {
  if (keywordSnapshots.length === 0 && pageSnapshots.length === 0) {
    return emptyProgress();
  }

  const latest = latestPosition(keywordSnapshots);
  const latestDate = latest.date ?? new Date();
  const date7d = new Date(latestDate);
  date7d.setUTCDate(date7d.getUTCDate() - 7);
  const date28d = new Date(latestDate);
  date28d.setUTCDate(date28d.getUTCDate() - 28);
  const prior7d = positionAtOrBefore(keywordSnapshots, date7d);
  const prior28d = positionAtOrBefore(keywordSnapshots, date28d);
  const windowStart = startOfDayDaysAgo(27);
  const gsc28d = keywordSnapshots.filter(
    (snapshot) =>
      snapshot.source === "google_search_console" &&
      new Date(snapshot.snapshot_date).getTime() >= windowStart.getTime(),
  );
  const impressions28d = gsc28d.reduce(
    (total, snapshot) => total + (numeric(snapshot.impressions) ?? 0),
    0,
  );
  const clicks28d = gsc28d.reduce(
    (total, snapshot) => total + (numeric(snapshot.clicks) ?? 0),
    0,
  );
  const bestPosition = keywordSnapshots.reduce<number | null>(
    (best, snapshot) => {
      const position = numeric(snapshot.rank) ?? numeric(snapshot.average_position);
      if (position === null) return best;
      return best === null ? position : Math.min(best, position);
    },
    null,
  );
  const latestSite = pageSnapshots
    .filter((snapshot) => snapshot.source === "site_check")
    .toSorted(
      (left, right) =>
        new Date(right.snapshot_date).getTime() -
        new Date(left.snapshot_date).getTime(),
    )[0];
  const latestIndex = pageSnapshots
    .filter((snapshot) => snapshot.source === "google_search_console")
    .toSorted(
      (left, right) =>
        new Date(right.snapshot_date).getTime() -
        new Date(left.snapshot_date).getTime(),
    )[0];
  const indexed = latestIndex?.index_verdict
    ? latestIndex.index_verdict.toUpperCase() === "PASS"
    : null;
  const live = latestSite?.is_live ?? null;
  const analytics28d = pageSnapshots.filter(
    (snapshot) =>
      snapshot.source === "google_analytics" &&
      new Date(snapshot.snapshot_date).getTime() >= windowStart.getTime(),
  );
  const organicSessions28d = analytics28d.reduce(
    (total, snapshot) => total + (numeric(snapshot.organic_sessions) ?? 0),
    0,
  );
  const keyEvents28d = analytics28d.reduce(
    (total, snapshot) => total + (numeric(snapshot.key_events) ?? 0),
    0,
  );
  const latestCollectedAt = [...keywordSnapshots, ...pageSnapshots]
    .map((snapshot) => isoTimestamp(snapshot.collected_at))
    .toSorted()
    .at(-1) ?? null;

  return {
    stage: stageFor({
      indexed,
      live,
      position: latest.position,
      visible: impressions28d > 0,
    }),
    currentPosition: latest.position,
    positionChange7d:
      latest.position !== null && prior7d !== null
        ? prior7d - latest.position
        : null,
    positionChange28d:
      latest.position !== null && prior28d !== null
        ? prior28d - latest.position
        : null,
    bestPosition,
    impressions28d,
    clicks28d,
    ctr28d: impressions28d > 0 ? clicks28d / impressions28d : null,
    organicSessions28d,
    keyEvents28d,
    rankingUrl: latest.rankingUrl,
    rankingUrlMatchesTarget: targetMatchesRankingUrl(
      latest.rankingUrl,
      row.targetPath,
    ),
    indexed,
    live,
    lastUpdated: latestCollectedAt,
  };
}

function seoForRow(
  row: KeywordTargetRow,
  pageSnapshots: PageSnapshotRow[],
): TargetPageSeo {
  const latestSite = pageSnapshots
    .filter((snapshot) => snapshot.source === "site_check")
    .toSorted(
      (left, right) =>
        new Date(right.collected_at).getTime() -
        new Date(left.collected_at).getTime(),
    )[0];
  if (!latestSite) return row.seo;

  const metadata = metadataObject(latestSite.metadata);
  return {
    title: metadataText(metadata, "title") ?? row.seo.title,
    metaDescription:
      metadataText(metadata, "metaDescription") ?? row.seo.metaDescription,
    h1: metadataText(metadata, "h1") ?? row.seo.h1,
    firstParagraph:
      metadataText(metadata, "firstParagraph") ?? row.seo.firstParagraph,
    checkedAt: isoTimestamp(latestSite.collected_at),
  };
}

function indexingForRow(
  row: KeywordTargetRow,
  pageSnapshots: PageSnapshotRow[],
): TargetPageIndexing {
  const latestInspection = pageSnapshots
    .filter((snapshot) => snapshot.source === "google_search_console")
    .toSorted(
      (left, right) =>
        new Date(right.collected_at).getTime() -
        new Date(left.collected_at).getTime(),
    )[0];
  if (!latestInspection) return row.indexing;

  const metadata = metadataObject(latestInspection.metadata);
  return {
    verdict: latestInspection.index_verdict,
    coverageState: metadataText(metadata, "coverageState"),
    indexingState: metadataText(metadata, "indexingState"),
    pageFetchState: metadataText(metadata, "pageFetchState"),
    robotsTxtState: latestInspection.robots_verdict,
    userCanonical: latestInspection.user_canonical,
    googleCanonical: latestInspection.google_canonical,
    lastCrawlTime: latestInspection.last_crawl_time
      ? isoTimestamp(latestInspection.last_crawl_time)
      : null,
    checkedAt: isoTimestamp(latestInspection.collected_at),
    inspectionResultLink: metadataText(metadata, "inspectionResultLink"),
  };
}

export async function getTrackedKeywordDashboard(
  rows: KeywordTargetRow[],
): Promise<TrackedKeywordDashboard> {
  const stageCounts = Object.fromEntries(
    stages.map((stage) => [stage, 0]),
  ) as Record<KeywordProgressStage, number>;
  const emptySummary: SeoTrackingSummary = {
    connected: false,
    stageCounts,
    clicks28d: 0,
    impressions28d: 0,
    organicSessions28d: 0,
    keyEvents28d: 0,
    trackedKeywords: 0,
    lastSyncedAt: null,
    lastSyncStatus: null,
    lastSyncMessage: null,
    downloads28d: 0,
  };
  const databaseUrl = process.env.DATABASE_URL;
  if (!databaseUrl) {
    return {
      rows: rows.map((row) => ({ ...row, progress: emptyProgress() })),
      summary: emptySummary,
      trend: buildTrend([], [], []),
    };
  }

  try {
    const sql = neon(databaseUrl);
    const [keywordResult, pageResult, syncResult, downloadResult] =
      await Promise.all([
        sql`
          SELECT
            snapshot_date,
            keyword,
            target_path,
            source,
            ranking_url,
            rank,
            clicks,
            impressions,
            average_position,
            collected_at
          FROM app.seo_keyword_snapshots
          WHERE snapshot_date >= current_date - 120
        `,
        sql`
          SELECT
            snapshot_date,
            target_path,
            source,
            is_live,
            index_verdict,
            robots_verdict,
            user_canonical,
            google_canonical,
            last_crawl_time,
            organic_sessions,
            key_events,
            metadata,
            collected_at
          FROM app.seo_page_snapshots
          WHERE snapshot_date >= current_date - 120
        `,
        sql`
          SELECT
            source,
            status,
            records_written,
            message,
            started_at,
            finished_at
          FROM app.seo_sync_runs
          ORDER BY started_at DESC
          LIMIT 1
        `,
        sql`
          SELECT
            created_at::date AS event_date,
            count(*)::integer AS downloads
          FROM app.download_events
          WHERE outcome = 'succeeded'
            AND created_at >= now() - interval '120 days'
          GROUP BY created_at::date
          ORDER BY event_date
        `,
      ]);
    const keywordSnapshots = keywordResult as unknown as KeywordSnapshotRow[];
    const pageSnapshots = pageResult as unknown as PageSnapshotRow[];
    const lastSync = (syncResult as unknown as SyncRunRow[])[0];
    const downloadRows = downloadResult as unknown as DownloadTrendRow[];
    const downloadWindowStart = startOfDayDaysAgo(27).getTime();
    const downloads28d = downloadRows.reduce(
      (total, row) =>
        new Date(row.event_date).getTime() >= downloadWindowStart
          ? total + (numeric(row.downloads) ?? 0)
          : total,
      0,
    );
    const snapshotsByTarget = new Map<string, KeywordSnapshotRow[]>();
    const pagesByTarget = new Map<string, PageSnapshotRow[]>();

    for (const snapshot of keywordSnapshots) {
      const key = `${snapshot.keyword}\u0000${snapshot.target_path}`;
      const current = snapshotsByTarget.get(key) ?? [];
      current.push(snapshot);
      snapshotsByTarget.set(key, current);
    }
    for (const snapshot of pageSnapshots) {
      const current = pagesByTarget.get(snapshot.target_path) ?? [];
      current.push(snapshot);
      pagesByTarget.set(snapshot.target_path, current);
    }

    const enrichedRows = rows.map((row) => {
      const pageSnapshotsForTarget = pagesByTarget.get(row.targetPath) ?? [];
      return {
        ...row,
        progress: progressForRow(
          row,
          snapshotsByTarget.get(`${row.keyword}\u0000${row.targetPath}`) ?? [],
          pageSnapshotsForTarget,
        ),
        seo: seoForRow(row, pageSnapshotsForTarget),
        indexing: indexingForRow(row, pageSnapshotsForTarget),
      };
    });
    for (const row of enrichedRows) {
      stageCounts[row.progress.stage] += 1;
    }

    const keywordTotals = new Map<
      string,
      { clicks: number; impressions: number }
    >();
    for (const row of enrichedRows) {
      const existing = keywordTotals.get(row.keyword);
      if (!existing) {
        keywordTotals.set(row.keyword, {
          clicks: row.progress.clicks28d,
          impressions: row.progress.impressions28d,
        });
      } else {
        existing.clicks = Math.max(existing.clicks, row.progress.clicks28d);
        existing.impressions = Math.max(
          existing.impressions,
          row.progress.impressions28d,
        );
      }
    }
    const analyticsTotals = new Map<
      string,
      { keyEvents: number; sessions: number }
    >();
    for (const row of enrichedRows) {
      if (!analyticsTotals.has(row.targetPath)) {
        analyticsTotals.set(row.targetPath, {
          keyEvents: row.progress.keyEvents28d,
          sessions: row.progress.organicSessions28d,
        });
      }
    }

    return {
      rows: enrichedRows,
      summary: {
        connected: true,
        stageCounts,
        clicks28d: [...keywordTotals.values()].reduce(
          (total, value) => total + value.clicks,
          0,
        ),
        impressions28d: [...keywordTotals.values()].reduce(
          (total, value) => total + value.impressions,
          0,
        ),
        organicSessions28d: [...analyticsTotals.values()].reduce(
          (total, value) => total + value.sessions,
          0,
        ),
        keyEvents28d: [...analyticsTotals.values()].reduce(
          (total, value) => total + value.keyEvents,
          0,
        ),
        trackedKeywords: enrichedRows.filter(
          (row) => row.progress.lastUpdated !== null,
        ).length,
        lastSyncedAt: lastSync
          ? isoTimestamp(lastSync.finished_at ?? lastSync.started_at)
          : null,
        lastSyncStatus: lastSync?.status ?? null,
        lastSyncMessage: lastSync?.message ?? null,
        downloads28d,
      },
      trend: buildTrend(keywordSnapshots, pageSnapshots, downloadRows),
    };
  } catch (error) {
    const kind = error instanceof Error ? error.name : "UnknownError";
    console.warn(`[seo] Tracking read failed (${kind}); using empty progress.`);
    return {
      rows: rows.map((row) => ({ ...row, progress: emptyProgress() })),
      summary: emptySummary,
      trend: buildTrend([], [], []),
    };
  }
}

export function snapshotDate(value: string | Date): string {
  return isoDate(value);
}
