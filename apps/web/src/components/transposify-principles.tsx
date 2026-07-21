import Link from "next/link";

const principles = [
  {
    title: "Start with music data",
    copy: "Notes, rhythms, voices, and keys stay structured so the transformation remains musical.",
  },
  {
    title: "Change the right thing",
    copy: "Transposition changes pitches. A clef changes their representation. The tool keeps that distinction explicit.",
  },
  {
    title: "Finish with a real edition",
    copy: "Preview and PDF come from the same engraving path, sized for a music stand and a printer.",
  },
] as const;

export function TransposifyPrinciples() {
  return (
    <section
      id="how-transposify-works"
      className="bg-ink px-5 py-16 text-cream sm:px-8 sm:py-24 lg:px-10"
    >
      <div className="mx-auto w-full max-w-[1440px]">
        <div className="grid gap-12 lg:grid-cols-[0.72fr_1.28fr] lg:gap-20">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-coral">
              The Transposify approach
            </p>
            <h2 className="mt-4 max-w-md text-balance text-4xl font-medium leading-[1.02] tracking-[-0.045em] sm:text-5xl">
              Move the music without losing its meaning.
            </h2>
            <p className="mt-6 max-w-md text-sm leading-6 text-cream/55">
              The live hymn tool is a focused demonstration of the system:
              semantic transformation first, fresh notation second.
            </p>
          </div>

          <div>
            <ol className="divide-y divide-cream/10 border-y border-cream/10">
              {principles.map((principle, index) => (
                <li
                  key={principle.title}
                  className="grid gap-3 py-6 sm:grid-cols-[52px_0.8fr_1.2fr] sm:items-start sm:gap-6 sm:py-7"
                >
                  <span className="font-mono text-[10px] tracking-[0.15em] text-coral">
                    0{index + 1}
                  </span>
                  <h3 className="text-base font-medium tracking-[-0.02em] text-cream">
                    {principle.title}
                  </h3>
                  <p className="text-sm leading-6 text-cream/50">
                    {principle.copy}
                  </p>
                </li>
              ))}
            </ol>
            <div className="mt-9 flex flex-wrap items-center justify-between gap-5 rounded-2xl border border-cream/10 bg-cream/[0.04] p-5 sm:p-6">
              <div>
                <p className="text-sm font-medium text-cream">
                  Put the live workflow through its paces.
                </p>
                <p className="mt-1 text-xs text-cream/45">
                  Free beta · no account needed
                </p>
              </div>
              <Link
                href="/uses/hymn-transposer#make-an-edition"
                className="inline-flex rounded-full bg-coral px-5 py-2.5 text-sm font-semibold text-white transition hover:-translate-y-px hover:bg-[#d95f45] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral focus-visible:ring-offset-4 focus-visible:ring-offset-ink"
              >
                Make a hymn edition
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
