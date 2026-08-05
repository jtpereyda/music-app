import Link from "next/link";
import { notFound } from "next/navigation";
import { KeywordPositionChart } from "@/components/admin/keyword-position-chart";
import {
  getKeywordDashboard,
  type KeywordProgress,
  type KeywordTargetRow,
} from "@/lib/keyword-targets";
import {
  getTrackedKeywordDetails,
  type KeywordHistoryPoint,
} from "@/lib/seo-tracking.server";

type KeywordDetailsPageProps = {
  params: Promise<{ keyword: string }>;
  searchParams: Promise<{ target?: string | string[] }>;
};

const numberFormatter = new Intl.NumberFormat("en-US");
const percentFormatter = new Intl.NumberFormat("en-US", {
  style: "percent",
  maximumFractionDigits: 1,
});

const sourceLabels: Record<KeywordHistoryPoint["source"], string> = {
  google_search_console: "Search Console",
  ahrefs: "Ahrefs",
  manual: "Manual",
};

const stageLabels: Record<KeywordProgress["stage"], string> = {
  planned: "Planned",
  live: "Live",
  indexed: "Indexed",
  visible: "Visible",
  top20: "Top 20",
  page1: "Page 1",
  top3: "Top 3",
};

function targetOrigin(): string {
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

function detailsHref(row: KeywordTargetRow) {
  return {
    pathname: `/admin/keywords/${encodeURIComponent(row.keyword)}`,
    query: { target: row.targetPath },
  };
}

function googleSearchUrl(keyword: string): string {
  return `https://www.google.com/search?q=${encodeURIComponent(keyword)}`;
}

function ahrefsKeywordUrl(keyword: string): string {
  return `https://app.ahrefs.com/keywords-explorer/google/us/overview?keyword=${encodeURIComponent(keyword)}`;
}

function formatDate(value: string | null): string {
  if (!value) return "Not measured";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value.slice(0, 10)}T00:00:00Z`));
}

function formatTimestamp(value: string | null): string {
  if (!value) return "Not synced";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatPosition(value: number | null): string {
  if (value === null) return "—";
  return Number.isInteger(value) ? value.toString() : value.toFixed(1);
}

function formatMovement(value: number | null): string {
  if (value === null) return "—";
  if (value === 0) return "0";
  return `${value > 0 ? "+" : ""}${value.toFixed(1)}`;
}

function rankingUrlLabel(value: string): string {
  try {
    return new URL(value).pathname;
  } catch {
    return value;
  }
}

function movementClass(value: number | null): string {
  if (value === null || value === 0) return "text-white/40";
  return value > 0 ? "text-emerald-200" : "text-rose-200";
}

function historyWithMovement(history: KeywordHistoryPoint[]) {
  const previousBySource = new Map<KeywordHistoryPoint["source"], number>();
  return history.map((point) => {
    const previousPosition = previousBySource.get(point.source) ?? null;
    const movement =
      point.position !== null && previousPosition !== null
        ? previousPosition - point.position
        : null;
    if (point.position !== null) {
      previousBySource.set(point.source, point.position);
    }
    return { ...point, movement };
  });
}

function StatusPill({
  label,
  state,
}: {
  label: string;
  state: boolean | null;
}) {
  const classes =
    state === true
      ? "border-emerald-300/15 bg-emerald-300/10 text-emerald-200"
      : state === false
        ? "border-amber-300/15 bg-amber-300/10 text-amber-100"
        : "border-white/10 bg-white/[0.035] text-white/35";
  return (
    <span
      className={`inline-flex rounded-full border px-2.5 py-1 font-mono text-[8px] uppercase tracking-[0.12em] ${classes}`}
    >
      {label}
    </span>
  );
}

export default async function KeywordDetailsPage({
  params,
  searchParams,
}: KeywordDetailsPageProps) {
  const [{ keyword }, query] = await Promise.all([params, searchParams]);
  const requestedTarget = Array.isArray(query.target)
    ? query.target[0]
    : query.target;
  const dashboard = getKeywordDashboard();
  const candidates = dashboard.rows.filter((row) => row.keyword === keyword);
  const selectedRow =
    candidates.find((row) => row.targetPath === requestedTarget) ??
    candidates[0];
  if (!selectedRow) notFound();

  const details = await getTrackedKeywordDetails(selectedRow);
  const row = details.row;
  const progress = row.progress;
  if (!progress) notFound();

  const measuredHistory = details.history.filter(
    (point) => point.position !== null,
  );
  const lastMeasured = measuredHistory.at(-1) ?? null;
  const lastSnapshot = details.history.at(-1) ?? null;
  const historyRows = historyWithMovement(details.history).toReversed();
  const targetUrl = new URL(row.targetPath, targetOrigin()).toString();
  const metricCards = [
    {
      label: "Current position",
      value: formatPosition(progress.currentPosition),
      detail: lastMeasured
        ? `${sourceLabels[lastMeasured.source]} · ${formatDate(lastMeasured.snapshotDate)}`
        : "No measured position yet",
      accent: "text-[#ffad9c]",
    },
    {
      label: "Best position",
      value: formatPosition(progress.bestPosition),
      detail: `${formatMovement(progress.positionChange7d)} over 7d · ${formatMovement(progress.positionChange28d)} over 28d`,
      accent: "text-emerald-200",
    },
    {
      label: "Impressions · 28d",
      value: numberFormatter.format(progress.impressions28d),
      detail: `${numberFormatter.format(progress.clicks28d)} Google clicks`,
      accent: "text-[#9fd2e8]",
    },
    {
      label: "Search CTR · 28d",
      value:
        progress.ctr28d === null
          ? "—"
          : percentFormatter.format(progress.ctr28d),
      detail: `${details.history.length} daily snapshots stored`,
      accent: "text-white",
    },
  ];

  return (
    <main className="px-5 py-8 sm:px-8 sm:py-10 lg:px-10 lg:py-12">
      <div className="mx-auto w-full max-w-[1440px]">
        <Link
          href="/admin"
          className="inline-flex items-center gap-2 rounded-lg text-xs font-medium text-white/45 transition hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral"
        >
          <span aria-hidden="true">←</span>
          All keywords
        </Link>

        <div className="mt-7 flex flex-col gap-7 xl:flex-row xl:items-end xl:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-coral/20 bg-coral/10 px-2.5 py-1 font-mono text-[8px] uppercase tracking-[0.13em] text-[#ffad9c]">
                {row.role} keyword
              </span>
              <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 font-mono text-[8px] uppercase tracking-[0.13em] text-white/40">
                P{row.priority} · {stageLabels[progress.stage]}
              </span>
              {!details.connected ? (
                <span className="rounded-full border border-amber-300/15 bg-amber-300/10 px-2.5 py-1 font-mono text-[8px] uppercase tracking-[0.13em] text-amber-100">
                  Database unavailable
                </span>
              ) : null}
            </div>
            <h1 className="mt-4 max-w-5xl break-words text-4xl font-medium leading-[0.98] tracking-[-0.055em] sm:text-5xl lg:text-6xl">
              {row.keyword}
            </h1>
            <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-2 text-sm">
              <span className="text-white/35">Targeting</span>
              <a
                href={targetUrl}
                target="_blank"
                rel="noreferrer"
                className="break-all font-mono text-[11px] text-white/65 underline decoration-white/15 underline-offset-4 transition hover:text-white hover:decoration-white/45 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral"
              >
                {row.targetPath}
              </a>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <a
              href={googleSearchUrl(row.keyword)}
              target="_blank"
              rel="noreferrer"
              className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-white/10 bg-white/[0.035] px-4 text-xs font-semibold text-white/60 transition hover:border-white/20 hover:bg-white/[0.07] hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral"
            >
              <span className="grid size-5 place-items-center rounded-md bg-white text-[10px] font-bold text-[#10171d]">
                G
              </span>
              Google result
            </a>
            <a
              href={ahrefsKeywordUrl(row.keyword)}
              target="_blank"
              rel="noreferrer"
              className="inline-flex min-h-11 items-center rounded-xl border border-white/10 bg-white/[0.035] px-4 text-xs font-semibold text-white/60 transition hover:border-white/20 hover:bg-white/[0.07] hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral"
            >
              Open in Ahrefs ↗
            </a>
          </div>
        </div>

        {candidates.length > 1 ? (
          <nav
            aria-label="Target-page mapping"
            className="mt-7 flex flex-wrap gap-2 rounded-2xl border border-white/[0.07] bg-white/[0.025] p-2"
          >
            {candidates.map((candidate) => {
              const selected = candidate.targetPath === row.targetPath;
              return (
                <Link
                  key={candidate.id}
                  href={detailsHref(candidate)}
                  aria-current={selected ? "page" : undefined}
                  className={`rounded-xl px-3 py-2 font-mono text-[9px] transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral ${
                    selected
                      ? "bg-white/10 text-white"
                      : "text-white/35 hover:bg-white/5 hover:text-white/65"
                  }`}
                >
                  {candidate.targetPath}
                </Link>
              );
            })}
          </nav>
        ) : null}

        <section
          className="mt-8 grid gap-px overflow-hidden rounded-[1.6rem] border border-white/10 bg-white/10 sm:grid-cols-2 xl:grid-cols-4"
          aria-label="Keyword ranking summary"
        >
          {metricCards.map((card) => (
            <article key={card.label} className="bg-[#151d23] p-5 sm:p-6">
              <p className="font-mono text-[8px] uppercase tracking-[0.15em] text-white/35">
                {card.label}
              </p>
              <p
                className={`mt-4 font-mono text-4xl font-medium tracking-[-0.06em] tabular-nums ${card.accent}`}
              >
                {card.value}
              </p>
              <p className="mt-2 text-[11px] leading-5 text-white/35">
                {card.detail}
              </p>
            </article>
          ))}
        </section>

        <section className="mt-5 rounded-[1.75rem] border border-white/10 bg-white/[0.035] p-5 sm:p-6 lg:p-7">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="font-mono text-[8px] uppercase tracking-[0.15em] text-white/30">
                Daily snapshots · 120-day window
              </p>
              <h2 className="mt-2 text-2xl font-semibold tracking-[-0.04em]">
                Position history
              </h2>
              <p className="mt-1 text-xs leading-5 text-white/35">
                Lower is better. Days without impressions remain stored but do
                not create a plotted position.
              </p>
            </div>
            <p className="font-mono text-[9px] uppercase tracking-[0.1em] text-white/25">
              Last snapshot {formatDate(lastSnapshot?.snapshotDate ?? null)}
            </p>
          </div>
          <div className="mt-6">
            <KeywordPositionChart points={details.history} />
          </div>
        </section>

        <section className="mt-5 grid gap-5 xl:grid-cols-[1.35fr_0.65fr]">
          <article className="rounded-[1.75rem] border border-white/10 bg-white/[0.035] p-5 sm:p-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="font-mono text-[8px] uppercase tracking-[0.15em] text-white/30">
                  Target health
                </p>
                <h2 className="mt-2 text-xl font-semibold tracking-[-0.035em]">
                  Search readiness
                </h2>
              </div>
              <div className="flex flex-wrap justify-end gap-2">
                <StatusPill
                  label={progress.live ? "Live" : "Not confirmed live"}
                  state={progress.live}
                />
                <StatusPill
                  label={progress.indexed ? "Indexed" : "Not confirmed indexed"}
                  state={progress.indexed}
                />
                <StatusPill
                  label={
                    progress.rankingUrlMatchesTarget === true
                      ? "Correct URL ranks"
                      : progress.rankingUrlMatchesTarget === false
                        ? "Other URL ranks"
                        : "Ranking URL unconfirmed"
                  }
                  state={progress.rankingUrlMatchesTarget}
                />
              </div>
            </div>

            <dl className="mt-5 grid gap-3 sm:grid-cols-2">
              {[
                ["Title", row.seo.title],
                ["H1", row.seo.h1],
                ["Meta description", row.seo.metaDescription],
                ["First paragraph", row.seo.firstParagraph],
              ].map(([label, value]) => (
                <div
                  key={label}
                  className="rounded-xl border border-white/[0.065] bg-black/15 p-4"
                >
                  <dt className="font-mono text-[8px] uppercase tracking-[0.12em] text-white/30">
                    {label}
                  </dt>
                  <dd
                    className={`mt-2 text-xs leading-5 ${
                      value ? "text-white/65" : "italic text-white/25"
                    }`}
                  >
                    {value ?? "Not captured"}
                  </dd>
                </div>
              ))}
            </dl>
            <p className="mt-3 text-right font-mono text-[8px] uppercase tracking-[0.1em] text-white/20">
              Page checked {formatTimestamp(row.seo.checkedAt)}
            </p>
          </article>

          <article className="rounded-[1.75rem] border border-white/10 bg-white/[0.035] p-5 sm:p-6">
            <p className="font-mono text-[8px] uppercase tracking-[0.15em] text-white/30">
              Research baseline
            </p>
            <h2 className="mt-2 text-xl font-semibold tracking-[-0.035em]">
              Opportunity
            </h2>
            <dl className="mt-6 divide-y divide-white/[0.07]">
              {[
                ["US monthly volume", row.volume],
                ["Keyword difficulty", row.difficulty],
                ["Traffic potential", row.trafficPotential],
              ].map(([label, value]) => (
                <div
                  key={label}
                  className="flex items-center justify-between gap-4 py-4 first:pt-0"
                >
                  <dt className="text-xs text-white/35">{label}</dt>
                  <dd className="font-mono text-lg tabular-nums text-white/75">
                    {typeof value === "number"
                      ? numberFormatter.format(value)
                      : "—"}
                  </dd>
                </div>
              ))}
            </dl>
            <div className="mt-4 rounded-xl border border-white/[0.07] bg-black/10 p-4">
              <p className="font-mono text-[8px] uppercase tracking-[0.12em] text-white/25">
                Mapping
              </p>
              <p className="mt-2 text-xs text-white/55">
                {row.role} · priority {row.priority} · {row.pageType.replaceAll("_", " ")}
              </p>
            </div>
          </article>
        </section>

        <section className="mt-5 overflow-hidden rounded-[1.75rem] border border-white/10 bg-white/[0.035]">
          <div className="flex flex-col gap-2 border-b border-white/[0.07] px-5 py-5 sm:flex-row sm:items-end sm:justify-between sm:px-6">
            <div>
              <p className="font-mono text-[8px] uppercase tracking-[0.15em] text-white/30">
                Source records
              </p>
              <h2 className="mt-2 text-xl font-semibold tracking-[-0.035em]">
                Snapshot ledger
              </h2>
            </div>
            <p className="text-[11px] text-white/30">
              Movement compares with the prior measured position from the same
              source.
            </p>
          </div>

          {historyRows.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[920px] border-collapse text-left">
                <thead>
                  <tr className="border-b border-white/[0.07] font-mono text-[8px] uppercase tracking-[0.12em] text-white/30">
                    <th className="px-6 py-3 font-medium">Snapshot</th>
                    <th className="px-4 py-3 text-right font-medium">Position</th>
                    <th className="px-4 py-3 text-right font-medium">Movement</th>
                    <th className="px-4 py-3 text-right font-medium">Impressions</th>
                    <th className="px-4 py-3 text-right font-medium">Clicks</th>
                    <th className="px-4 py-3 text-right font-medium">CTR</th>
                    <th className="px-4 py-3 font-medium">Ranking URL</th>
                    <th className="px-6 py-3 font-medium">Source</th>
                  </tr>
                </thead>
                <tbody>
                  {historyRows.map((point, index) => (
                    <tr
                      key={`${point.snapshotDate}-${point.source}-${point.country}-${point.device}-${index}`}
                      className="border-b border-white/[0.055] text-xs last:border-0 hover:bg-white/[0.025]"
                    >
                      <td className="px-6 py-3 font-medium text-white/65">
                        {formatDate(point.snapshotDate)}
                      </td>
                      <td className="px-4 py-3 text-right font-mono tabular-nums text-white/75">
                        {formatPosition(point.position)}
                      </td>
                      <td
                        className={`px-4 py-3 text-right font-mono tabular-nums ${movementClass(point.movement)}`}
                      >
                        {formatMovement(point.movement)}
                      </td>
                      <td className="px-4 py-3 text-right font-mono tabular-nums text-white/55">
                        {numberFormatter.format(point.impressions)}
                      </td>
                      <td className="px-4 py-3 text-right font-mono tabular-nums text-white/55">
                        {numberFormatter.format(point.clicks)}
                      </td>
                      <td className="px-4 py-3 text-right font-mono tabular-nums text-white/55">
                        {point.ctr === null
                          ? "—"
                          : percentFormatter.format(point.ctr)}
                      </td>
                      <td className="max-w-[300px] px-4 py-3">
                        {point.rankingUrl ? (
                          <a
                            href={point.rankingUrl}
                            target="_blank"
                            rel="noreferrer"
                            className="block truncate font-mono text-[10px] text-[#9fd2e8] underline decoration-blue/30 underline-offset-4 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral"
                          >
                            {rankingUrlLabel(point.rankingUrl)}
                          </a>
                        ) : (
                          <span className="text-white/20">No ranking URL</span>
                        )}
                      </td>
                      <td className="px-6 py-3 text-[10px] text-white/40">
                        {sourceLabels[point.source]}
                        <span className="mt-0.5 block font-mono text-[8px] uppercase tracking-[0.08em] text-white/20">
                          {point.country} · {point.device}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="px-6 py-14 text-center">
              <p className="text-sm font-medium text-white/60">
                No snapshots stored for this mapping.
              </p>
              <p className="mt-1 text-xs text-white/30">
                Run a tracking sync after the target page starts receiving
                Search Console data.
              </p>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
