"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import type {
  KeywordDataState,
  KeywordProgressStage,
  KeywordTargetRow,
  TargetPageIndexing,
} from "@/lib/keyword-targets";

type KeywordTableProps = {
  rows: KeywordTargetRow[];
  targetOrigin: string;
};

type SortKey =
  | "keyword"
  | "priority"
  | "page"
  | "stage"
  | "indexing"
  | "position"
  | "change7d"
  | "impressions28d"
  | "clicks28d"
  | "organicSessions28d"
  | "keyEvents28d"
  | "volume"
  | "difficulty"
  | "trafficPotential"
  | "dataState";

type SortDirection = "asc" | "desc";

type SortState = {
  key: SortKey;
  direction: SortDirection;
};

const numberFormatter = new Intl.NumberFormat("en-US");

const pageTypeLabels: Record<string, string> = {
  canonical_hymn: "Hymn page",
  clef_preset: "Clef preset",
  exact_key_preset: "Key preset",
  generic_tool: "Tool page",
  hymn_collection_hub: "Collection hub",
  instrumentalist_hub: "Instrument hub",
  instrument_preset: "Instrument preset",
};

const dataStateOrder: Record<KeywordDataState, number> = {
  complete: 0,
  partial: 1,
  unresearched: 2,
};

const progressStageOrder: Record<KeywordProgressStage, number> = {
  planned: 0,
  live: 1,
  indexed: 2,
  visible: 3,
  top20: 4,
  page1: 5,
  top3: 6,
};

const defaultSortDirections: Record<SortKey, SortDirection> = {
  keyword: "asc",
  priority: "asc",
  page: "asc",
  stage: "desc",
  indexing: "asc",
  position: "asc",
  change7d: "desc",
  impressions28d: "desc",
  clicks28d: "desc",
  organicSessions28d: "desc",
  keyEvents28d: "desc",
  volume: "desc",
  difficulty: "desc",
  trafficPotential: "desc",
  dataState: "asc",
};

function ahrefsKeywordUrl(keyword: string): string {
  return `https://app.ahrefs.com/keywords-explorer/google/us/overview?keyword=${encodeURIComponent(keyword)}`;
}

function ahrefsPageUrl(targetOrigin: string, targetPath: string): string {
  const target = new URL(targetPath, targetOrigin).toString();
  return `https://app.ahrefs.com/site-explorer/overview/v2/exact/live?target=${encodeURIComponent(target)}`;
}

function formatMetric(value: number | null): string {
  return value === null ? "—" : numberFormatter.format(value);
}

