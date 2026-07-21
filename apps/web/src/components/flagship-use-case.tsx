import Link from "next/link";

const capabilities = [
  {
    number: "01",
    label: "Find",
    copy: "Choose from the curated technical-preview hymn catalog.",
  },
  {
    number: "02",
    label: "Fit",
    copy: "Set the key, full SATB or a single line, clef, pitch register, and page size.",
  },
  {
    number: "03",
    label: "Print",
    copy: "Preview fresh notation and download the matching engraved PDF.",
  },
] as const;

export function FlagshipUseCase() {
  return (
    <section className="bg-[#edf0ef] px-5 py-16 sm:px-8 sm:py-24 lg:px-10">
      <div className="mx-auto w-full max-w-[1440px]">
        <div className="grid gap-10 lg:grid-cols-[0.72fr_1.28fr] lg:items-end lg:gap-20">
          <div>
            <div className="inline-flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.18em] text-[#34704f]">
              <span className="size-1.5 rounded-full bg-[#4f8e6b]" />
              Live flagship use case
            </div>
            <h2 className="mt-4 max-w-lg text-balance text-4xl font-medium leading-[1] tracking-[-0.05em] text-ink sm:text-6xl">
              Hymn editions that meet the moment.
            </h2>
          </div>
          <div className="max-w-2xl lg:justify-self-end">
            <p className="text-base leading-7 text-ink/58">
              A rehearsal should not stall because the available score is in
              the wrong key or the useful line is buried in a full arrangement.
              The Transposify hymn tool rebuilds the edition from structured
              music data instead of stretching or relabeling a scan.
            </p>
            <Link
              href="/uses/hymn-transposer"
              className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-blue underline decoration-blue/25 underline-offset-4 transition hover:decoration-blue focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral focus-visible:ring-offset-4"
            >
              Open the live hymn transposer
              <span aria-hidden="true">→</span>
            </Link>
          </div>
        </div>

        <ol className="mt-12 grid gap-px overflow-hidden rounded-2xl border border-ink/10 bg-ink/10 sm:grid-cols-3">
          {capabilities.map((capability) => (
            <li key={capability.number} className="bg-paper p-6 sm:min-h-52 sm:p-7">
              <span className="font-mono text-[10px] tracking-[0.15em] text-coral">
                {capability.number}
              </span>
              <h3 className="mt-12 text-lg font-medium tracking-[-0.025em] text-ink">
                {capability.label}
              </h3>
              <p className="mt-3 max-w-xs text-sm leading-6 text-ink/50">
                {capability.copy}
              </p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
