import type { Metadata } from "next";
import Link from "next/link";
import { getKeyLabel } from "@/lib/catalog";
import { getCatalogSnapshot } from "@/lib/catalog.server";
import { curatedPresets, getLandingTuneName } from "@/lib/landing-pages";

export const metadata: Metadata = {
  title: "Sheet Music for Instrumentalists — Keys, Clefs & Melody Parts",
  description:
    "Printable hymn sheet music for cello, trombone, and other instrumentalists. Start with an exact key, bass clef, or melody-part preset, then adjust the range.",
  alternates: { canonical: "/hymns/sheet-music-for-instrumentalists" },
  openGraph: {
    title: "Sheet Music for Instrumentalists — Keys, Clefs & Parts",
    description:
      "Configurable hymn melody parts and exact-key editions for instrumentalists.",
    type: "website",
    url: "/hymns/sheet-music-for-instrumentalists",
  },
};

export const dynamic = "force-dynamic";

export default async function InstrumentalistSheetMusicPage() {
  const snapshot = await getCatalogSnapshot();
  const instrumentPresets = curatedPresets.filter(
    (preset) => preset.kind === "instrument",
  );
  const keyPresets = curatedPresets.filter((preset) => preset.kind === "key");
  const hymnBySlug = new Map(snapshot.hymns.map((hymn) => [hymn.slug, hymn]));

  return (
    <>
      <section className="relative overflow-hidden border-b border-ink/10 bg-cream px-5 py-14 sm:px-8 sm:py-20 lg:px-10 lg:py-24">
        <div className="pointer-events-none absolute -right-24 -top-20 size-96 rounded-full bg-blue/10 blur-3xl" />
        <div className="relative mx-auto w-full max-w-[1440px]">
          <nav
            className="mb-8 flex items-center gap-2 font-mono text-[9px] uppercase tracking-[0.14em] text-ink/40"
            aria-label="Breadcrumb"
          >
            <Link className="transition hover:text-ink" href="/hymns">
              Hymns
            </Link>
            <span aria-hidden="true">/</span>
            <span className="text-ink/65">For instrumentalists</span>
          </nav>
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-blue">
            Instrument · key · clef
          </p>
          <h1 className="mt-4 max-w-5xl text-balance text-5xl font-medium leading-[0.94] tracking-[-0.06em] text-ink sm:text-7xl lg:text-8xl">
            Sheet music shaped for instrumentalists.
          </h1>
          <p className="mt-7 max-w-3xl text-pretty text-base leading-7 text-ink/60 sm:text-lg sm:leading-8">
            Start from a practical melody part or an exact key, then choose the
            clef and register that fit your instrument. Every edition stays in
            concert pitch unless the page explicitly says otherwise.
          </p>
        </div>
      </section>

      <section className="bg-paper px-5 py-16 sm:px-8 sm:py-24 lg:px-10">
        <div className="mx-auto w-full max-w-[1440px]">
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-coral">
            Instrument melody parts
          </p>
          <h2 className="mt-3 text-3xl font-medium tracking-[-0.045em] text-ink sm:text-5xl">
            Open with a musician-friendly range.
          </h2>
          <div className="mt-9 grid gap-4 lg:grid-cols-2">
            {instrumentPresets.map((preset) => {
              const hymn = hymnBySlug.get(preset.hymnSlug);
              if (!hymn) return null;
              return (
                <Link
                  key={preset.slug}
                  href={`/hymns/${preset.hymnSlug}/${preset.slug}`}
                  className="group rounded-3xl border border-ink/10 bg-cream p-7 transition hover:-translate-y-1 hover:border-ink/20 hover:shadow-[0_18px_44px_rgba(29,39,50,0.08)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral sm:p-9"
                >
                  <span className="font-mono text-[9px] uppercase tracking-[0.16em] text-coral">
                    {getLandingTuneName(hymn)} · {preset.shortLabel}
                  </span>
                  <h3 className="mt-10 text-3xl font-medium tracking-[-0.045em] text-ink sm:text-4xl">
                    {preset.heading}
                  </h3>
                  <p className="mt-4 max-w-2xl text-sm leading-6 text-ink/55">
                    {preset.intro}
                  </p>
                  <span className="mt-7 inline-flex text-sm font-semibold text-blue underline decoration-blue/25 underline-offset-4 transition group-hover:decoration-blue">
                    Preview the melody part →
                  </span>
                </Link>
              );
            })}
          </div>
        </div>
      </section>

      <section className="bg-[#edf0ef] px-5 py-16 sm:px-8 sm:py-24 lg:px-10">
        <div className="mx-auto w-full max-w-[1440px]">
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-blue">
            Exact-key hymn sheet music
          </p>
          <h2 className="mt-3 max-w-3xl text-balance text-3xl font-medium tracking-[-0.045em] text-ink sm:text-5xl">
            Begin in the requested key. Change anything else.
          </h2>
          <div className="mt-9 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {keyPresets.map((preset) => {
              const hymn = hymnBySlug.get(preset.hymnSlug);
              if (!hymn) return null;
              return (
                <Link
                  key={`${preset.hymnSlug}-${preset.slug}`}
                  href={`/hymns/${preset.hymnSlug}/${preset.slug}`}
                  className="group rounded-2xl border border-ink/10 bg-paper p-5 transition hover:-translate-y-0.5 hover:border-ink/20 hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral sm:p-6"
                >
                  <span className="font-mono text-[9px] uppercase tracking-[0.14em] text-coral">
                    {getKeyLabel(preset.edition.targetKey)} · SATB
                  </span>
                  <h3 className="mt-5 text-xl font-medium leading-tight tracking-[-0.035em] text-ink group-hover:text-blue">
                    {hymn.title}
                  </h3>
                  <p className="mt-3 text-xs leading-5 text-ink/48">
                    Original clefs, with every voice and alternate clef one
                    click away.
                  </p>
                </Link>
              );
            })}
          </div>
        </div>
      </section>

      <section className="bg-ink px-5 py-16 text-cream sm:px-8 sm:py-24 lg:px-10">
        <div className="mx-auto grid w-full max-w-[1440px] gap-10 lg:grid-cols-[0.8fr_1.2fr] lg:gap-20">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-coral">
              Clef and range
            </p>
            <h2 className="mt-4 text-balance text-4xl font-medium leading-[1.02] tracking-[-0.045em] sm:text-5xl">
              Bass clef is a notation choice. Range is a musical choice.
            </h2>
          </div>
          <div className="space-y-5 text-sm leading-7 text-cream/58 sm:text-base">
            <p>
              Cello and trombone pages open with the hymn melody in bass clef
              and automatically choose a readable octave. You can keep the
              same sounding pitches and change only the clef, or shift the
              melody by an octave when the instrument needs another register.
            </p>
            <p>
              These pages provide concert-pitch hymn melody parts. They do not
              claim to be composed solos with piano accompaniment, and they do
              not transpose for E-flat or B-flat instruments unless that is
              stated on the page.
            </p>
            <Link
              href="/uses/hymn-transposer#make-an-edition"
              className="inline-flex text-sm font-semibold text-coral underline decoration-coral/35 underline-offset-4 transition hover:decoration-coral focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral"
            >
              Configure any catalog hymn →
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
