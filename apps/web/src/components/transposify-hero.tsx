import Link from "next/link";

const editionFields = [
  ["Key", "D major"],
  ["Line", "Bass"],
  ["Clef", "Bass"],
  ["Register", "Auto"],
  ["Page", "Letter"],
] as const;

export function TransposifyHero() {
  return (
    <section className="relative overflow-hidden border-b border-ink/10 bg-cream">
      <div className="pointer-events-none absolute -left-28 top-12 size-80 rounded-full bg-coral/10 blur-3xl" />
      <div className="pointer-events-none absolute -right-24 -top-24 size-96 rounded-full bg-blue/10 blur-3xl" />
      <div className="mx-auto grid w-full max-w-[1440px] gap-12 px-5 py-16 sm:px-8 sm:py-24 lg:grid-cols-[minmax(0,1.05fr)_minmax(380px,0.7fr)] lg:items-center lg:gap-20 lg:px-10 lg:py-28">
        <div className="relative z-10 max-w-4xl">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-ink/10 bg-white/70 px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.15em] text-ink/65 shadow-sm">
            <span className="size-1.5 rounded-full bg-coral" />
            Practical music tools
          </div>
          <h1 className="text-balance text-[clamp(3.25rem,7vw,7rem)] font-medium leading-[0.9] tracking-[-0.07em] text-ink">
            Shape the score{" "}
            <span className="text-coral">to fit the musician.</span>
          </h1>
          <p className="mt-8 max-w-2xl text-pretty text-base leading-7 text-ink/62 sm:text-lg sm:leading-8">
            Transposify turns structured music into practical, freshly
            engraved editions. The first live tool is built for hymns: choose
            the key, SATB line, clef, and page size you actually need.
          </p>
          <div className="mt-9 flex flex-wrap items-center gap-3">
            <Link
              href="/uses/hymn-transposer#make-an-edition"
              className="inline-flex items-center gap-2 rounded-full bg-ink px-5 py-3 text-sm font-semibold text-cream shadow-[0_10px_24px_rgba(29,39,50,0.18)] transition hover:-translate-y-px hover:bg-ink/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral focus-visible:ring-offset-4"
            >
              Try the hymn transposer
              <span aria-hidden="true">↗</span>
            </Link>
            <Link
              href="/#how-transposify-works"
              className="inline-flex rounded-full border border-ink/15 bg-white/45 px-5 py-3 text-sm font-medium text-ink transition hover:-translate-y-px hover:bg-white/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral focus-visible:ring-offset-4"
            >
              See how it works
            </Link>
          </div>
          <div className="mt-10 flex items-center gap-3 border-t border-ink/10 pt-5 text-xs text-ink/48">
            <span className="relative flex size-2" aria-hidden="true">
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-[#4f8e6b] opacity-40" />
              <span className="relative inline-flex size-2 rounded-full bg-[#4f8e6b]" />
            </span>
            <span>
              Live now: hymn transposition and print-ready PDF editions
            </span>
          </div>
        </div>

        <div className="relative mx-auto w-full max-w-xl lg:max-w-none" aria-hidden="true">
          <div className="absolute -inset-8 rounded-full bg-white/25 blur-2xl" />
          <div className="relative rotate-[1.5deg] rounded-[28px] border border-ink/10 bg-[#e8ecea] p-3 shadow-[0_28px_80px_rgba(29,39,50,0.16)] sm:p-4">
            <div className="flex items-center justify-between rounded-t-[20px] border-b border-ink/10 bg-paper px-4 py-3">
              <span className="font-mono text-[9px] uppercase tracking-[0.16em] text-ink/42">
                Edition request
              </span>
              <span className="rounded-full bg-[#4f8e6b]/10 px-2.5 py-1 font-mono text-[8px] uppercase tracking-[0.12em] text-[#34704f]">
                Ready
              </span>
            </div>
            <div className="grid gap-3 bg-paper p-4 sm:grid-cols-[0.7fr_1.3fr]">
              <div className="space-y-2">
                {editionFields.map(([label, value]) => (
                  <div
                    key={label}
                    className="rounded-xl border border-ink/10 bg-cream/55 px-3 py-2.5"
                  >
                    <span className="block text-[9px] uppercase tracking-[0.12em] text-ink/38">
                      {label}
                    </span>
                    <span className="mt-0.5 block text-xs font-semibold text-ink">
                      {value}
                    </span>
                  </div>
                ))}
              </div>
              <div className="min-h-64 rounded-sm bg-white px-5 py-6 shadow-[0_10px_28px_rgba(29,39,50,0.09)]">
                <div className="mx-auto h-1.5 w-24 rounded-full bg-ink/14" />
                <div className="mx-auto mt-2 h-1 w-16 rounded-full bg-ink/8" />
                <div className="relative mt-10 text-ink/55">
                  <div className="music-staff" />
                  <span className="absolute left-[12%] top-1 size-2 -rotate-12 rounded-full bg-ink/70" />
                  <span className="absolute left-[32%] top-2.5 size-2 -rotate-12 rounded-full bg-ink/70" />
                  <span className="absolute left-[53%] top-0 size-2 -rotate-12 rounded-full bg-coral" />
                  <span className="absolute left-[75%] top-3 size-2 -rotate-12 rounded-full bg-ink/70" />
                </div>
                <div className="relative mt-10 text-ink/55">
                  <div className="music-staff" />
                  <span className="absolute left-[18%] top-2.5 size-2 -rotate-12 rounded-full bg-ink/70" />
                  <span className="absolute left-[41%] top-1 size-2 -rotate-12 rounded-full bg-ink/70" />
                  <span className="absolute left-[65%] top-3.5 size-2 -rotate-12 rounded-full bg-ink/70" />
                </div>
                <div className="relative mt-10 text-ink/55">
                  <div className="music-staff" />
                  <span className="absolute left-[24%] top-0 size-2 -rotate-12 rounded-full bg-ink/70" />
                  <span className="absolute left-[50%] top-2 size-2 -rotate-12 rounded-full bg-ink/70" />
                  <span className="absolute left-[78%] top-1 size-2 -rotate-12 rounded-full bg-coral" />
                </div>
              </div>
            </div>
            <div className="rounded-b-[20px] bg-ink px-4 py-3 font-mono text-[9px] uppercase tracking-[0.13em] text-cream/60">
              Structured score → fresh notation
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
