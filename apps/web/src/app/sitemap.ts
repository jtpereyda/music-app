import type { MetadataRoute } from "next";
import {
  curatedPresets,
  priorityHymnSlugs,
} from "@/lib/landing-pages";
import { getSiteUrl } from "@/lib/site";

export default function sitemap(): MetadataRoute.Sitemap {
  const siteUrl = getSiteUrl();
  const sectionPaths = [
    "",
    "/hymns",
    "/hymns/sheet-music-for-instrumentalists",
    "/uses/hymn-transposer",
  ];
  const hymnPaths = priorityHymnSlugs.map((slug) => `/hymns/${slug}`);
  const presetPaths = curatedPresets.map(
    (preset) => `/hymns/${preset.hymnSlug}/${preset.slug}`,
  );

  return [...sectionPaths, ...hymnPaths, ...presetPaths].map(
    (path, index) => ({
      url: new URL(path || "/", siteUrl).toString(),
      changeFrequency: index < sectionPaths.length ? "weekly" : "monthly",
      priority: path === "" ? 1 : path === "/hymns" ? 0.9 : 0.8,
    }),
  );
}
