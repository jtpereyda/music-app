import keywordResearch from "../../../../docs/2026-07-21-keyword-targeting.json";

type KeywordMetric = {
  us_volume_monthly: number | null;
  kd: number | null;
  traffic_potential: number | null;
};

type KeywordPage = {
  priority: number;
  page_type: string;
  path: string;
  primary_keyword: string;
  supporting_keywords?: string[] | null;
  keyword_metrics: Record<string, KeywordMetric>;
  index_when_launched: boolean;
  title?: string;
  h1?: string;
};

type KeywordResearch = {
  market: string;
  language: string;
  research_date: string;
  pages: KeywordPage[];
};

export type KeywordDataState = "complete" | "partial" | "unresearched";

export type KeywordProgressStage =
  | "planned"
  | "live"
  | "indexed"
  | "visible"
  | "top20"
  | "page1"
  | "top3";

export type KeywordProgress = {
  stage: KeywordProgressStage;
  currentPosition: number | null;
  positionChange7d: number | null;
  positionChange28d: number | null;
  bestPosition: number | null;
  impressions28d: number;
  clicks28d: number;
  ctr28d: number | null;
  organicSessions28d: number;
  keyEvents28d: number;
  rankingUrl: string | null;
  rankingUrlMatchesTarget: boolean | null;
  indexed: boolean | null;
  live: boolean | null;
  lastUpdated: string | null;
};

export type TargetPageSeo = {
  title: string | null;
  metaDescription: string | null;
  h1: string | null;
  firstParagraph: string | null;
  checkedAt: string | null;
};

export type KeywordTargetRow = {
  id: string;
  keyword: string;
  role: "Primary" | "Supporting";
  priority: number;
  pageType: string;
  targetPath: string;
  volume: number | null;
  difficulty: number | null;
  trafficPotential: number | null;
  dataState: KeywordDataState;
  indexWhenLaunched: boolean;
  seo: TargetPageSeo;
  progress?: KeywordProgress;
};

export type KeywordDashboard = {
  rows: KeywordTargetRow[];
  summary: {
    uniqueKeywords: number;
    keywordMappings: number;
    targetPages: number;
    knownMonthlyVolume: number;
    knownTrafficPotential: number;
    measuredKeywords: number;
    measurementCoverage: number;
    duplicateMappings: number;
    priorityZeroPages: number;
    priorityOnePages: number;
  };
  market: string;
  language: string;
  researchDate: string;
};

function getDataState(metric: KeywordMetric | undefined): KeywordDataState {
  if (!metric) return "unresearched";

  const values = [
    metric.us_volume_monthly,
    metric.kd,
    metric.traffic_potential,
  ];
  if (values.every((value) => value !== null)) return "complete";
  return values.some((value) => value !== null) ? "partial" : "unresearched";
}

export function getKeywordDashboard(): KeywordDashboard {
  const research = keywordResearch as unknown as KeywordResearch;
  const metricsByKeyword = new Map<string, KeywordMetric>();

  for (const page of research.pages) {
    for (const [keyword, metric] of Object.entries(page.keyword_metrics)) {
      metricsByKeyword.set(keyword, metric);
    }
  }

  const rows = research.pages.flatMap((page) => {
    const createRow = (
      keyword: string,
      role: KeywordTargetRow["role"],
      index: number,
    ): KeywordTargetRow => {
      const metric = page.keyword_metrics[keyword] ?? metricsByKeyword.get(keyword);

      return {
        id: `${page.path}:${role.toLowerCase()}:${index}:${keyword}`,
        keyword,
        role,
        priority: page.priority,
        pageType: page.page_type,
        targetPath: page.path,
        volume: metric?.us_volume_monthly ?? null,
        difficulty: metric?.kd ?? null,
        trafficPotential: metric?.traffic_potential ?? null,
        dataState: getDataState(metric),
        indexWhenLaunched: page.index_when_launched,
        seo: {
          title: page.title ?? null,
          metaDescription: null,
          h1: page.h1 ?? null,
          firstParagraph: null,
          checkedAt: null,
        },
      };
    };

    return [
      createRow(page.primary_keyword, "Primary", 0),
      ...(page.supporting_keywords ?? []).map((keyword, index) =>
        createRow(keyword, "Supporting", index + 1),
      ),
    ];
  });

  const uniqueKeywords = new Set(rows.map((row) => row.keyword));
  const measuredKeywords = [...uniqueKeywords].filter((keyword) =>
    metricsByKeyword.has(keyword),
  ).length;
  const knownMonthlyVolume = [...metricsByKeyword.values()].reduce(
    (total, metric) => total + (metric.us_volume_monthly ?? 0),
    0,
  );
  const knownTrafficPotential = [...metricsByKeyword.values()].reduce(
    (total, metric) => total + (metric.traffic_potential ?? 0),
    0,
  );

  return {
    rows,
    summary: {
      uniqueKeywords: uniqueKeywords.size,
      keywordMappings: rows.length,
      targetPages: research.pages.length,
      knownMonthlyVolume,
      knownTrafficPotential,
      measuredKeywords,
      measurementCoverage: uniqueKeywords.size
        ? Math.round((measuredKeywords / uniqueKeywords.size) * 100)
        : 0,
      duplicateMappings: rows.length - uniqueKeywords.size,
      priorityZeroPages: research.pages.filter((page) => page.priority === 0)
        .length,
      priorityOnePages: research.pages.filter((page) => page.priority === 1)
        .length,
    },
    market: research.market,
    language: research.language,
    researchDate: research.research_date,
  };
}
