import Link from "next/link";

export default function NotFound() {
  return (
    <section className="grid min-h-[65vh] place-items-center bg-cream px-5 py-20 text-center">
      <div>
        <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-coral">
          404 · tacet
        </p>
        <h1 className="mt-4 text-4xl font-medium tracking-[-0.045em] text-ink">
          That page missed its entrance.
        </h1>
        <p className="mx-auto mt-4 max-w-md text-sm leading-6 text-ink/55">
          Return to Transposify, or open the live hymn tool and make an
          edition.
        </p>
        <div className="mt-7 flex flex-wrap justify-center gap-3">
          <Link
            href="/"
            className="inline-flex rounded-full border border-ink/15 bg-white/50 px-5 py-2.5 text-sm font-medium text-ink transition hover:-translate-y-px hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral focus-visible:ring-offset-2"
          >
            Transposify home
          </Link>
          <Link
            href="/uses/hymn-transposer"
            className="inline-flex rounded-full bg-ink px-5 py-2.5 text-sm font-medium text-cream transition hover:-translate-y-px hover:bg-ink/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral focus-visible:ring-offset-2"
          >
            Open hymn transposer
          </Link>
        </div>
      </div>
    </section>
  );
}
