"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type {
  KeywordDataState,
  KeywordTargetRow,
} from "@/lib/keyword-targets";

type KeywordTableProps = {
  rows: KeywordTargetRow[];
  targetOrigin: string;
};

type SortOption = "keyword" | "page" | "priority" | "volume";

const numberFormatter = new Intl.NumberFormat("en-US");

const pageTypeLabels: Record<string, string> = {
  canonical_hymn: "Hymn page",
  exact_key_preset: "Key preset",
  generic_tool: "Tool page",
  hymn_collection_hub: "Collection hub",
  instrumentalist_hub: "Instrument hub",
  instrument_preset: "Instrument preset",
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

export function KeywordTable({ rows, targetOrigin }: KeywordTableProps) {
  const [query, setQuery] = useState("");
  const [priority, setPriority] = useState("all");
  const [dataState, setDataState] = useState("all");
  const [sort, setSort] = useState<SortOption>("priority");

  const keywordOccurrences = useMemo(() => {
    const counts = new Map<string, number>();
    for (const row of rows) {
      counts.set(row.keyword, (counts.get(row.keyword) ?? 0) + 1);
    }
    return counts;
  }, [rows]);

  const visibleRows = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    const filtered = rows.filter((row) => {
      const matchesQuery =
        !normalizedQuery ||
        row.keyword.toLowerCase().includes(normalizedQuery) ||
        row.targetPath.toLowerCase().includes(normalizedQuery) ||
        row.pageType.toLowerCase().includes(normalizedQuery);
      const matchesPriority =
        priority === "all" || row.priority === Number(priority);
      const matchesData = dataState === "all" || row.dataState === dataState;
      return matchesQuery && matchesPriority && matchesData;
    });

    return filtered.toSorted((left, right) => {
      if (sort === "keyword") return left.keyword.localeCompare(right.keyword);
      if (sort === "page") return left.targetPath.localeCompare(right.targetPath);
      if (sort === "volume") {
        return (right.volume ?? -1) - (left.volume ?? -1);
      }

      return (
        left.priority - right.priority ||
        Number(left.role === "Supporting") -
          Number(right.role === "Supporting") ||
        (right.volume ?? -1) - (left.volume ?? -1)
      );
    });
  }, [dataState, priority, query, rows, sort]);

  const filtersActive =
    query.trim() !== "" || priority !== "all" || dataState !== "all";

  return (
    <div className="overflow-hidden rounded-[1.75rem] border border-white/10 bg-white/[0.035] shadow-[0_20px_70px_rgba(0,0,0,0.16)]">
      <div className="border-b border-white/10 p-5 sm:p-6">
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
              One row per keyword-to-page mapping. Missing metrics are queued
              for research.
            </p>
          </div>

          <div className="grid gap-2 sm:grid-cols-2 xl:flex xl:items-center">
            <label className="relative sm:col-span-2 xl:w-72">
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
              <span className="sr-only">Sort keyword rows</span>
              <select
                value={sort}
                onChange={(event) => setSort(event.target.value as SortOption)}
                className="h-10 w-full rounded-xl border border-white/10 bg-[#0c1217] px-3 text-xs text-white/70 outline-none focus:border-coral/60 focus:ring-2 focus:ring-coral/15 xl:w-auto"
              >
                <option value="priority">Sort: Priority</option>
                <option value="volume">Sort: Volume</option>
                <option value="keyword">Sort: Keyword</option>
                <option value="page">Sort: Target page</option>
              </select>
            </label>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[1120px] border-collapse text-left">
          <thead>
            <tr className="border-b border-white/10 bg-black/10 font-mono text-[8px] uppercase tracking-[0.14em] text-white/30">
              <th className="px-6 py-3.5 font-medium">Keyword</th>
              <th className="px-4 py-3.5 font-medium">Priority</th>
              <th className="px-4 py-3.5 font-medium">Target page</th>
              <th className="px-4 py-3.5 text-right font-medium">Volume</th>
              <th className="px-4 py-3.5 text-right font-medium">KD</th>
              <th className="px-4 py-3.5 text-right font-medium">Traffic potential</th>
              <th className="px-4 py-3.5 font-medium">Metrics</th>
              <th className="px-6 py-3.5 text-right font-medium">Open</th>
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((row) => {
              const targetCount = keywordOccurrences.get(row.keyword) ?? 1;

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
                  <td className="max-w-[330px] px-4 py-4 align-top">
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
