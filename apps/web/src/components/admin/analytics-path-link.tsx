import { normalizeInternalPath } from "@/lib/internal-path";

export function AnalyticsPathLink({ path }: { path: string }) {
  const href = normalizeInternalPath(path);
  const className =
    "block truncate font-mono text-blue-200/70 underline decoration-blue-200/20 underline-offset-4 transition hover:text-blue-100 hover:decoration-blue-100/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-100/70";

  if (!href) {
    return (
      <span
        className="block truncate font-mono text-white/35"
        title="Link unavailable for an invalid stored path"
      >
        {path}
      </span>
    );
  }

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={className}
    >
      {path}
    </a>
  );
}
