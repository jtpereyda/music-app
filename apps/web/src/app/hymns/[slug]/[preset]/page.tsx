import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { HymnLandingPage } from "@/components/hymn-landing-page";
import {
  curatedPresets,
  editionFromSearchParams,
  getCuratedPreset,
  type EditionSearchParams,
} from "@/lib/landing-pages";
import {
  getCatalogSnapshot,
  renderApiConfigured,
} from "@/lib/catalog.server";
import { indexingEnabled } from "@/lib/site";

interface PresetPageProps {
  params: Promise<{ slug: string; preset: string }>;
  searchParams: Promise<EditionSearchParams>;
}

export const dynamic = "force-dynamic";

export function generateStaticParams() {
  return curatedPresets.map((preset) => ({
    slug: preset.hymnSlug,
    preset: preset.slug,
  }));
}

export async function generateMetadata({
  params,
}: PresetPageProps): Promise<Metadata> {
  const { slug, preset: presetSlug } = await params;
  const preset = getCuratedPreset(slug, presetSlug);

  if (!preset) {
    return {};
  }

  const canonical = `/hymns/${preset.hymnSlug}/${preset.slug}`;

  return {
    title: preset.title,
    description: preset.intro,
    alternates: { canonical },
    openGraph: {
      title: preset.title,
      description: preset.intro,
      type: "website",
      url: canonical,
    },
    robots: {
      index: indexingEnabled(),
      follow: indexingEnabled(),
    },
  };
}

export default async function PresetPage({
  params,
  searchParams,
}: PresetPageProps) {
  const [{ slug, preset: presetSlug }, query, snapshot] = await Promise.all([
    params,
    searchParams,
    getCatalogSnapshot(),
  ]);
  const preset = getCuratedPreset(slug, presetSlug);
  const hymn = snapshot.hymns.find((item) => item.slug === slug);

  if (!preset || !hymn) {
    notFound();
  }

  const initialEdition = editionFromSearchParams(query, preset.edition);

  return (
    <HymnLandingPage
      hymn={hymn}
      catalog={snapshot.hymns}
      renderApiConnected={renderApiConfigured()}
      preset={preset}
      initialEdition={initialEdition}
      urlBaseEdition={preset.edition}
    />
  );
}
