import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { HymnConfigurator } from "@/components/hymn-configurator";
import { getKeyLabel, hymns } from "@/lib/catalog";
import {
  getCatalogSnapshot,
  renderApiConfigured,
} from "@/lib/catalog.server";

interface HymnPageProps {
  params: Promise<{ slug: string }>;
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

  return {
    title: `${hymn.title} sheet music in any key`,
    description: `Transpose ${hymn.title} (${hymn.tuneName}) into any major key, choose a SATB voice and clef, and make a print-ready PDF.`,
    alternates: {
      canonical: `/hymns/${hymn.slug}`,
    },
  };
}

export default async function HymnPage({ params }: HymnPageProps) {
  const { slug } = await params;
  const snapshot = await getCatalogSnapshot();
  const hymn = snapshot.hymns.find((item) => item.slug === slug);

  if (!hymn) {
    notFound();
  }

  return (
    <>
      <section className="border-b border-ink/10 bg-cream px-5 py-12 sm:px-8 sm:py-16 lg:px-10">
        <div className="mx-auto w-full max-w-[1440px]">
          <nav className="mb-8 flex items-center gap-2 font-mono text-[9px] uppercase tracking-[0.14em] text-ink/40">
            <Link
              className="transition hover:text-ink"
              href="/uses/hymn-transposer"
            >
              Hymn transposer
            </Link>
            <span aria-hidden="true">/</span>
            <span className="truncate text-ink/65">{hymn.title}</span>
          </nav>
          <div className="grid gap-7 lg:grid-cols-[1fr_320px] lg:items-end">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-coral">
                {hymn.tuneName} · {hymn.meter}
              </p>
              <h1 className="mt-4 max-w-4xl text-balance text-4xl font-medium leading-[0.98] tracking-[-0.05em] text-ink sm:text-6xl lg:text-7xl">
                {hymn.title} sheet music, made to fit.
              </h1>
            </div>
            <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-ink/10 bg-ink/10">
              <div className="bg-paper p-4">
                <dt className="text-xs text-ink/45">Text</dt>
                <dd className="mt-1 text-sm font-medium text-ink">
                  {hymn.textAuthor}
                </dd>
              </div>
              <div className="bg-paper p-4">
                <dt className="text-xs text-ink/45">Source key</dt>
                <dd className="mt-1 font-mono text-xs font-medium text-ink">
                  {getKeyLabel(hymn.originalKey)}
                </dd>
              </div>
            </dl>
          </div>
          <p className="mt-7 max-w-2xl text-sm leading-6 text-ink/55">
            Create a fresh edition for full SATB or a single voice line. Change
            key, clef, pitch register, and page size below—the source pitches
            remain structured music data, never a distorted scan.
          </p>
        </div>
      </section>
      <HymnConfigurator
        initialHymn={hymn}
        catalog={snapshot.hymns}
        renderApiConnected={renderApiConfigured()}
        navigateOnHymnSelect
      />
    </>
  );
}
