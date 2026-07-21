import Link from "next/link";

export function AppFooter() {
  return (
    <footer className="border-t border-ink/10 bg-cream">
      <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-4 px-5 py-8 text-sm text-ink/55 sm:flex-row sm:items-center sm:justify-between sm:px-8 lg:px-10">
        <p>Practical music tools for the player in front of you.</p>
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
          <Link className="transition-colors hover:text-ink" href="/">
            Transposify
          </Link>
          <Link
            className="transition-colors hover:text-ink"
            href="/hymns"
          >
            Hymns
          </Link>
          <Link
            className="transition-colors hover:text-ink"
            href="/hymns/sheet-music-for-instrumentalists"
          >
            For instrumentalists
          </Link>
          <Link
            className="transition-colors hover:text-ink"
            href="/uses/hymn-transposer"
          >
            Transposer
          </Link>
          <span className="font-mono text-[10px] uppercase tracking-[0.15em]">
            Technical preview
          </span>
        </div>
      </div>
    </footer>
  );
}
