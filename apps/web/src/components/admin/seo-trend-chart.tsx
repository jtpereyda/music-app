import type { SeoTrendPoint } from "@/lib/seo-tracking.server";

type MetricKey =
  | "impressions"
  | "clicks"
  | "organicSessions"
  | "downloads";

const numberFormatter = new Intl.NumberFormat("en-US", {
  notation: "compact",
  maximumFractionDigits: 1,
});

const percentFormatter = new Intl.NumberFormat("en-US", {
  style: "percent",
  maximumFractionDigits: 1,
});

function MetricTrend({
  color,
  label,
  metric,
  points,
}: {
  color: string;
  label: string;
  metric: MetricKey;
  points: SeoTrendPoint[];
}) {
  const values = points.map((point) => point[metric]);
  const maximum = Math.max(...values, 1);
  const total = values.reduce((sum, value) => sum + value, 0);

  return (
    <article className="rounded-2xl border border-white/[0.07] bg-black/10 p-4">
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-xs font-medium text-white/50">{label}</p>
        <p className="font-mono text-sm tabular-nums text-white/75">
          {numberFormatter.format(total)}
        </p>
      </div>
      <div
        role="img"
        aria-label={`${label} by week for the last 12 weeks`}
        className="mt-5 flex h-20 items-end gap-1"
      >
        {points.map((point) => {
          const value = point[metric];
          const height = value === 0 ? 2 : Math.max(7, (value / maximum) * 100);
          return (
            <div
              key={point.startDate}
              className={`min-w-0 flex-1 rounded-t-sm ${color}`}
              style={{ height: `${height}%` }}
              title={`${point.label}: ${numberFormatter.format(value)}`}
            />
          );
        })}
      </div>
      <div className="mt-2 flex justify-between font-mono text-[8px] uppercase tracking-[0.08em] text-white/20">
        <span>{points[0]?.label}</span>
        <span>{points.at(-1)?.label}</span>
      </div>
    </article>
  );
}

function BounceRateTrend({ points }: { points: SeoTrendPoint[] }) {
  const sessions = points.reduce(
    (total, point) => total + point.engagementMeasuredSessions,
    0,
  );
  const engagedSessions = points.reduce(
    (total, point) => total + point.engagedSessions,
    0,
  );
  const bounceRate =
    sessions > 0
      ? Math.max(0, Math.min(1, 1 - engagedSessions / sessions))
      : null;

  return (
    <article className="rounded-2xl border border-white/[0.07] bg-black/10 p-4">
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-xs font-medium text-white/50">Organic bounce</p>
        <p className="font-mono text-sm tabular-nums text-white/75">
          {bounceRate === null ? "—" : percentFormatter.format(bounceRate)}
        </p>
      </div>
      <div
        role="img"
        aria-label="Organic bounce rate by week for the last 12 weeks"
        className="mt-5 flex h-20 items-end gap-1"
      >
        {points.map((point) => {
          const height =
            point.bounceRate === null
              ? 2
              : Math.max(7, point.bounceRate * 100);
          return (
            <div
              key={point.startDate}
              className="min-w-0 flex-1 rounded-t-sm bg-amber-300/70"
              style={{ height: `${height}%` }}
              title={`${point.label}: ${point.bounceRate === null ? "No sessions" : percentFormatter.format(point.bounceRate)}`}
            />
          );
        })}
      </div>
      <div className="mt-2 flex justify-between font-mono text-[8px] uppercase tracking-[0.08em] text-white/20">
        <span>{points[0]?.label}</span>
        <span>{points.at(-1)?.label}</span>
      </div>
    </article>
  );
}

export function SeoTrendChart({ points }: { points: SeoTrendPoint[] }) {
  return (
    <section className="mt-8 rounded-[1.75rem] border border-white/10 bg-white/[0.035] p-5 sm:p-6">
      <div>
        <p className="font-mono text-[8px] uppercase tracking-[0.15em] text-white/30">
          12-week movement
        </p>
        <h2 className="mt-2 text-xl font-semibold tracking-[-0.035em]">
          Visibility to outcome
        </h2>
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <MetricTrend
          label="Impressions"
          metric="impressions"
          points={points}
          color="bg-blue/70"
        />
        <MetricTrend
          label="Google clicks"
          metric="clicks"
          points={points}
          color="bg-coral/80"
        />
        <MetricTrend
          label="Organic sessions"
          metric="organicSessions"
          points={points}
          color="bg-violet-300/70"
        />
        <MetricTrend
          label="PDF downloads"
          metric="downloads"
          points={points}
          color="bg-emerald-300/70"
        />
        <BounceRateTrend points={points} />
      </div>
    </section>
  );
}
