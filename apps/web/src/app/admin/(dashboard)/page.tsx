import { KeywordTable } from "@/components/admin/keyword-table";
import { getKeywordDashboard } from "@/lib/keyword-targets";

const compactNumberFormatter = new Intl.NumberFormat("en-US", {
  notation: "compact",
  maximumFractionDigits: 1,
});

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

export default function AdminDashboardPage() {
  const dashboard = getKeywordDashboard();
  const { summary } = dashboard;
  const targetOrigin = getTargetOrigin();
  const researchDate = new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${dashboard.researchDate}T00:00:00Z`));
  const ahrefsSiteUrl = `https://app.ahrefs.com/site-explorer/overview/v2/subdomains/live?target=${encodeURIComponent(new URL(targetOrigin).hostname)}`;

  const cards = [
    {
      label: "Target keywords",
      value: summary.uniqueKeywords.toString(),
      detail: `${summary.keywordMappings} page mappings`,
      accent: "text-[#ffad9c]",
    },
    {
      label: "Known monthly demand",
      value: compactNumberFormatter.format(summary.knownMonthlyVolume),
      detail: `${compactNumberFormatter.format(summary.knownTrafficPotential)} traffic potential`,
      accent: "text-[#9fd2e8]",
    },
    {
      label: "Target pages",
      value: summary.targetPages.toString(),
      detail: `${summary.priorityZeroPages} P0 · ${summary.priorityOnePages} P1`,
      accent: "text-white",
    },
    {
      label: "Metric coverage",
      value: `${summary.measurementCoverage}%`,
      detail: `${summary.measuredKeywords} of ${summary.uniqueKeywords} researched`,
      accent: "text-emerald-200",
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
              A research baseline for every launch keyword and its target page.
              Use the Ahrefs shortcuts to refresh SERPs and validate rankings.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="rounded-2xl border border-white/10 bg-white/[0.035] px-4 py-3">
              <p className="font-mono text-[8px] uppercase tracking-[0.14em] text-white/30">
                Research snapshot
              </p>
              <p className="mt-1 text-sm font-medium text-white/70">
                {researchDate}
              </p>
            </div>
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
          className="mt-10 grid gap-px overflow-hidden rounded-[1.75rem] border border-white/10 bg-white/10 sm:grid-cols-2 xl:grid-cols-4"
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

        <section className="mt-4 grid gap-4 lg:grid-cols-[1.35fr_0.65fr]">
          <div className="rounded-3xl border border-white/10 bg-white/[0.035] p-6">
            <div className="flex items-center justify-between gap-5">
              <div>
                <p className="font-mono text-[8px] uppercase tracking-[0.15em] text-white/30">
                  Research completeness
                </p>
                <p className="mt-2 text-sm font-medium text-white/70">
                  {summary.measuredKeywords} keywords have at least one metric
                </p>
              </div>
              <span className="font-mono text-lg text-emerald-200">
                {summary.measurementCoverage}%
              </span>
            </div>
            <div className="mt-5 h-2 overflow-hidden rounded-full bg-white/[0.065]">
              <div
                className="h-full rounded-full bg-gradient-to-r from-blue to-emerald-300"
                style={{ width: `${summary.measurementCoverage}%` }}
              />
            </div>
            <p className="mt-3 text-xs leading-5 text-white/30">
              Rankings are not synced yet; “complete” currently means volume,
              keyword difficulty, and traffic potential are present in the
              source file.
            </p>
          </div>

          <div className="rounded-3xl border border-amber-200/10 bg-amber-200/[0.045] p-6">
            <div className="flex items-start gap-3">
              <span className="mt-0.5 grid size-7 shrink-0 place-items-center rounded-full bg-amber-200/10 text-xs text-amber-200">
                !
              </span>
              <div>
                <p className="text-sm font-medium text-amber-100/80">
                  {summary.duplicateMappings} overlapping keyword mapping
                  {summary.duplicateMappings === 1 ? "" : "s"}
                </p>
                <p className="mt-1 text-xs leading-5 text-white/35">
                  The table flags keywords assigned to multiple pages so you
                  can check for search cannibalization early.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section className="mt-8">
          <KeywordTable rows={dashboard.rows} targetOrigin={targetOrigin} />
        </section>
      </div>
    </main>
  );
}