function formatCheckedAt(value: string | null): string {
  if (!value) return "Not checked";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

function indexingSortValue(indexing: TargetPageIndexing): number {
  const verdict = indexing.verdict?.toUpperCase();
  if (verdict === "PASS") return 0;
  if (indexing.checkedAt && verdict === "FAIL") return 1;
  if (indexing.checkedAt) return 2;
  return 3;
}

function IndexingBadge({ indexing }: { indexing: TargetPageIndexing }) {
  const verdict = indexing.verdict?.toUpperCase();
  const label =
    verdict === "PASS"
      ? "Indexed"
      : verdict === "FAIL"
        ? "Not indexed"
        : indexing.checkedAt
          ? "Needs review"
          : "Not checked";
  const classes =
    verdict === "PASS"
      ? "border-emerald-300/15 bg-emerald-300/10 text-emerald-200"
      : verdict === "FAIL"
        ? "border-amber-300/15 bg-amber-300/10 text-amber-200"
        : indexing.checkedAt
          ? "border-violet-300/15 bg-violet-300/10 text-violet-200"
          : "border-white/10 bg-white/[0.035] text-white/35";

  return (
    <span
      className={`inline-flex rounded-full border px-2 py-1 font-mono text-[8px] uppercase tracking-[0.12em] ${classes}`}
    >
      {label}
    </span>
  );
}

function SeoCopyValue({
  label,
  value,
}: {
  label: string;
  value: string | null;
}) {
  return (
    <div className="grid grid-cols-[72px_minmax(0,1fr)] gap-2">
      <dt className="font-mono text-[8px] uppercase tracking-[0.11em] text-white/25">
        {label}
      </dt>
      <dd
        className={`line-clamp-2 text-[10px] leading-4 ${
          value ? "text-white/50" : "italic text-white/20"
        }`}
        title={value ?? undefined}
      >
        {value ?? "Not captured"}
      </dd>
    </div>
  );
}

function compareNullableNumbers(
  left: number | null,
  right: number | null,
  direction: SortDirection,
): number {
  if (left === null && right === null) return 0;
  if (left === null) return 1;
  if (right === null) return -1;
  return direction === "asc" ? left - right : right - left;
}

function SortableHeader({
  align = "left",
  column,
  label,
  onSort,
  sort,
}: {
  align?: "left" | "right";
  column: SortKey;
  label: string;
  onSort: (column: SortKey) => void;
  sort: SortState;
}) {
  const isActive = sort.key === column;
  const ariaSort = isActive
    ? sort.direction === "asc"
      ? "ascending"
      : "descending"
    : "none";

  return (
    <th
      aria-sort={ariaSort}
      className={`px-4 py-3.5 font-medium ${align === "right" ? "text-right" : "text-left"}`}
    >
      <button
        type="button"
        onClick={() => onSort(column)}
        className={`group inline-flex w-full items-center gap-1.5 rounded-md outline-none transition hover:text-white/65 focus-visible:ring-2 focus-visible:ring-coral ${align === "right" ? "justify-end" : "justify-start"}`}
      >
        {label}
        <span
          aria-hidden="true"
          className={isActive ? "text-coral" : "text-white/20"}
        >
          {isActive ? (sort.direction === "asc" ? "↑" : "↓") : "↕"}
        </span>
      </button>
    </th>
  );
}

function DataBadge({ state }: { state: KeywordDataState }) {
  const labels: Record<KeywordDataState, string> = {
    complete: "Complete",
    partial: "Partial",
    unresearched: "Needed",
  };
  const classes: Record<KeywordDataState, string> = {
    complete: "border-emerald-300/15 bg-emerald-300/10 text-emerald-200",
    partial: "border-amber-300/15 bg-amber-300/10 text-amber-200",
    unresearched: "border-white/10 bg-white/[0.035] text-white/35",
  };

  return (
    <span
      className={`inline-flex rounded-full border px-2 py-1 font-mono text-[8px] uppercase tracking-[0.12em] ${classes[state]}`}
    >
      {labels[state]}
    </span>
  );
}

function ProgressBadge({ stage }: { stage: KeywordProgressStage }) {
  const labels: Record<KeywordProgressStage, string> = {
    planned: "Planned",
    live: "Live",
    indexed: "Indexed",
    visible: "Visible",
    top20: "Top 20",
    page1: "Page 1",
    top3: "Top 3",
  };
  const classes: Record<KeywordProgressStage, string> = {
    planned: "border-white/10 bg-white/[0.035] text-white/35",
    live: "border-blue/15 bg-blue/10 text-[#9fd2e8]",
    indexed: "border-violet-300/15 bg-violet-300/10 text-violet-200",
    visible: "border-cyan-300/15 bg-cyan-300/10 text-cyan-200",
    top20: "border-amber-300/15 bg-amber-300/10 text-amber-200",
    page1: "border-emerald-300/15 bg-emerald-300/10 text-emerald-200",
    top3: "border-coral/20 bg-coral/12 text-[#ffad9c]",
  };
  return (
    <span
      className={`inline-flex rounded-full border px-2 py-1 font-mono text-[8px] uppercase tracking-[0.12em] ${classes[stage]}`}
    >
      {labels[stage]}
    </span>
  );
}

export function KeywordTable({ rows, targetOrigin }: KeywordTableProps) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [priority, setPriority] = useState("all");
  const [dataState, setDataState] = useState("all");
  const [indexingState, setIndexingState] = useState("all");
  const [checkStatus, setCheckStatus] = useState<
    "idle" | "running" | "success" | "error"
  >("idle");
  const [checkMessage, setCheckMessage] = useState<string | null>(null);
  const [sort, setSort] = useState<SortState>({
    key: "dataState",
    direction: "asc",
  });

  const handleSort = (column: SortKey) => {
    setSort((current) =>
      current.key === column
        ? {
            key: column,
            direction: current.direction === "asc" ? "desc" : "asc",
          }
        : { key: column, direction: defaultSortDirections[column] },
    );
  };

  const keywordOccurrences = useMemo(() => {
    const counts = new Map<string, number>();
    for (const row of rows) {
      counts.set(row.keyword, (counts.get(row.keyword) ?? 0) + 1);
    }
    return counts;
  }, [rows]);

  const indexingSummary = useMemo(() => {
    const pages = new Map(
      rows.map((row) => [row.targetPath, row.indexing] as const),
    );
    const values = [...pages.values()];
    return {
      total: pages.size,
      indexed: values.filter(
        (indexing) => indexing.verdict?.toUpperCase() === "PASS",
      ).length,
      notIndexed: values.filter(
        (indexing) =>
          indexing.checkedAt &&
          indexing.verdict?.toUpperCase() !== "PASS",
      ).length,
      unchecked: values.filter((indexing) => !indexing.checkedAt).length,
    };
  }, [rows]);

  const handleCheckAllPages = async () => {
    setCheckStatus("running");
    setCheckMessage(null);
    try {
      const response = await fetch("/api/admin/seo/indexing/check", {
        method: "POST",
      });
      const payload = (await response.json()) as {
        error?: string;
        message?: string;
        recordsWritten?: number;
      };
      if (!response.ok) {
        throw new Error(
          payload.error ?? payload.message ?? "Indexing check failed.",
        );
      }
      setCheckStatus("success");
      setCheckMessage(
        payload.message ??
          `Checked ${payload.recordsWritten ?? indexingSummary.total} pages.`,
      );
      router.refresh();
    } catch (error) {
      setCheckStatus("error");
      setCheckMessage(
        error instanceof Error ? error.message : "Indexing check failed.",
      );
    }
  };

  const visibleRows = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    const filtered = rows.filter((row) => {
      const matchesQuery =
        !normalizedQuery ||
        row.keyword.toLowerCase().includes(normalizedQuery) ||
        row.targetPath.toLowerCase().includes(normalizedQuery) ||
        row.pageType.toLowerCase().includes(normalizedQuery) ||
        [
          row.seo.title,
          row.seo.metaDescription,
          row.seo.h1,
          row.seo.firstParagraph,
        ].some((value) => value?.toLowerCase().includes(normalizedQuery));
      const matchesPriority =
        priority === "all" || row.priority === Number(priority);
      const matchesData = dataState === "all" || row.dataState === dataState;
      const verdict = row.indexing.verdict?.toUpperCase();
      const matchesIndexing =
        indexingState === "all" ||
        (indexingState === "indexed" && verdict === "PASS") ||
        (indexingState === "not-indexed" &&
          row.indexing.checkedAt !== null &&
          verdict !== "PASS") ||
        (indexingState === "unchecked" && row.indexing.checkedAt === null);
      return matchesQuery && matchesPriority && matchesData && matchesIndexing;
    });

    return filtered.toSorted((left, right) => {
      const directionMultiplier = sort.direction === "asc" ? 1 : -1;
      let comparison = 0;

      if (sort.key === "keyword") {
        comparison = left.keyword.localeCompare(right.keyword);
      } else if (sort.key === "priority") {
        comparison = left.priority - right.priority;
      } else if (sort.key === "page") {
        comparison = left.targetPath.localeCompare(right.targetPath);
      } else if (sort.key === "stage") {
        comparison =
          progressStageOrder[left.progress?.stage ?? "planned"] -
          progressStageOrder[right.progress?.stage ?? "planned"];
      } else if (sort.key === "indexing") {
        comparison =
          indexingSortValue(left.indexing) - indexingSortValue(right.indexing);
      } else if (sort.key === "position") {
        comparison = compareNullableNumbers(
          left.progress?.currentPosition ?? null,
          right.progress?.currentPosition ?? null,
          sort.direction,
        );
      } else if (sort.key === "change7d") {
        comparison = compareNullableNumbers(
          left.progress?.positionChange7d ?? null,
          right.progress?.positionChange7d ?? null,
          sort.direction,
        );
      } else if (sort.key === "impressions28d") {
        comparison =
          (left.progress?.impressions28d ?? 0) -
          (right.progress?.impressions28d ?? 0);
      } else if (sort.key === "clicks28d") {
        comparison =
          (left.progress?.clicks28d ?? 0) -
          (right.progress?.clicks28d ?? 0);
      } else if (sort.key === "organicSessions28d") {
        comparison =
          (left.progress?.organicSessions28d ?? 0) -
          (right.progress?.organicSessions28d ?? 0);
      } else if (sort.key === "keyEvents28d") {
        comparison =
          (left.progress?.keyEvents28d ?? 0) -
          (right.progress?.keyEvents28d ?? 0);
      } else if (sort.key === "volume") {
        comparison = compareNullableNumbers(
          left.volume,
          right.volume,
          sort.direction,
        );
      } else if (sort.key === "difficulty") {
        comparison = compareNullableNumbers(
          left.difficulty,
          right.difficulty,
          sort.direction,
        );
      } else if (sort.key === "trafficPotential") {
        comparison = compareNullableNumbers(
          left.trafficPotential,
          right.trafficPotential,
          sort.direction,
        );
      } else {
        comparison =
          dataStateOrder[left.dataState] - dataStateOrder[right.dataState];
      }

      if (
        comparison !== 0 &&
        ![
          "volume",
          "difficulty",
          "trafficPotential",
          "position",
          "change7d",
        ].includes(sort.key)
      ) {
        return comparison * directionMultiplier;
      }
      if (comparison !== 0) return comparison;

      return (
        dataStateOrder[left.dataState] - dataStateOrder[right.dataState] ||
        left.priority - right.priority ||
        Number(left.role === "Supporting") -
          Number(right.role === "Supporting") ||
        left.keyword.localeCompare(right.keyword)
      );
    });
  }, [dataState, indexingState, priority, query, rows, sort]);

  const filtersActive =
    query.trim() !== "" ||
    priority !== "all" ||
    dataState !== "all" ||
    indexingState !== "all";

  return (
    <div className="overflow-hidden rounded-[1.75rem] border border-white/10 bg-white/[0.035] shadow-[0_20px_70px_rgba(0,0,0,0.16)]">
      <div className="border-b border-white/10 p-5 sm:p-6">
        <div className="mb-6 flex flex-col gap-4 rounded-2xl border border-blue/15 bg-blue/[0.055] p-4 sm:p-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-semibold text-white/80">
                Google indexing tools
              </p>
              <span className="rounded-full border border-white/10 bg-black/10 px-2 py-1 font-mono text-[8px] uppercase tracking-[0.12em] text-white/40">
                {indexingSummary.total} unique pages
              </span>
            </div>
            <p className="mt-1.5 max-w-3xl text-xs leading-5 text-white/40">
              Check every target with Google&apos;s URL Inspection API. Then use
              a page&apos;s Request indexing button to open its preloaded Search
              Console inspection in a new tab.
            </p>
            <div className="mt-3 flex flex-wrap gap-2 font-mono text-[9px] tabular-nums">
              <span className="text-emerald-200/80">
                {indexingSummary.indexed} indexed
              </span>
              <span className="text-amber-200/80">
                {indexingSummary.notIndexed} not indexed
              </span>
              <span className="text-white/30">
                {indexingSummary.unchecked} not checked
              </span>
            </div>
            {checkMessage ? (
              <p
                aria-live="polite"
                className={`mt-2 text-xs ${
                  checkStatus === "error"
                    ? "text-rose-200/80"
                    : "text-emerald-200/75"
                }`}
              >
                {checkMessage}
              </p>
            ) : null}
          </div>
          <div className="shrink-0">
            <button
              type="button"
              onClick={handleCheckAllPages}
              disabled={checkStatus === "running"}
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-blue/25 bg-blue/15 px-4 text-xs font-semibold text-[#bfe8f7] transition hover:border-blue/40 hover:bg-blue/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral disabled:cursor-wait disabled:opacity-55"
            >
              {checkStatus === "running"
                ? "Checking all pages…"
                : `Check all ${indexingSummary.total} pages`}
              {checkStatus !== "running" ? (
                <span aria-hidden="true">↻</span>
              ) : null}
            </button>
            <p className="mt-2 text-center font-mono text-[8px] uppercase tracking-[0.1em] text-white/25">
              API allowance: 2,000 / day
            </p>
          </div>
        </div>

        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-semibold tracking-[-0.035em]">
                Keyword map
              </h2>
              <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 font-mono text-[8px] uppercase tracking-[0.14em] text-white/45">
                {visibleRows.length} of {rows.length}
              </span>
            </div>
            <p className="mt-1 text-sm text-white/40">
              Daily search progress plus the original research baseline. Click
              any heading to sort ascending or descending.
            </p>
          </div>

          <div className="grid gap-2 sm:grid-cols-3 xl:flex xl:items-center">
            <label className="relative sm:col-span-3 xl:w-72">
              <span className="sr-only">Search keywords and target pages</span>
              <svg
                viewBox="0 0 24 24"
                className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-white/30"
                fill="none"
                aria-hidden="true"
              >
                <circle cx="11" cy="11" r="6.5" stroke="currentColor" />
                <path d="m16 16 4 4" stroke="currentColor" strokeLinecap="round" />
              </svg>
              <input
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search keyword or page"
                className="h-10 w-full rounded-xl border border-white/10 bg-[#0c1217] pl-10 pr-3 text-sm text-white outline-none placeholder:text-white/25 focus:border-coral/60 focus:ring-2 focus:ring-coral/15"
              />
            </label>

            <label>
              <span className="sr-only">Filter by priority</span>
              <select
                value={priority}
                onChange={(event) => setPriority(event.target.value)}
                className="h-10 w-full rounded-xl border border-white/10 bg-[#0c1217] px-3 text-xs text-white/70 outline-none focus:border-coral/60 focus:ring-2 focus:ring-coral/15 xl:w-auto"
              >
                <option value="all">All priorities</option>
                <option value="0">Priority 0</option>
                <option value="1">Priority 1</option>
              </select>
            </label>

            <label>
              <span className="sr-only">Filter by metric coverage</span>
              <select
                value={dataState}
                onChange={(event) => setDataState(event.target.value)}
                className="h-10 w-full rounded-xl border border-white/10 bg-[#0c1217] px-3 text-xs text-white/70 outline-none focus:border-coral/60 focus:ring-2 focus:ring-coral/15 xl:w-auto"
              >
                <option value="all">All metric states</option>
                <option value="complete">Complete</option>
                <option value="partial">Partial</option>
                <option value="unresearched">Needed</option>
              </select>
            </label>

            <label>
              <span className="sr-only">Filter by indexing status</span>
              <select
                value={indexingState}
                onChange={(event) => setIndexingState(event.target.value)}
                className="h-10 w-full rounded-xl border border-white/10 bg-[#0c1217] px-3 text-xs text-white/70 outline-none focus:border-coral/60 focus:ring-2 focus:ring-coral/15 xl:w-auto"
              >
                <option value="all">All indexing states</option>
                <option value="indexed">Indexed</option>
                <option value="not-indexed">Not indexed</option>
                <option value="unchecked">Not checked</option>
              </select>
            </label>

          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[2380px] border-collapse text-left">
          <thead>
            <tr className="border-b border-white/10 bg-black/10 font-mono text-[8px] uppercase tracking-[0.14em] text-white/30">
              <SortableHeader
                column="keyword"
                label="Keyword"
                onSort={handleSort}
                sort={sort}
              />
              <SortableHeader
                column="priority"
                label="Priority"
                onSort={handleSort}
                sort={sort}
              />
              <SortableHeader
                column="page"
                label="Target page"
                onSort={handleSort}
                sort={sort}
              />
              <SortableHeader
                column="stage"
                label="Progress"
                onSort={handleSort}
                sort={sort}
              />
              <SortableHeader
                column="indexing"
                label="Google index"
                onSort={handleSort}
                sort={sort}
              />
              <SortableHeader
                align="right"
                column="position"
                label="Position"
                onSort={handleSort}
                sort={sort}
              />
              <SortableHeader
                align="right"
                column="change7d"
                label="Δ 7d"
                onSort={handleSort}
                sort={sort}
              />
              <SortableHeader
                align="right"
                column="impressions28d"
                label="Impr. 28d"
                onSort={handleSort}
                sort={sort}
              />
              <SortableHeader
                align="right"
                column="clicks28d"
                label="Clicks 28d"
                onSort={handleSort}
                sort={sort}
              />
              <SortableHeader
                align="right"
                column="organicSessions28d"
                label="Organic sessions"
                onSort={handleSort}
                sort={sort}
              />
              <SortableHeader
                align="right"
                column="keyEvents28d"
                label="Key events"
                onSort={handleSort}
                sort={sort}
              />
              <SortableHeader
                align="right"
                column="volume"
                label="Volume"
                onSort={handleSort}
                sort={sort}
              />
              <SortableHeader
                align="right"
                column="difficulty"
                label="KD"
                onSort={handleSort}
                sort={sort}
              />
              <SortableHeader
                align="right"
                column="trafficPotential"
                label="Traffic potential"
                onSort={handleSort}
                sort={sort}
              />
              <SortableHeader
                column="dataState"
                label="Metrics"
                onSort={handleSort}
                sort={sort}
              />
              <th className="px-6 py-3.5 text-right font-medium">Open</th>
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((row) => {
              const targetCount = keywordOccurrences.get(row.keyword) ?? 1;
              const progress = row.progress;

              return (
                <tr
                  key={row.id}
                  className="border-b border-white/[0.065] text-sm transition-colors last:border-0 hover:bg-white/[0.035]"
                >
                  <td className="max-w-[340px] px-6 py-4 align-top">
                    <p className="font-medium leading-5 tracking-[-0.015em] text-white/90">
                      {row.keyword}
                    </p>
                    <div className="mt-1.5 flex items-center gap-2 font-mono text-[8px] uppercase tracking-[0.12em]">
                      <span
                        className={
                          row.role === "Primary"
                            ? "text-coral"
                            : "text-white/30"
                        }
                      >
                        {row.role}
                      </span>
                      {targetCount > 1 ? (
                        <span className="text-amber-200/70">
                          {targetCount} target pages
                        </span>
                      ) : null}
                    </div>
                  </td>
                  <td className="px-4 py-4 align-top">
                    <span
                      className={
                        row.priority === 0
                          ? "inline-flex rounded-full bg-coral/12 px-2 py-1 font-mono text-[9px] font-semibold text-[#ffad9c]"
                          : "inline-flex rounded-full bg-blue/15 px-2 py-1 font-mono text-[9px] font-semibold text-[#9fd2e8]"
                      }
                    >
                      P{row.priority}
                    </span>
                  </td>
                  <td className="w-[480px] max-w-[480px] px-4 py-4 align-top">
                    <Link
                      href={row.targetPath}
                      target="_blank"
                      className="block truncate font-mono text-[10px] text-white/65 underline decoration-white/10 underline-offset-4 transition hover:text-white hover:decoration-white/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral"
                    >
                      {row.targetPath}
                    </Link>
                    <p className="mt-1.5 text-[10px] text-white/28">
                      {pageTypeLabels[row.pageType] ?? row.pageType}
                    </p>
                    <dl className="mt-3 space-y-1.5 rounded-xl border border-white/[0.065] bg-black/10 p-3">
                      <SeoCopyValue label="Title" value={row.seo.title} />
                      <SeoCopyValue
                        label="Meta desc."
                        value={row.seo.metaDescription}
                      />
                      <SeoCopyValue label="H1" value={row.seo.h1} />
                      <SeoCopyValue
                        label="First para."
                        value={row.seo.firstParagraph}
                      />
                    </dl>
                  </td>
                  <td className="px-4 py-4 align-top">
                    <ProgressBadge stage={progress?.stage ?? "planned"} />
                    {progress?.rankingUrlMatchesTarget === false ? (
                      <p className="mt-1.5 font-mono text-[8px] uppercase tracking-[0.1em] text-amber-200/75">
                        Other URL ranks
                      </p>
                    ) : null}
                  </td>
                  <td className="w-[230px] max-w-[230px] px-4 py-4 align-top">
                    <IndexingBadge indexing={row.indexing} />
                    <p
                      className="mt-2 line-clamp-2 text-[10px] leading-4 text-white/40"
                      title={row.indexing.coverageState ?? undefined}
                    >
                      {row.indexing.coverageState ?? "No inspection result yet"}
                    </p>
                    <p className="mt-1 font-mono text-[8px] uppercase tracking-[0.1em] text-white/25">
                      {formatCheckedAt(row.indexing.checkedAt)}
                    </p>
                    {row.indexing.inspectionResultLink ? (
                      <a
                        href={row.indexing.inspectionResultLink}
                        target="_blank"
                        rel="noreferrer"
                        className="mt-3 inline-flex rounded-lg border border-coral/20 bg-coral/10 px-2.5 py-1.5 text-[10px] font-semibold text-[#ffad9c] transition hover:border-coral/35 hover:bg-coral/15 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral"
                        title={`Open ${row.targetPath} in Google Search Console to request indexing`}
                      >
                        Request indexing ↗
                      </a>
                    ) : (
                      <span className="mt-3 inline-flex rounded-lg border border-white/[0.07] px-2.5 py-1.5 text-[10px] text-white/25">
                        Check status first
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-4 text-right align-top font-mono text-xs tabular-nums text-white/75">
                    {progress?.currentPosition === null ||
                    progress?.currentPosition === undefined
                      ? "—"
                      : progress.currentPosition.toFixed(1)}
                  </td>
                  <td className="px-4 py-4 text-right align-top font-mono text-xs tabular-nums">
                    {progress?.positionChange7d === null ||
                    progress?.positionChange7d === undefined ? (
                      <span className="text-white/25">—</span>
                    ) : (
                      <span
                        className={
                          progress.positionChange7d > 0
                            ? "text-emerald-200"
                            : progress.positionChange7d < 0
                              ? "text-rose-200"
                              : "text-white/40"
                        }
                      >
                        {progress.positionChange7d > 0 ? "+" : ""}
                        {progress.positionChange7d.toFixed(1)}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-4 text-right align-top font-mono text-xs tabular-nums text-white/70">
                    {numberFormatter.format(progress?.impressions28d ?? 0)}
                  </td>
                  <td className="px-4 py-4 text-right align-top font-mono text-xs tabular-nums text-white/70">
                    {numberFormatter.format(progress?.clicks28d ?? 0)}
                  </td>
                  <td className="px-4 py-4 text-right align-top font-mono text-xs tabular-nums text-white/70">
                    {numberFormatter.format(progress?.organicSessions28d ?? 0)}
                  </td>
                  <td className="px-4 py-4 text-right align-top font-mono text-xs tabular-nums text-white/70">
                    {numberFormatter.format(progress?.keyEvents28d ?? 0)}
                  </td>
                  <td className="px-4 py-4 text-right font-mono text-xs tabular-nums text-white/70">
                    {formatMetric(row.volume)}
                  </td>
                  <td className="px-4 py-4 text-right font-mono text-xs tabular-nums">
                    <span
                      className={
                        row.difficulty === null
                          ? "text-white/25"
                          : row.difficulty <= 3
                            ? "text-emerald-200"
                            : "text-white/70"
                      }
                    >
                      {formatMetric(row.difficulty)}
                    </span>
                  </td>
                  <td className="px-4 py-4 text-right font-mono text-xs tabular-nums text-white/70">
                    {formatMetric(row.trafficPotential)}
                  </td>
                  <td className="px-4 py-4">
                    <DataBadge state={row.dataState} />
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <a
                        href={ahrefsKeywordUrl(row.keyword)}
                        target="_blank"
                        rel="noreferrer"
                        className="rounded-lg border border-white/10 px-2.5 py-1.5 text-[10px] font-medium text-white/55 transition hover:border-white/20 hover:bg-white/5 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral"
                        title={`Open “${row.keyword}” in Ahrefs Keywords Explorer`}
                      >
                        Keyword ↗
                      </a>
                      <a
                        href={ahrefsPageUrl(targetOrigin, row.targetPath)}
                        target="_blank"
                        rel="noreferrer"
                        className="rounded-lg border border-white/10 px-2.5 py-1.5 text-[10px] font-medium text-white/55 transition hover:border-white/20 hover:bg-white/5 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral"
                        title={`Open ${row.targetPath} in Ahrefs Site Explorer`}
                      >
                        Page ↗
                      </a>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {visibleRows.length === 0 ? (
        <div className="border-t border-white/10 px-6 py-14 text-center">
          <p className="text-sm font-medium text-white/65">No keywords found.</p>
          <p className="mt-1 text-xs text-white/35">
            Try a broader search or clear the active filters.
          </p>
          {filtersActive ? (
            <button
              type="button"
              onClick={() => {
                setQuery("");
                setPriority("all");
                setDataState("all");
                setIndexingState("all");
              }}
              className="mt-4 rounded-full border border-white/10 px-4 py-2 text-xs font-medium text-white/60 transition hover:bg-white/5 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral"
            >
              Clear filters
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
