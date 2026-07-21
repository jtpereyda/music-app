export function LandingIntro() {
  return (
    <section className="relative overflow-hidden border-b border-ink/10 bg-cream">
      <div className="pointer-events-none absolute -left-28 top-14 size-72 rounded-full bg-coral/10 blur-3xl" />
      <div className="pointer-events-none absolute -right-24 -top-20 size-80 rounded-full bg-blue/10 blur-3xl" />
      <div className="mx-auto grid w-full max-w-[1440px] gap-8 px-5 pb-12 pt-14 sm:px-8 sm:pb-16 sm:pt-20 lg:grid-cols-[1fr_auto] lg:items-end lg:px-10">
        <div className="max-w-4xl">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-ink/10 bg-white/70 px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.15em] text-ink/65 shadow-sm">
            <span className="size-1.5 rounded-full bg-coral" />
            Transposify flagship · free beta
          </div>
          <h1 className="max-w-4xl text-balance text-[clamp(2.8rem,7vw,6.7rem)] font-medium leading-[0.92] tracking-[-0.065em] text-ink">
            The hymn you need,{" "}
            <span className="text-coral">in the key you need.</span>
          </h1>
          <p className="mt-7 max-w-2xl text-pretty text-base leading-7 text-ink/62 sm:text-lg sm:leading-8">
            Choose a traditional hymn from the fixed catalog, transpose it,
            select any SATB line and clef, then download a clean edition built
            for the musicians in front of you. Arbitrary score uploads are not
            supported yet.
          </p>
        </div>
        <div className="hidden pb-2 lg:block" aria-hidden="true">
          <div className="relative h-32 w-56 -rotate-2 rounded-sm bg-paper p-5 shadow-[0_18px_45px_rgba(29,39,50,0.14)]">
            <div className="mb-5 h-px bg-ink/15" />
            <div className="music-staff opacity-40" />
            <div className="music-staff mt-5 opacity-40" />
            <span className="absolute left-12 top-[58px] size-2 -rotate-12 rounded-full bg-ink/50" />
            <span className="absolute left-24 top-[51px] size-2 -rotate-12 rounded-full bg-ink/50" />
            <span className="absolute right-14 top-[64px] size-2 -rotate-12 rounded-full bg-coral/70" />
          </div>
        </div>
      </div>
    </section>
  );
}
