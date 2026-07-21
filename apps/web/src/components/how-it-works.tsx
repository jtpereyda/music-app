const steps = [
  {
    number: "01",
    title: "Find the hymn",
    copy: "Search the curated technical-preview catalog, not a folder of scanned PDFs.",
  },
  {
    number: "02",
    title: "Shape the edition",
    copy: "Choose the key, SATB line, clef, pitch register, and paper size that suit the player or singer.",
  },
  {
    number: "03",
    title: "Print and rehearse",
    copy: "Download a newly engraved PDF with crisp notation and practical page breaks.",
  },
] as const;

export function HowItWorks() {
  return (
    <section id="how-it-works" className="bg-ink px-5 py-16 text-cream sm:px-8 sm:py-24 lg:px-10">
      <div className="mx-auto w-full max-w-[1440px]">
        <div className="grid gap-10 lg:grid-cols-[0.7fr_1.3fr] lg:gap-20">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-coral">
              How the hymn tool works
            </p>
            <h2 className="mt-4 max-w-md text-4xl font-medium leading-[1.02] tracking-[-0.045em] sm:text-5xl">
              New notation, not a stretched scan.
            </h2>
            <p className="mt-6 max-w-md text-sm leading-6 text-cream/55">
              Each edition is rendered from structured music data. That means
              transposition changes the notes correctly, while choosing a clef
              simply changes how those pitches are represented.
            </p>
          </div>
          <ol className="grid gap-px overflow-hidden rounded-2xl border border-cream/10 bg-cream/10 sm:grid-cols-3">
            {steps.map((step) => (
              <li key={step.number} className="bg-ink p-6 sm:min-h-60 sm:p-7">
                <span className="font-mono text-[10px] tracking-[0.15em] text-coral">
                  {step.number}
                </span>
                <h3 className="mt-14 text-lg font-medium tracking-[-0.025em]">
                  {step.title}
                </h3>
                <p className="mt-3 text-sm leading-6 text-cream/50">{step.copy}</p>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}
