import Link from "next/link";

type AnalyticsPaginationProps = {
  page: number;
  pathname: string;
  query?: Record<string, string | undefined>;
  totalPages: number;
};

function pageHref({
  page,
  pathname,
  query,
}: Omit<AnalyticsPaginationProps, "totalPages">): string {
  const params = new URLSearchParams();

  for (const [key, value] of Object.entries(query ?? {})) {
    if (value) params.set(key, value);
  }
  if (page > 1) params.set("page", page.toString());

  const search = params.toString();
  return search ? `${pathname}?${search}` : pathname;
}

export function AnalyticsPagination({
  page,
  pathname,
  query,
  totalPages,
}: AnalyticsPaginationProps) {
  const previousPage = Math.max(1, page - 1);
  const nextPage = Math.min(totalPages, page + 1);

  return (
    <nav
      aria-label="Pagination"
      className="flex items-center justify-between gap-4 border-t border-white/[0.07] px-5 py-4 sm:px-6"
    >
      {page > 1 ? (
        <Link
          href={pageHref({ page: previousPage, pathname, query })}
          className="rounded-full border border-white/10 px-4 py-2 text-xs font-medium text-white/55 transition hover:border-white/20 hover:bg-white/[0.05] hover:text-white/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral"
        >
          ← Previous
        </Link>
      ) : (
        <span aria-hidden="true" />
      )}

      <span className="font-mono text-[9px] uppercase tracking-[0.13em] text-white/30">
        Page {page} of {totalPages}
      </span>

      {page < totalPages ? (
        <Link
          href={pageHref({ page: nextPage, pathname, query })}
          className="rounded-full border border-white/10 px-4 py-2 text-xs font-medium text-white/55 transition hover:border-white/20 hover:bg-white/[0.05] hover:text-white/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral"
        >
          Next →
        </Link>
      ) : (
        <span aria-hidden="true" />
      )}
    </nav>
  );
}
