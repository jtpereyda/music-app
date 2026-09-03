import Link from "next/link";

type AnalyticsNavigationProps = {
  active: "overview" | "pages" | "sessions";
};

const destinations = [
  {
    href: "/admin#first-party-analytics",
    key: "overview",
    label: "Overview",
  },
  {
    href: "/admin/analytics/sessions",
    key: "sessions",
    label: "Sessions",
  },
  {
    href: "/admin/analytics/pages",
    key: "pages",
    label: "Pages",
  },
] as const;

export function AnalyticsNavigation({ active }: AnalyticsNavigationProps) {
  return (
    <nav
      aria-label="First-party analytics"
      className="flex w-fit rounded-full border border-white/10 bg-white/[0.035] p-1"
    >
      {destinations.map((destination) => (
        <Link
          key={destination.key}
          href={destination.href}
          aria-current={destination.key === active ? "page" : undefined}
          className={`rounded-full px-4 py-2 text-xs font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral ${
            destination.key === active
              ? "bg-white text-[#151d23]"
              : "text-white/45 hover:bg-white/[0.06] hover:text-white/75"
          }`}
        >
          {destination.label}
        </Link>
      ))}
    </nav>
  );
}
