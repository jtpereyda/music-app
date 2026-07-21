import Link from "next/link";

export function AppHeader() {
  return (
    <header className="border-b border-ink/10 bg-cream/90 backdrop-blur-xl">
      <div className="mx-auto flex h-16 w-full max-w-[1440px] items-center justify-between px-5 sm:px-8 lg:px-10">
        <Link
          href="/"
          className="group flex items-center gap-3 rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-coral focus-visible:ring-offset-4 focus-visible:ring-offset-cream"
          aria-label="Transposify home"
        >
          <span className="grid size-9 place-items-center rounded-full bg-ink text-cream shadow-[0_4px_14px_rgba(29,39,50,0.18)] transition-transform group-hover:-rotate-3">
            <svg
              viewBox="0 0 24 24"
              className="size-[18px]"
              fill="none"
              aria-hidden="true"
            >
              <path
                d="M8.5 5.5v11.25a2.75 2.75 0 1 1-1-2.12V8l9-2v8.75a2.75 2.75 0 1 1-1-2.12V3.5l-7 2Z"
                fill="currentColor"
              />
            </svg>
          </span>
          <span>
            <span className="block text-[15px] font-semibold tracking-[-0.02em] text-ink">
              Transposify
            </span>
            <span className="hidden font-mono text-[9px] uppercase tracking-[0.18em] text-ink/50 sm:block">
              practical music tools
            </span>
          </span>
        </Link>

        <nav className="flex items-center gap-1 text-sm" aria-label="Main navigation">
          <Link
            href="/hymns"
            className="hidden rounded-full px-4 py-2 text-ink/65 transition-colors hover:bg-white/65 hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral sm:block"
          >
            Hymns
          </Link>
          <Link
            href="/hymns/sheet-music-for-instrumentalists"
            className="hidden rounded-full px-4 py-2 text-ink/65 transition-colors hover:bg-white/65 hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral lg:block"
          >
            For instrumentalists
          </Link>
          <Link
            href="/uses/hymn-transposer#make-an-edition"
            className="rounded-full bg-ink px-4 py-2 font-medium text-cream shadow-sm transition hover:-translate-y-px hover:bg-ink/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral focus-visible:ring-offset-2"
          >
            Try the live tool
          </Link>
        </nav>
      </div>
    </header>
  );
}
