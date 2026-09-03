import { KeywordTable } from "@/components/admin/keyword-table";
import { SeoSyncButton } from "@/components/admin/seo-sync-button";
import { SeoTrendChart } from "@/components/admin/seo-trend-chart";
import {
  getKeywordDashboard,
  type KeywordProgressStage,
} from "@/lib/keyword-targets";
import { getFirstPartyAnalyticsSummary } from "@/lib/first-party-analytics.server";
import { getTrackedKeywordDashboard } from "@/lib/seo-tracking.server";

const compactNumberFormatter = new Intl.NumberFormat("en-US", {
  notation: "compact",
  maximumFractionDigits: 1,
});

const percentFormatter = new Intl.NumberFormat("en-US", {
  style: "percent",
  maximumFractionDigits: 1,
});

const progressStages = [
  {
    key: "planned",
    label: "Planned",
    description: "Mapped as a target; a live page has not been confirmed.",
  },
  {
    key: "live",
    label: "Live",
    description: "The target URL responds successfully.",
  },
  {
    key: "indexed",
    label: "Indexed",
    description: "Google Search Console confirms the URL is indexed.",
  },
  {
    key: "visible",
    label: "Visible",
    description: "The keyword has an impression or measured position.",
  },
  {
    key: "top20",
    label: "Top 20",
    description: "The latest measured position is 20 or better.",
  },
  {
    key: "page1",
    label: "Page 1",
    description: "The latest measured position is 10 or better.",
  },
  {
    key: "top3",
    label: "Top 3",
    description: "The latest measured position is 3 or better.",
  },
] as const satisfies ReadonlyArray<{
  key: KeywordProgressStage;
  label: string;
  description: string;
}>;

function getTargetOrigin(): string {
  const configured = process.env.SITE_URL ?? "https://transposify.com";
  const withProtocol = configured.startsWith("http")
    ? configured
    : `https://${configured}`;

  try {
    return new URL(withProtocol).origin;
  } catch {
    return "https://transposify.com";
  }
}

