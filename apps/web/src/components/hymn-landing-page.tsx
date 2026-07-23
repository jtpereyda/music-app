import Link from "next/link";
import { HymnConfigurator } from "@/components/hymn-configurator";
import {
  getKeyLabel,
  outputOptions,
  type EditionConfig,
  type Hymn,
} from "@/lib/catalog";
import {
  getLandingTuneName,
  getPresetsForHymn,
  isPriorityHymn,
  type CuratedPreset,
} from "@/lib/landing-pages";
import { getSiteUrl } from "@/lib/site";

interface HymnLandingPageProps {
  hymn: Hymn;
  catalog: readonly Hymn[];
  renderApiConnected: boolean;
  initialEdition: EditionConfig;
  urlBaseEdition: EditionConfig;
  preset?: CuratedPreset;
}

function jsonLd(value: object): string {
  return JSON.stringify(value).replaceAll("<", "\\u003c");
}

export function HymnLandingPage({
  hymn,
  catalog,
  renderApiConnected,
  initialEdition,
  urlBaseEdition,
  preset,
}: HymnLandingPageProps) {
  const tuneName = getLandingTuneName(hymn);
  const presets = getPresetsForHymn(hymn.slug);
  const heading =
    preset?.heading ??
    `${hymn.title} sheet music in the key and clef you need`;
  const intro =
    preset?.intro ??
    `Print the traditional ${tuneName} tune, choose any major key, and use the complete SATB score or an individual soprano, alto, tenor, or bass line in the clef you need.`;
  const canonicalPath = preset
    ? `/hymns/${hymn.slug}/${preset.slug}`
    : `/hymns/${hymn.slug}`;
  const relatedHymns = catalog
    .filter(
      (candidate) =>
        candidate.slug !== hymn.slug && isPriorityHymn(candidate.slug),
    )
    .slice(0, 3);
  const selectedPart =
    outputOptions.find(
      (option) => option.value === initialEdition.outputPart,
    )?.label ?? initialEdition.outputPart;
  const structuredData = {
    "@context": "https://schema.org",
    "@type": "MusicComposition",
    name: hymn.title,
    alternateName: `${hymn.title} (${tuneName})`,
    lyricist: {
      "@type": "Person",
      name: hymn.textAuthor,
    },
    url: new URL(canonicalPath, getSiteUrl()).toString(),
    inLanguage: "en",
    description: intro,
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: jsonLd(structuredData) }}
      />
      <section className="border-b border-ink/10 bg-cream px-5 py-12 sm:px-8 sm:py-16 lg:px-10">
        <div className="mx-auto w-full max-w-[1440px]">
          <nav
            className="mb-8 flex flex-wrap items-center gap-2 font-mono text-[9px] uppercase tracking-[0.14em] text-ink/40"
            aria-label="Breadcrumb"
          >
            <Link className="transition hover:text-ink" href="/hymns">
              Hymns
            </Link>
            {preset?.kind === "instrument" || preset?.kind === "clef" ? (
              <>
                <span aria-hidden="true">/</span>
                <Link
                  className="transition hover:text-ink"
                  href="/hymns/sheet-music-for-instrumentalists"
                >
                  For instrumentalists
                </Link>
              </>
            ) : null}
            <span aria-hidden="true">/</span>
            {preset ? (
              <Link
                className="transition hover:text-ink"
                href={`/hymns/${hymn.slug}`}
              >
                {hymn.title}
              </Link>
            ) : (
              <span className="truncate text-ink/65">{hymn.title}</span>
            )}
            {preset ? (
              <>
                <span aria-hidden="true">/</span>
                <span className="text-ink/65">{preset.shortLabel}</span>
              </>
            ) : null}
          </nav>

          <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_390px] lg:items-end lg:gap-14">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-coral">
                {preset?.eyebrow ?? `${tuneName} · ${hymn.meter}`}
              </p>
              <h1 className="mt-4 max-w-5xl text-balance text-4xl font-medium leading-[0.98] tracking-[-0.05em] text-ink sm:text-6xl lg:text-7xl">
                {heading}
              </h1>
              <p className="mt-7 max-w-3xl text-pretty text-base leading-7 text-ink/60 sm:text-lg sm:leading-8">
                {intro}
              </p>
              <div className="mt-7 flex flex-wrap gap-3">
                <Link
                  href="#make-an-edition"
                  className="inline-flex rounded-full bg-ink px-5 py-2.5 text-sm font-semibold text-cream transition hover:-translate-y-px hover:bg-ink/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral focus-visible:ring-offset-4"
                >
                  Preview and download
                </Link>
                <Link
                  href="/hymns/sheet-music-for-instrumentalists"
                  className="inline-flex rounded-full border border-ink/15 bg-white/50 px-5 py-2.5 text-sm font-medium text-ink transition hover:-translate-y-px hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral focus-visible:ring-offset-4"
                >
                  Browse keys and parts
                </Link>
              </div>
            </div>

            <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-ink/10 bg-ink/10">
              <div className="bg-paper p-4 sm:p-5">
                <dt className="text-xs text-ink/45">Traditional tune</dt>
                <dd className="mt-1 text-sm font-medium text-ink">
                  {tuneName}
                </dd>
              </div>
              <div className="bg-paper p-4 sm:p-5">
                <dt className="text-xs text-ink/45">Selected key</dt>
                <dd className="mt-1 font-mono text-xs font-medium text-ink">
                  {getKeyLabel(initialEdition.targetKey)}
                </dd>
              </div>
              <div className="bg-paper p-4 sm:p-5">
                <dt className="text-xs text-ink/45">Words</dt>
                <dd className="mt-1 text-sm font-medium text-ink">
                  {hymn.textAuthor}
                </dd>
              </div>
              <div className="bg-paper p-4 sm:p-5">
                <dt className="text-xs text-ink/45">Edition</dt>
                <dd className="mt-1 text-sm font-medium text-ink">
                  {selectedPart}
                </dd>
              </div>
            </dl>
          </div>

          {presets.length ? (
            <div className="mt-10 border-t border-ink/10 pt-6">
              <p className="font-mono text-[9px] uppercase tracking-[0.15em] text-ink/45">
                Ready-made editions
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Link
                  href={`/hymns/${hymn.slug}`}
                  aria-current={preset ? undefined : "page"}
                  className={`rounded-full border px-3.5 py-2 text-xs font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral ${
                    preset
                      ? "border-ink/10 bg-white/45 text-ink/60 hover:bg-white hover:text-ink"
                      : "border-ink bg-ink text-cream"
                  }`}
                >
                  Any key & clef
                </Link>
                {presets.map((candidate) => {
                  const active = preset?.slug === candidate.slug;
                  return (
                    <Link
                      key={candidate.slug}
                      href={`/hymns/${hymn.slug}/${candidate.slug}`}
                      aria-current={active ? "page" : undefined}
                      className={`rounded-full border px-3.5 py-2 text-xs font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral ${
                        active
                          ? "border-ink bg-ink text-cream"
                          : "border-ink/10 bg-white/45 text-ink/60 hover:bg-white hover:text-ink"
                      }`}
                    >
                      {candidate.shortLabel}
                    </Link>
                  );
                })}
              </div>
            </div>
          ) : null}
        </div>
      </section>

      <HymnConfigurator
        initialHymn={hymn}
        catalog={catalog}
        renderApiConnected={renderApiConnected}
        navigateOnHymnSelect
        initialEdition={initialEdition}
        urlBaseEdition={urlBaseEdition}
      />

      <section className="bg-paper px-5 py-16 sm:px-8 sm:py-24 lg:px-10">
        <div className="mx-auto grid w-full max-w-[1440px] gap-12 lg:grid-cols-[1.2fr_0.8fr] lg:gap-20">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-coral">
              About this sheet music
            </p>
            <h2 className="mt-4 max-w-2xl text-balance text-3xl font-medium leading-[1.05] tracking-[-0.045em] text-ink sm:text-5xl">
              A practical edition of {hymn.title}, built from music data.
            </h2>
            <div className="mt-7 max-w-3xl space-y-5 text-sm leading-7 text-ink/58 sm:text-base">
              <p>
                This page uses the traditional {tuneName} setting associated
                with {hymn.title}, with words credited to {hymn.textAuthor}.
                Naming the tune keeps this edition distinct from modern songs
                or arrangements that may share the same title.
              </p>
              <p>
                Choose full SATB, soprano, alto, tenor, or bass. Individual
                lines can be written in treble, bass, alto, tenor, or treble
                8vb clef and moved by an octave when a different range is more
                useful. Transposition changes the notes; clef selection changes
                how those notes are written.
              </p>
              {preset?.kind === "instrument" ? (
                <p className="rounded-2xl border border-blue/15 bg-blue/[0.05] p-5 text-ink/65">
                  This instrument page provides the hymn melody as a flexible,
                  concert-pitch part. It does not include a separately composed
                  piano accompaniment or imply a published solo arrangement.
                </p>
              ) : null}
              {preset?.kind === "clef" ? (
                <p className="rounded-2xl border border-blue/15 bg-blue/[0.05] p-5 text-ink/65">
                  This bass-clef page starts with the traditional hymn melody
                  in a readable register. It is not tied to one instrument, so
                  you can keep bass clef while changing the key or octave.
                </p>
              ) : null}
            </div>
          </div>

          <aside className="rounded-3xl border border-ink/10 bg-cream p-6 sm:p-8">
            <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink/45">
              What you can make
            </p>
            <ul className="mt-5 divide-y divide-ink/10 text-sm text-ink/65">
              <li className="flex items-start gap-3 py-4 first:pt-0">
                <span className="mt-1 text-coral" aria-hidden="true">✓</span>
                A print-ready PDF in US Letter or A4 size
              </li>
              <li className="flex items-start gap-3 py-4">
                <span className="mt-1 text-coral" aria-hidden="true">✓</span>
                A complete SATB score or one extracted hymn voice
              </li>
              <li className="flex items-start gap-3 py-4">
                <span className="mt-1 text-coral" aria-hidden="true">✓</span>
                Any supported major key and a musician-friendly clef
              </li>
              <li className="flex items-start gap-3 py-4 last:pb-0">
                <span className="mt-1 text-coral" aria-hidden="true">✓</span>
                A shareable URL for the exact choices shown in the preview
              </li>
            </ul>
            <p className="mt-6 border-t border-ink/10 pt-5 text-xs leading-5 text-ink/42">
              Source notation: {hymn.sourceLabel}. Score publication status and
              source provenance are tracked separately in the catalog.
            </p>
          </aside>
        </div>

        <div className="mx-auto mt-16 w-full max-w-[1440px] border-t border-ink/10 pt-10">
          <div className="flex flex-wrap items-end justify-between gap-5">
            <div>
              <p className="font-mono text-[9px] uppercase tracking-[0.15em] text-ink/42">
                Continue browsing
              </p>
              <h2 className="mt-2 text-2xl font-medium tracking-[-0.035em] text-ink">
                More free hymn sheet music
              </h2>
            </div>
            <Link
              className="text-sm font-semibold text-blue underline decoration-blue/25 underline-offset-4 transition hover:decoration-blue"
              href="/hymns"
            >
              View the hymn collection →
            </Link>
          </div>
          <div className="mt-6 grid gap-3 sm:grid-cols-3">
            {relatedHymns.map((related) => (
              <Link
                key={related.id}
                href={`/hymns/${related.slug}`}
                className="group rounded-2xl border border-ink/10 bg-cream p-5 transition hover:-translate-y-0.5 hover:border-ink/20 hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral"
              >
                <span className="font-mono text-[9px] uppercase tracking-[0.14em] text-coral">
                  {getLandingTuneName(related)}
                </span>
                <span className="mt-2 block text-base font-medium tracking-[-0.02em] text-ink group-hover:text-blue">
                  {related.title}
                </span>
                <span className="mt-3 block text-xs text-ink/45">
                  Any key · SATB & individual parts
                </span>
              </Link>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
