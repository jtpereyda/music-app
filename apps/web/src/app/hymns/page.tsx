import type { Metadata } from "next";
import Link from "next/link";
import { getKeyLabel } from "@/lib/catalog";
import { getCatalogSnapshot } from "@/lib/catalog.server";
import {
  getLandingTuneName,
  getPresetsForHymn,
  priorityHymnSlugs,
} from "@/lib/landing-pages";
import { getSiteUrl } from "@/lib/site";

export const metadata: Metadata = {
  title: "Free Hymn Sheet Music in Any Key & Clef",
  description:
    "Browse free printable hymn sheet music by title and tune. Change the key, choose full SATB or an individual voice, select a clef, and download a fresh PDF.",
  alternates: { canonical: "/hymns" },
  openGraph: {
    title: "Free Hymn Sheet Music in Any Key & Clef",
    description:
      "Traditional hymn scores with selectable keys, SATB parts, clefs, live previews, and print-ready PDFs.",
    url: "/hymns",
    type: "website",
  },
};

export const dynamic = "force-dynamic";

function jsonLd(value: object): string {
  return JSON.stringify(value).replaceAll("<", "\\u003c");
}

export default async function HymnsPage() {
  const snapshot = await getCatalogSnapshot();
  const hymns = priorityHymnSlugs
    .map((slug) => snapshot.hymns.find((hymn) => hymn.slug === slug))
    .filter((hymn) => hymn !== undefined);
  const structuredData = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    name: "Free printable hymn sheet music",
    itemListElement: hymns.map((hymn, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: hymn.title,
      url: new URL(`/hymns/${hymn.slug}`, getSiteUrl()).toString(),
    })),
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: jsonLd(structuredData) }}
      />
      <section className="border-b border-ink/10 bg-cream px-5 py-14 sm:px-8 sm:py-20 lg:px-10 lg:py-24">
        <div className="mx-auto w-full max-w-[1440px]">
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-coral">
            Free hymn sheet music
          </p>
          <h1 className="mt-4 max-w-5xl text-balance text-5xl font-medium leading-[0.94] tracking-[-0.06em] text-ink sm:text-7xl lg:text-8xl">
            Traditional hymns, in the key and clef you need.
          </h1>
          <p className="mt-7 max-w-3xl text-pretty text-base leading-7 text-ink/60 sm:text-lg sm:leading-8">
            Choose a hymn by title or tune, preview the complete score, and
            print a fresh edition. Every hymn page includes full SATB plus
            soprano, alto, tenor, and bass lines in selectable clefs.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              href="#hymn-collection"
              className="rounded-full bg-ink px-5 py-2.5 text-sm font-semibold text-cream transition hover:-translate-y-px hover:bg-ink/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral focus-visible:ring-offset-4"
            >
              Browse hymn titles
            </Link>
            <Link
              href="/hymns/sheet-music-for-instrumentalists"
              className="rounded-full border border-ink/15 bg-white/45 px-5 py-2.5 text-sm font-medium text-ink transition hover:-translate-y-px hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral focus-visible:ring-offset-4"
            >
              Browse by instrument, key, or clef
            </Link>
          </div>
        </div>
      </section>

      <section
        id="hymn-collection"
        className="bg-paper px-5 py-16 sm:px-8 sm:py-24 lg:px-10"
      >
        <div className="mx-auto w-full max-w-[1440px]">
          <div className="flex flex-wrap items-end justify-between gap-6">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-blue">
                Priority hymn editions
              </p>
              <h2 className="mt-3 text-3xl font-medium tracking-[-0.045em] text-ink sm:text-5xl">
                Start with a hymn.
              </h2>
            </div>
            <p className="max-w-lg text-sm leading-6 text-ink/50">
              These launch pages answer the most active hymn-sheet-music
              searches first. The full in-product catalog remains available
              from the edition builder.
            </p>
          </div>

          <div className="mt-10 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {hymns.map((hymn) => {
              const presets = getPresetsForHymn(hymn.slug);
              return (
                <article
                  key={hymn.id}
                  className="group flex min-h-80 flex-col rounded-3xl border border-ink/10 bg-cream p-6 transition hover:-translate-y-0.5 hover:border-ink/20 hover:shadow-[0_18px_44px_rgba(29,39,50,0.08)] sm:p-7"
                >
                  <div className="flex items-start justify-between gap-5">
                    <p className="font-mono text-[9px] uppercase tracking-[0.16em] text-coral">
                      {getLandingTuneName(hymn)}
                    </p>
                    <span className="rounded-full border border-ink/10 bg-white/60 px-2.5 py-1 font-mono text-[8px] uppercase tracking-[0.12em] text-ink/45">
                      {getKeyLabel(hymn.originalKey)} source
                    </span>
                  </div>
                  <h3 className="mt-8 text-3xl font-medium leading-[1.02] tracking-[-0.045em] text-ink">
                    <Link
                      href={`/hymns/${hymn.slug}`}
                      className="rounded-sm outline-none focus-visible:ring-2 focus-visible:ring-coral"
                    >
                      {hymn.title}
                    </Link>
                  </h3>
                  <p className="mt-4 text-sm leading-6 text-ink/52">
                    Words by {hymn.textAuthor}. Full SATB or any individual
                    hymn voice, transposed and freshly engraved.
                  </p>
                  <div className="mt-auto pt-7">
                    {presets.length ? (
                      <p className="mb-3 text-xs text-ink/42">
                        Ready-made: {presets.map((preset) => preset.shortLabel).join(" · ")}
                      </p>
                    ) : null}
                    <Link
                      href={`/hymns/${hymn.slug}`}
                      className="text-sm font-semibold text-blue underline decoration-blue/25 underline-offset-4 transition group-hover:decoration-blue focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral"
                    >
                      Open sheet music →
                    </Link>
                  </div>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      <section className="bg-ink px-5 py-14 text-cream sm:px-8 sm:py-18 lg:px-10">
        <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="font-mono text-[9px] uppercase tracking-[0.16em] text-coral">
              Need a different starting point?
            </p>
            <h2 className="mt-2 text-2xl font-medium tracking-[-0.035em]">
              Browse melody parts by instrument, key, and clef.
            </h2>
          </div>
          <Link
            href="/hymns/sheet-music-for-instrumentalists"
            className="inline-flex self-start rounded-full bg-coral px-5 py-2.5 text-sm font-semibold text-white transition hover:-translate-y-px hover:bg-[#d95f45] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral focus-visible:ring-offset-4 focus-visible:ring-offset-ink"
          >
            Sheet music for instrumentalists
          </Link>
        </div>
      </section>
    </>
  );
}
