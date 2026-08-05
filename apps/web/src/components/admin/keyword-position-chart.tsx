import type { KeywordHistoryPoint } from "@/lib/seo-tracking.server";

const sourceStyles = {
  google_search_console: {
    color: "#ff8f78",
    label: "Search Console",
  },
  ahrefs: {
    color: "#8bc8df",
    label: "Ahrefs",
  },
  manual: {
    color: "#fde68a",
    label: "Manual",
  },
} as const;

function dateTimestamp(value: string): number {
  return new Date(`${value}T00:00:00Z`).getTime();
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}

function formatPosition(value: number): string {
  return Number.isInteger(value) ? value.toString() : value.toFixed(1);
}

export function KeywordPositionChart({
  points,
}: {
  points: KeywordHistoryPoint[];
}) {
  const measuredPoints = points.filter(
    (point): point is KeywordHistoryPoint & { position: number } =>
      point.position !== null,
  );

  if (points.length === 0) {
    return (
      <div className="grid min-h-72 place-items-center rounded-2xl border border-dashed border-white/10 bg-black/10 px-6 text-center">
        <div>
          <p className="text-sm font-medium text-white/60">
            No ranking snapshots yet
          </p>
          <p className="mt-1 max-w-sm text-xs leading-5 text-white/30">
            Position history will appear after Search Console or another rank
            source records this keyword.
          </p>
        </div>
      </div>
    );
  }

  const width = 1000;
  const height = 370;
  const plotLeft = 64;
  const plotRight = 976;
  const plotTop = 28;
  const plotBottom = 306;
  const plotWidth = plotRight - plotLeft;
  const plotHeight = plotBottom - plotTop;
  const timestamps = points.map((point) => dateTimestamp(point.snapshotDate));
  const firstTimestamp = Math.min(...timestamps);
  const lastTimestamp = Math.max(...timestamps);
  const hasDateRange = firstTimestamp !== lastTimestamp;
  const highestMeasuredPosition = Math.max(
    ...measuredPoints.map((point) => point.position),
    10,
  );
  const positionCeiling =
    highestMeasuredPosition <= 10
      ? 10
      : highestMeasuredPosition <= 20
        ? 20
        : Math.ceil(highestMeasuredPosition / 10) * 10;
  const xFor = (date: string) => {
    if (!hasDateRange) return plotLeft + plotWidth / 2;
    return (
      plotLeft +
      ((dateTimestamp(date) - firstTimestamp) /
        (lastTimestamp - firstTimestamp)) *
        plotWidth
    );
  };
  const yFor = (position: number) =>
    plotTop + ((position - 1) / (positionCeiling - 1)) * plotHeight;
  const tickCandidates = [1, 3, 10, 20, 50, 100, positionCeiling];
  const positionTicks = [...new Set(tickCandidates)]
    .filter((tick) => tick <= positionCeiling)
    .toSorted((left, right) => left - right);
  const series = Object.entries(sourceStyles)
    .map(([source, style]) => ({
      source: source as KeywordHistoryPoint["source"],
      style,
      points: measuredPoints.filter((point) => point.source === source),
    }))
    .filter((item) => item.points.length > 0);
  const firstDate = points[0]?.snapshotDate ?? "";
  const lastDate = points.at(-1)?.snapshotDate ?? firstDate;

  return (
    <div>
      <div className="overflow-x-auto rounded-2xl border border-white/[0.07] bg-[#0d1419]">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="block h-auto min-w-[720px] w-full"
          role="img"
          aria-label={`Position history from ${formatDate(firstDate)} to ${formatDate(lastDate)}. Lower position numbers are better.`}
        >
          <rect
            x={plotLeft}
            y={yFor(1)}
            width={plotWidth}
            height={Math.max(yFor(3) - yFor(1), 1)}
            fill="rgba(52, 211, 153, 0.055)"
          />
          <rect
            x={plotLeft}
            y={yFor(3)}
            width={plotWidth}
            height={Math.max(yFor(10) - yFor(3), 1)}
            fill="rgba(139, 200, 223, 0.035)"
          />

          {positionTicks.map((tick) => (
            <g key={tick}>
              <line
                x1={plotLeft}
                x2={plotRight}
                y1={yFor(tick)}
                y2={yFor(tick)}
                stroke="rgba(255,255,255,0.08)"
                strokeDasharray={tick === 10 ? "5 5" : undefined}
              />
              <text
                x={plotLeft - 14}
                y={yFor(tick) + 4}
                textAnchor="end"
                fill="rgba(255,255,255,0.32)"
                fontSize="11"
                fontFamily="var(--font-geist-mono), monospace"
              >
                {tick}
              </text>
            </g>
          ))}

          <text
            x={plotLeft}
            y={18}
            fill="rgba(255,255,255,0.27)"
            fontSize="10"
            fontFamily="var(--font-geist-mono), monospace"
            letterSpacing="1.2"
          >
            BETTER
          </text>
          <text
            x={plotRight}
            y={yFor(3) - 7}
            textAnchor="end"
            fill="rgba(110,231,183,0.55)"
            fontSize="9"
            fontFamily="var(--font-geist-mono), monospace"
            letterSpacing="1"
          >
            TOP 3
          </text>
          <text
            x={plotRight}
            y={yFor(10) - 7}
            textAnchor="end"
            fill="rgba(139,200,223,0.5)"
            fontSize="9"
            fontFamily="var(--font-geist-mono), monospace"
            letterSpacing="1"
          >
            PAGE 1
          </text>

          {points.map((point, index) => (
            <line
              key={`${point.snapshotDate}-${point.source}-${index}`}
              x1={xFor(point.snapshotDate)}
              x2={xFor(point.snapshotDate)}
              y1={plotBottom + 6}
              y2={plotBottom + 12}
              stroke="rgba(255,255,255,0.16)"
            />
          ))}

          {series.map(({ points: sourcePoints, source, style }) => {
            const path = sourcePoints
              .map(
                (point, index) =>
                  `${index === 0 ? "M" : "L"} ${xFor(point.snapshotDate).toFixed(2)} ${yFor(point.position).toFixed(2)}`,
              )
              .join(" ");
            return (
              <g key={source}>
                <path
                  d={path}
                  fill="none"
                  stroke={style.color}
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                {sourcePoints.map((point) => (
                  <g
                    key={`${source}-${point.snapshotDate}-${point.country}-${point.device}`}
                  >
                    <circle
                      cx={xFor(point.snapshotDate)}
                      cy={yFor(point.position)}
                      r="8"
                      fill="#0d1419"
                      stroke={style.color}
                      strokeWidth="3"
                    >
                      <title>
                        {`${formatDate(point.snapshotDate)}: position ${formatPosition(point.position)}, ${point.impressions} impressions, ${point.clicks} clicks`}
                      </title>
                    </circle>
                    <text
                      x={xFor(point.snapshotDate)}
                      y={yFor(point.position) - 14}
                      textAnchor="middle"
                      fill={style.color}
                      fontSize="11"
                      fontWeight="600"
                      fontFamily="var(--font-geist-mono), monospace"
                    >
                      {formatPosition(point.position)}
                    </text>
                  </g>
                ))}
              </g>
            );
          })}

          <line
            x1={plotLeft}
            x2={plotRight}
            y1={plotBottom}
            y2={plotBottom}
            stroke="rgba(255,255,255,0.12)"
          />
          <text
            x={plotLeft}
            y={342}
            fill="rgba(255,255,255,0.32)"
            fontSize="11"
            fontFamily="var(--font-geist-mono), monospace"
          >
            {formatDate(firstDate)}
          </text>
          <text
            x={plotRight}
            y={342}
            textAnchor="end"
            fill="rgba(255,255,255,0.32)"
            fontSize="11"
            fontFamily="var(--font-geist-mono), monospace"
          >
            {formatDate(lastDate)}
          </text>
        </svg>
      </div>

      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-4">
          {series.map(({ source, style }) => (
            <span
              key={source}
              className="inline-flex items-center gap-2 text-[10px] text-white/40"
            >
              <span
                className="size-2 rounded-full"
                style={{ backgroundColor: style.color }}
                aria-hidden="true"
              />
              {style.label}
            </span>
          ))}
        </div>
        <p className="font-mono text-[9px] uppercase tracking-[0.1em] text-white/25">
          {measuredPoints.length} measured · {points.length} snapshots
        </p>
      </div>
    </div>
  );
}
