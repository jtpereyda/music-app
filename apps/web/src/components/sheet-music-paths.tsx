import Link from "next/link";

const paths = [
  {
    eyebrow: "Hymns",
    title: "Find a hymn, then make the edition fit.",
    copy: "Browse traditional hymn sheet music by title and tune. Every page opens the complete tool with SATB parts, key changes, clef choices, and a printable PDF.",
    href: "/hymns",
    link: "Browse hymn sheet music",
    tone: "coral",
  },
  {
    eyebrow: "Sheet music for instrumentalists",
    title: "Start with the key, clef, or instrument.",
    copy: "Open demand-validated cello, trombone, bass-clef, and exact-key editions, then adjust the melody part or range for the player in front of you.",
    href: "/hymns/sheet-music-for-instrumentalists",
    link: "Browse keys, clefs, and parts",
    tone: "blue",
  },
] as const;

export function SheetMusicPaths() {
  return (
    <section className="bg-paper px-5 py-16 sm:px-8 sm:py-24 lg:px-10">
      <div className="mx-auto w-full max-w-[1440px]">
        <div className="max-w-3xl">
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-coral">
            Browse sheet music
          </p>
          <h2 className="mt-4 text-balance text-4xl font-medium leading-[1] tracking-[-0.05em] text-ink sm:text-6xl">
            Two ways into the same flexible score.
          </h2>
        </div>
        <div className="mt-10 grid gap-4 lg:grid-cols-2">
          {paths.map((path, index) => (
            <Link
              key={path.href}
              href={path.href}
              className="group relative min-h-80 overflow-hidden rounded-3xl border border-ink/10 bg-cream p-7 transition hover:-translate-y-1 hover:border-ink/20 hover:shadow-[0_20px_50px_rgba(29,39,50,0.1)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral focus-visible:ring-offset-4 sm:p-10"
            >
              <div
                className={`pointer-events-none absolute -right-16 -top-20 size-64 rounded-full blur-3xl ${
                  path.tone === "coral" ? "bg-coral/15" : "bg-blue/15"
                }`}
              />
              <span className="font-mono text-[9px] uppercase tracking-[0.16em] text-ink/42">
                0{index + 1} · {path.eyebrow}
              </span>
              <h3 className="relative mt-12 max-w-xl text-balance text-3xl font-medium leading-[1.04] tracking-[-0.045em] text-ink sm:text-4xl">
                {path.title}
              </h3>
              <p className="relative mt-5 max-w-xl text-sm leading-6 text-ink/55 sm:text-base sm:leading-7">
                {path.copy}
              </p>
              <span className="relative mt-8 inline-flex items-center gap-2 text-sm font-semibold text-blue underline decoration-blue/25 underline-offset-4 transition group-hover:decoration-blue">
                {path.link}
                <span aria-hidden="true">→</span>
              </span>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}