export default async function AdminDashboardPage() {
  const dashboard = getKeywordDashboard();
  const [tracking, firstPartyAnalytics] = await Promise.all([
    getTrackedKeywordDashboard(dashboard.rows),
    getFirstPartyAnalyticsSummary(),
  ]);
  const { summary } = dashboard;
  const targetOrigin = getTargetOrigin();
  const researchDate = new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${dashboard.researchDate}T00:00:00Z`));
  const ahrefsSiteUrl = `https://app.ahrefs.com/site-explorer/overview/v2/subdomains/live?target=${encodeURIComponent(new URL(targetOrigin).hostname)}`;
  const pageOneKeywords =
    tracking.summary.stageCounts.page1 + tracking.summary.stageCounts.top3;
  const lastSynced = tracking.summary.lastSyncedAt
    ? new Intl.DateTimeFormat("en-US", {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      }).format(new Date(tracking.summary.lastSyncedAt))
    : "Not synced yet";

  const cards = [
    {
      label: "Target keywords",
      value: summary.uniqueKeywords.toString(),
      detail: `${summary.keywordMappings} page mappings`,
      accent: "text-[#ffad9c]",
    },
    {
      label: "Ranking on page 1",
      value: pageOneKeywords.toString(),
      detail: `${tracking.summary.stageCounts.top3} in the top 3`,
      accent: "text-emerald-200",
    },
    {
      label: "Search visibility · 28d",
      value: compactNumberFormatter.format(tracking.summary.impressions28d),
      detail: `${compactNumberFormatter.format(tracking.summary.clicks28d)} clicks · ${compactNumberFormatter.format(tracking.summary.organicSessions28d)} organic sessions`,
      accent: "text-[#9fd2e8]",
    },
    {
      label: "Product outcomes · 28d",
      value: compactNumberFormatter.format(tracking.summary.downloads28d),
      detail: `${compactNumberFormatter.format(tracking.summary.keyEvents28d)} GA4 key events`,
      accent: "text-white",
    },
    {
      label: "Organic bounce · 28d",
      value:
        tracking.summary.bounceRate28d === null
          ? "—"
          : percentFormatter.format(tracking.summary.bounceRate28d),
      detail:
        tracking.summary.bounceRate28d === null
          ? "Awaiting GA4 organic sessions"
          : `${compactNumberFormatter.format(tracking.summary.engagedSessions28d)} of ${compactNumberFormatter.format(tracking.summary.engagementMeasuredSessions28d)} sessions engaged · quick-return proxy`,
      accent: "text-amber-200",
    },
  ];

  return (
    <main className="px-5 py-10 sm:px-8 sm:py-12 lg:px-10 lg:py-14">
      <div className="mx-auto w-full max-w-[1440px]">
        <div className="flex flex-col gap-7 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <p className="font-mono text-[9px] uppercase tracking-[0.18em] text-coral">
                SEO · Bottom of funnel
              </p>
              <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 font-mono text-[8px] uppercase tracking-[0.14em] text-white/40">
                {dashboard.market} · {dashboard.language.toUpperCase()}
              </span>
            </div>
            <h1 className="mt-4 max-w-4xl text-5xl font-medium leading-[0.94] tracking-[-0.065em] sm:text-6xl lg:text-7xl">
              Keyword progress,
              <span className="block text-white/35">without the tab maze.</span>
            </h1>
            <p className="mt-5 max-w-2xl text-sm leading-6 text-white/45 sm:text-base sm:leading-7">
              Daily snapshots connect launch readiness, indexation, search
              visibility, rankings, clicks, and product outcomes without
              erasing historical movement.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="rounded-2xl border border-white/10 bg-white/[0.035] px-4 py-3">
              <p className="font-mono text-[8px] uppercase tracking-[0.14em] text-white/30">
                Last tracking sync
              </p>
              <p className="mt-1 text-sm font-medium text-white/70">
                {lastSynced}
              </p>
            </div>
            <SeoSyncButton />
            <a
              href={ahrefsSiteUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex min-h-14 items-center gap-2 rounded-2xl bg-coral px-5 text-sm font-semibold text-white shadow-[0_12px_34px_rgba(231,104,77,0.2)] transition hover:-translate-y-0.5 hover:bg-[#dc6047] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/80"
            >
              Open Site Explorer
              <span aria-hidden="true">↗</span>
            </a>
          </div>
        </div>

        <section
          className="mt-10 grid gap-px overflow-hidden rounded-[1.75rem] border border-white/10 bg-white/10 sm:grid-cols-2 xl:grid-cols-5"
          aria-label="Keyword overview"
        >
          {cards.map((card) => (
            <article key={card.label} className="bg-[#151d23] p-6 sm:p-7">
              <p className="font-mono text-[8px] uppercase tracking-[0.15em] text-white/35">
                {card.label}
              </p>
              <p
                className={`mt-5 font-mono text-4xl font-medium tracking-[-0.06em] tabular-nums ${card.accent}`}
              >
                {card.value}
              </p>
              <p className="mt-2 text-xs text-white/35">{card.detail}</p>
            </article>
          ))}
        </section>

        <section
          className="mt-4 overflow-hidden rounded-3xl border border-white/10 bg-white/[0.035]"
          aria-labelledby="first-party-analytics-heading"
        >
          <div className="flex flex-col gap-3 border-b border-white/10 px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="font-mono text-[8px] uppercase tracking-[0.15em] text-emerald-200/65">
                First-party analytics · 28d
              </p>
              <h2
                id="first-party-analytics-heading"
                className="mt-1 text-lg font-medium tracking-[-0.025em] text-white/80"
              >
                Sessions and page traffic
              </h2>
            </div>
            <span
              className={`w-fit rounded-full border px-3 py-1 font-mono text-[8px] uppercase tracking-[0.13em] ${
                firstPartyAnalytics.connected
                  ? "border-emerald-200/15 bg-emerald-200/[0.06] text-emerald-200/70"
                  : "border-amber-200/15 bg-amber-200/[0.06] text-amber-200/70"
              }`}
            >
              {firstPartyAnalytics.connected
                ? "Collecting"
                : "Migration needed"}
            </span>
          </div>

          <div className="grid lg:grid-cols-[0.72fr_1.28fr]">
            <div className="grid gap-px bg-white/10 sm:grid-cols-3 lg:grid-cols-1">
              {[
                {
                  label: "Anonymous sessions",
                  value: firstPartyAnalytics.connected
                    ? compactNumberFormatter.format(
                        firstPartyAnalytics.sessions28d,
                      )
                    : "—",
                },
                {
                  label: "Page views",
                  value: firstPartyAnalytics.connected
                    ? compactNumberFormatter.format(
                        firstPartyAnalytics.pageViews28d,
                      )
                    : "—",
                },
                {
                  label: "Views per session",
                  value:
                    firstPartyAnalytics.connected &&
                    firstPartyAnalytics.viewsPerSession28d !== null
                      ? firstPartyAnalytics.viewsPerSession28d.toFixed(1)
                      : "—",
                },
              ].map((metric) => (
                <article key={metric.label} className="bg-[#151d23] px-6 py-5">
                  <p className="font-mono text-[8px] uppercase tracking-[0.14em] text-white/30">
                    {metric.label}
                  </p>
                  <p className="mt-2 font-mono text-3xl tracking-[-0.05em] text-white/80 tabular-nums">
                    {metric.value}
                  </p>
                </article>
              ))}
            </div>

            <div className="p-6">
              <div className="flex items-center justify-between gap-4">
                <p className="text-sm font-medium text-white/65">Top pages</p>
                <p className="font-mono text-[8px] uppercase tracking-[0.12em] text-white/25">
                  Path only · no query data
                </p>
              </div>

              {firstPartyAnalytics.topPages28d.length > 0 ? (
                <ol className="mt-4 divide-y divide-white/[0.07]">
                  {firstPartyAnalytics.topPages28d.map((page) => (
                    <li
                      key={page.path}
                      className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-5 py-3 text-xs"
                    >
                      <span className="truncate font-mono text-white/55">
                        {page.path}
                      </span>
                      <span className="text-right text-white/35">
                        {compactNumberFormatter.format(page.sessions)} sessions
                      </span>
                      <span className="min-w-14 text-right font-mono text-white/70 tabular-nums">
                        {compactNumberFormatter.format(page.pageViews)} views
                      </span>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="mt-5 text-xs leading-5 text-white/35">
                  {firstPartyAnalytics.connected
                    ? "No public page views have been recorded in this window yet."
                    : "Apply database/migrations/0006_first_party_analytics.sql to begin collecting first-party traffic."}
                </p>
              )}
            </div>
          </div>
        </section>

        <section className="mt-4 grid gap-4 lg:grid-cols-[1.35fr_0.65fr]">
          <div className="rounded-3xl border border-white/10 bg-white/[0.035] p-6">
            <div className="flex items-center justify-between gap-5">
              <div>
                <p className="font-mono text-[8px] uppercase tracking-[0.15em] text-white/30">
                  Progress pipeline
                </p>
                <p className="mt-2 text-sm font-medium text-white/70">
                  Current highest stage for every keyword mapping
                </p>
              </div>
              <span className="font-mono text-[10px] text-white/35">
                {tracking.summary.trackedKeywords} tracked
              </span>
            </div>
            <ol className="mt-5 grid gap-2 sm:grid-cols-2 xl:grid-cols-7">
              {progressStages.map((stage, index) => (
                <li
                  key={stage.key}
                  className="relative rounded-xl border border-white/[0.07] bg-black/10 px-3 py-3"
                >
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-[10px] font-medium text-white/50">
                      {stage.label}
                    </p>
                    <p className="font-mono text-lg tabular-nums text-white/75">
                      {tracking.summary.stageCounts[stage.key]}
                    </p>
                  </div>
                  <p className="mt-2 text-[9px] leading-4 text-white/28">
                    {stage.description}
                  </p>
                  {index < progressStages.length - 1 ? (
                    <span
                      aria-hidden="true"
                      className="absolute -right-[9px] top-1/2 z-10 hidden -translate-y-1/2 font-mono text-xs text-coral/55 xl:block"
                    >
                      →
                    </span>
                  ) : null}
                </li>
              ))}
            </ol>
            <p className="mt-3 text-xs leading-5 text-white/30">
              A mapping shows its highest earned state. The flow moves left to
              right; research coverage remains a separate table column.
            </p>
          </div>

          <div
            className={`rounded-3xl border p-6 ${
              tracking.summary.lastSyncStatus === "failed"
                ? "border-rose-200/10 bg-rose-200/[0.045]"
                : "border-amber-200/10 bg-amber-200/[0.045]"
            }`}
          >
            <div className="flex items-start gap-3">
              <span className="mt-0.5 grid size-7 shrink-0 place-items-center rounded-full bg-amber-200/10 text-xs text-amber-200">
                !
              </span>
              <div>
                <p className="text-sm font-medium text-amber-100/80">
                  {tracking.summary.connected
                    ? tracking.summary.lastSyncStatus
                      ? `Last sync: ${tracking.summary.lastSyncStatus}`
                      : "Tracking storage connected"
                    : "Tracking setup needed"}
                </p>
                <p className="mt-1 text-xs leading-5 text-white/35">
                  {tracking.summary.lastSyncMessage ??
                    "Apply the SEO migration and configure Search Console credentials. Site checks will work before Google is connected."}
                </p>
                <p className="mt-3 font-mono text-[8px] uppercase tracking-[0.12em] text-white/25">
                  Research baseline {researchDate} · {summary.measurementCoverage}% complete
                </p>
              </div>
            </div>
          </div>
        </section>

        <SeoTrendChart points={tracking.trend} />

        <section className="mt-8">
          <KeywordTable rows={tracking.rows} targetOrigin={targetOrigin} />
        </section>
      </div>
    </main>
  );
}
