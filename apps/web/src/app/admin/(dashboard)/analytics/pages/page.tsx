import type { Metadata } from "next";
import Link from "next/link";
import { AnalyticsNavigation } from "@/components/admin/analytics-navigation";
import { AnalyticsPagination } from "@/components/admin/analytics-pagination";
import { getFirstPartyAnalyticsPages } from "@/lib/first-party-analytics.server";

export const metadata: Metadata = {
  title: "Analytics pages",
};

type PagesPageProps = {
  searchParams: Promise<{
    page?: string | string[];
    path?: string | string[];
    q?: string | string[];
  }>;
};

const numberFormatter = new Intl.NumberFormat("en-US");
const timestampFormatter = new Intl.DateTimeFormat("en-US", {
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
  month: "short",
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

function requestedQuery(value: string | string[] | undefined): string | undefined {
  const query = firstValue(value)?.trim();
  return query ? query.slice(0, 200) : undefined;
}

function formatTimestamp(value: string): string {
  const timestamp = new Date(value);
  return Number.isNaN(timestamp.valueOf())
    ? "Unknown"
    : timestampFormatter.format(timestamp);
}

export default async function AnalyticsPagesPage({
  searchParams,
}: PagesPageProps) {
  const params = await searchParams;
  const page = requestedPage(params.page);
  const path = requestedPath(params.path);
  const query = path ? undefined : requestedQuery(params.q);
  const data = await getFirstPartyAnalyticsPages({ page, path, query });

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
              Pages
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-6 text-white/45">
              Public paths viewed in the last 28 days. Query strings and URL
              fragments are never stored. Times are shown in UTC.
            </p>
          </div>
          <AnalyticsNavigation active="pages" />
        </div>

        <div className="mt-9 flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="font-mono text-[9px] uppercase tracking-[0.14em] text-white/30">
              Matching pages
            </p>
            <p className="mt-1 font-mono text-3xl tracking-[-0.05em] text-white/80 tabular-nums">
              {data.connected ? numberFormatter.format(data.totalPaths) : "—"}
            </p>
          </div>

          <form
            action="/admin/analytics/pages"
            method="get"
            className="flex w-full max-w-md items-center gap-2"
          >
            <label htmlFor="analytics-page-search" className="sr-only">
              Search page paths
            </label>
            <input
              id="analytics-page-search"
              name="q"
              type="search"
              defaultValue={query}
              placeholder="Search paths"
              className="min-h-11 min-w-0 flex-1 rounded-full border border-white/10 bg-white/[0.04] px-4 text-sm text-white/75 outline-none placeholder:text-white/25 focus:border-coral/60 focus:ring-2 focus:ring-coral/25"
            />
            <button
              type="submit"
              className="min-h-11 rounded-full bg-white px-5 text-xs font-semibold text-[#151d23] transition hover:bg-white/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral"
            >
              Search
            </button>
          </form>
        </div>

        {path ? (
          <div className="mt-4 flex w-fit items-center gap-2 rounded-full border border-blue-200/15 bg-blue-200/[0.06] py-1.5 pl-3.5 pr-2 text-xs text-blue-100/70">
            <span className="max-w-[75vw] truncate font-mono">{path}</span>
            <Link
              href="/admin/analytics/pages"
              aria-label={`Clear ${path} filter`}
              className="grid size-6 place-items-center rounded-full text-blue-100/45 transition hover:bg-white/10 hover:text-blue-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-100/70"
            >
              ×
            </Link>
          </div>
        ) : query ? (
          <div className="mt-4 flex w-fit items-center gap-2 rounded-full border border-white/10 bg-white/[0.035] py-1.5 pl-3.5 pr-2 text-xs text-white/50">
            <span>Search: {query}</span>
            <Link
              href="/admin/analytics/pages"
              aria-label={`Clear ${query} search`}
              className="grid size-6 place-items-center rounded-full text-white/35 transition hover:bg-white/10 hover:text-white/75 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/60"
            >
              ×
            </Link>
          </div>
        ) : null}

        <section
          className="mt-5 overflow-hidden rounded-3xl border border-white/10 bg-white/[0.035]"
          aria-labelledby="pages-table-heading"
        >
          <div className="flex items-center justify-between gap-4 border-b border-white/[0.07] px-5 py-4 sm:px-6">
            <h2
              id="pages-table-heading"
              className="text-sm font-medium text-white/70"
            >
              Page performance
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
          ) : data.pages.length === 0 ? (
            <p className="px-6 py-12 text-sm text-white/40">
              No pages match this view yet.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[920px] border-collapse text-left text-xs">
                <thead>
                  <tr className="border-b border-white/[0.07] font-mono text-[8px] uppercase tracking-[0.13em] text-white/25">
                    <th className="px-6 py-3 font-medium">Page</th>
                    <th className="px-4 py-3 text-right font-medium">Views</th>
                    <th className="px-4 py-3 text-right font-medium">Sessions</th>
                    <th className="px-4 py-3 text-right font-medium">
                      Views / session
                    </th>
                    <th className="px-4 py-3 text-right font-medium">First seen</th>
                    <th className="px-6 py-3 text-right font-medium">Last seen</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.06]">
                  {data.pages.map((pageRow) => (
                    <tr
                      key={pageRow.path}
                      className="transition hover:bg-white/[0.025]"
                    >
                      <td className="max-w-xl px-6 py-4">
                        <a
                          href={pageRow.path}
                          target="_blank"
                          rel="noreferrer"
                          className="block truncate font-mono text-blue-200/70 underline decoration-blue-200/20 underline-offset-4 transition hover:text-blue-100 hover:decoration-blue-100/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-100/70"
                        >
                          {pageRow.path}
                        </a>
                      </td>
                      <td className="px-4 py-4 text-right font-mono text-white/75 tabular-nums">
                        {numberFormatter.format(pageRow.pageViews)}
                      </td>
                      <td className="px-4 py-4 text-right">
                        <Link
                          href={{
                            pathname: "/admin/analytics/sessions",
                            query: { path: pageRow.path },
                          }}
                          className="font-mono text-blue-200/65 underline decoration-blue-200/20 underline-offset-4 transition hover:text-blue-100 hover:decoration-blue-100/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-100/70 tabular-nums"
                        >
                          {numberFormatter.format(pageRow.sessions)}
                        </Link>
                      </td>
                      <td className="px-4 py-4 text-right font-mono text-white/45 tabular-nums">
                        {pageRow.viewsPerSession.toFixed(2)}
                      </td>
                      <td className="whitespace-nowrap px-4 py-4 text-right text-white/40">
                        {formatTimestamp(pageRow.firstViewedAt)}
                      </td>
                      <td className="whitespace-nowrap px-6 py-4 text-right text-white/55">
                        {formatTimestamp(pageRow.lastViewedAt)}
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
              pathname="/admin/analytics/pages"
              query={{ path, q: query }}
              totalPages={data.totalPages}
            />
          ) : null}
        </section>
      </div>
    </main>
  );
}
