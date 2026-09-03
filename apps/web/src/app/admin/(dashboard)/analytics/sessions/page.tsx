import type { Metadata } from "next";
import Link from "next/link";
import { AnalyticsNavigation } from "@/components/admin/analytics-navigation";
import { AnalyticsPagination } from "@/components/admin/analytics-pagination";
import { getFirstPartyAnalyticsSessions } from "@/lib/first-party-analytics.server";

export const metadata: Metadata = {
  title: "Analytics sessions",
};

type SessionsPageProps = {
  searchParams: Promise<{
    page?: string | string[];
    path?: string | string[];
  }>;
};

const numberFormatter = new Intl.NumberFormat("en-US");
const timestampFormatter = new Intl.DateTimeFormat("en-US", {
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
  month: "short",
  second: "2-digit",
  timeZone: "UTC",
  year: "numeric",
});

function firstValue(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

function requestedPage(value: string | string[] | undefined): number {
  const parsed = Number(firstValue(value));
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 1;
}

function requestedPath(value: string | string[] | undefined): string | undefined {
  const path = firstValue(value)?.trim();
  return path &&
    path.startsWith("/") &&
    !path.startsWith("//") &&
    !path.includes("?") &&
    !path.includes("#") &&
    path.length <= 2048
    ? path
    : undefined;
}

function formatTimestamp(value: string): string {
  const timestamp = new Date(value);
  return Number.isNaN(timestamp.valueOf())
    ? "Unknown"
    : timestampFormatter.format(timestamp);
}

function formatDuration(totalSeconds: number): string {
  if (totalSeconds < 60) return `${totalSeconds}s`;

  const minutes = Math.floor(totalSeconds / 60);
  if (minutes < 60) return `${minutes}m ${totalSeconds % 60}s`;

  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m`;
}

export default async function AnalyticsSessionsPage({
  searchParams,
}: SessionsPageProps) {
  const query = await searchParams;
  const page = requestedPage(query.page);
  const path = requestedPath(query.path);
  const data = await getFirstPartyAnalyticsSessions({ page, path });

  return (
    <main className="px-5 py-10 sm:px-8 sm:py-12 lg:px-10 lg:py-14">
      <div className="mx-auto w-full max-w-[1440px]">
        <div className="flex flex-col gap-7 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <Link
              href="/admin#first-party-analytics"
              className="font-mono text-[9px] uppercase tracking-[0.18em] text-coral transition hover:text-[#ffad9c] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral"
            >
              ← First-party analytics
            </Link>
            <h1 className="mt-4 text-5xl font-medium leading-[0.94] tracking-[-0.065em] sm:text-6xl">
              Sessions
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-6 text-white/45">
              Anonymous sessions active in the last 28 days, ordered by their
              first page view. Times are shown in UTC.
            </p>
          </div>
          <AnalyticsNavigation active="sessions" />
        </div>

        <div className="mt-9 flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="font-mono text-[9px] uppercase tracking-[0.14em] text-white/30">
              Matching sessions
            </p>
            <p className="mt-1 font-mono text-3xl tracking-[-0.05em] text-white/80 tabular-nums">
              {data.connected ? numberFormatter.format(data.totalSessions) : "—"}
            </p>
          </div>

          {path ? (
            <div className="flex items-center gap-2 rounded-full border border-blue-200/15 bg-blue-200/[0.06] py-1.5 pl-3.5 pr-2 text-xs text-blue-100/70">
              <span className="max-w-[60vw] truncate font-mono">{path}</span>
              <Link
                href="/admin/analytics/sessions"
                aria-label={`Clear ${path} filter`}
                className="grid size-6 place-items-center rounded-full text-blue-100/45 transition hover:bg-white/10 hover:text-blue-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-100/70"
              >
                ×
              </Link>
            </div>
          ) : null}
        </div>

        <section
          className="mt-5 overflow-hidden rounded-3xl border border-white/10 bg-white/[0.035]"
          aria-labelledby="sessions-table-heading"
        >
          <div className="flex items-center justify-between gap-4 border-b border-white/[0.07] px-5 py-4 sm:px-6">
            <h2
              id="sessions-table-heading"
              className="text-sm font-medium text-white/70"
            >
              Recent sessions
            </h2>
            <span className="font-mono text-[8px] uppercase tracking-[0.12em] text-white/25">
              50 per page
            </span>
          </div>

          {!data.connected ? (
            <p className="px-6 py-12 text-sm text-amber-100/70">
              Analytics data is unavailable. Check the database connection and
              migration status.
            </p>
          ) : data.sessions.length === 0 ? (
            <p className="px-6 py-12 text-sm text-white/40">
              No sessions match this view yet.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[1080px] border-collapse text-left text-xs">
                <thead>
                  <tr className="border-b border-white/[0.07] font-mono text-[8px] uppercase tracking-[0.13em] text-white/25">
                    <th className="px-6 py-3 font-medium">Started</th>
                    <th className="px-4 py-3 font-medium">Session</th>
                    <th className="px-4 py-3 font-medium">Landing page</th>
                    <th className="px-4 py-3 font-medium">Referrer</th>
                    <th className="px-4 py-3 text-right font-medium">Views</th>
                    <th className="px-4 py-3 text-right font-medium">Pages</th>
                    <th className="px-4 py-3 text-right font-medium">Duration</th>
                    <th className="px-6 py-3 text-right font-medium">
                      Last activity
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.06]">
                  {data.sessions.map((session) => (
                    <tr key={session.id} className="transition hover:bg-white/[0.025]">
                      <td className="whitespace-nowrap px-6 py-4 text-white/55">
                        {formatTimestamp(session.startedAt)}
                      </td>
                      <td className="px-4 py-4">
                        <code
                          title={session.id}
                          className="rounded-md bg-black/20 px-2 py-1 font-mono text-[10px] text-white/45"
                        >
                          {session.id.slice(0, 8)}
                        </code>
                      </td>
                      <td className="max-w-72 px-4 py-4">
                        <a
                          href={session.landingPath}
                          target="_blank"
                          rel="noreferrer"
                          className="block truncate font-mono text-blue-200/70 underline decoration-blue-200/20 underline-offset-4 transition hover:text-blue-100 hover:decoration-blue-100/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-100/70"
                        >
                          {session.landingPath}
                        </a>
                      </td>
                      <td className="max-w-52 px-4 py-4">
                        <span className="block truncate text-white/40">
                          {session.referrerHost ?? "Direct / unknown"}
                        </span>
                      </td>
                      <td className="px-4 py-4 text-right font-mono text-white/70 tabular-nums">
                        {numberFormatter.format(session.pageViews)}
                      </td>
                      <td className="px-4 py-4 text-right font-mono text-white/50 tabular-nums">
                        {numberFormatter.format(session.uniquePages)}
                      </td>
                      <td className="px-4 py-4 text-right font-mono text-white/50 tabular-nums">
                        {formatDuration(session.durationSeconds)}
                      </td>
                      <td className="whitespace-nowrap px-6 py-4 text-right text-white/40">
                        {formatTimestamp(session.lastSeenAt)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {data.connected ? (
            <AnalyticsPagination
              page={data.page}
              pathname="/admin/analytics/sessions"
              query={{ path }}
              totalPages={data.totalPages}
            />
          ) : null}
        </section>
      </div>
    </main>
  );
}
