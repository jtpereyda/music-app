import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { HymnLandingPage } from "@/components/hymn-landing-page";
import { hymns } from "@/lib/catalog";
import {
  defaultEdition,
  editionFromSearchParams,
  getLandingTuneName,
  isPriorityHymn,
  type EditionSearchParams,
} from "@/lib/landing-pages";
import { indexingEnabled } from "@/lib/site";
import {
  getCatalogSnapshot,
  renderApiConfigured,
} from "@/lib/catalog.server";

interface HymnPageProps {
  params: Promise<{ slug: string }>;
  searchParams: Promise<EditionSearchParams>;
}

export const dynamic = "force-dynamic";

export function generateStaticParams() {
  return hymns.map((hymn) => ({ slug: hymn.slug }));
}

export async function generateMetadata({
  params,
}: HymnPageProps): Promise<Metadata> {
  const { slug } = await params;
  const snapshot = await getCatalogSnapshot();
  const hymn = snapshot.hymns.find((item) => item.slug === slug);

  if (!hymn) {
    return {};
  }

  const tuneName = getLandingTuneName(hymn);
  const title = `${hymn.title} Sheet Music in Any Key & Clef`;
  const description = `Printable ${hymn.title} sheet music to the traditional ${tuneName} tune. Choose any major key, full SATB or one hymn voice, and treble, bass, alto, or tenor clef.`;

  return {
    title,
    description,
    alternates: {
      canonical: `/hymns/${hymn.slug}`,
    },
    openGraph: {
      title,
      description,
      type: "website",
      url: `/hymns/${hymn.slug}`,
    },
    robots: {
      index: indexingEnabled() && isPriorityHymn(hymn.slug),
      follow: indexingEnabled(),
    },
  };
}

export default async function HymnPage({
  params,
  searchParams,
}: HymnPageProps) {
  const [{ slug }, query, snapshot] = await Promise.all([
    params,
    searchParams,
    getCatalogSnapshot(),
  ]);
  const hymn = snapshot.hymns.find((item) => item.slug === slug);

  if (!hymn) {
    notFound();
  }

  const urlBaseEdition = defaultEdition(hymn);
  const initialEdition = editionFromSearchParams(query, urlBaseEdition);

  return (
    <HymnLandingPage
      hymn={hymn}
      catalog={snapshot.hymns}
      renderApiConnected={renderApiConfigured()}
      initialEdition={initialEdition}
      urlBaseEdition={urlBaseEdition}
    />
  );
}
