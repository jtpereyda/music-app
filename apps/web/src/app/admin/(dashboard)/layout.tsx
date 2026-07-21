import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { auth, signOut } from "@/auth";
import { isAuthorizedAdmin } from "@/lib/admin-auth";

export const metadata: Metadata = {
  title: "SEO dashboard",
  robots: { index: false, follow: false },
};

export default async function AdminDashboardLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const session = await auth();

  if (!isAuthorizedAdmin(session?.user?.email)) {
    redirect("/admin/sign-in?callbackUrl=/admin");
  }

  return (
    <div className="min-h-[calc(100vh-8rem)] bg-[#10171d] text-[#eef0eb]">
      <header className="border-b border-white/10 bg-[#10171d]/95 px-5 backdrop-blur-xl sm:px-8 lg:px-10">
        <div className="mx-auto flex min-h-16 w-full max-w-[1440px] items-center justify-between gap-5 py-3">
          <div className="flex min-w-0 items-center gap-3">
            <Link
              href="/admin"
              className="grid size-9 shrink-0 place-items-center rounded-xl bg-coral text-white outline-none transition hover:-rotate-2 focus-visible:ring-2 focus-visible:ring-white/80"
              aria-label="SEO dashboard home"
            >
              <svg
                viewBox="0 0 24 24"
                className="size-[18px]"
                fill="none"
                aria-hidden="true"
              >
                <path
                  d="M5 18.5V13m7 5.5V5m7 13.5V9"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              </svg>
            </Link>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold tracking-[-0.02em]">
                Search control room
              </p>
              <p className="font-mono text-[9px] uppercase tracking-[0.16em] text-white/40">
                Transposify · admin
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden text-right sm:block">
              <p className="text-xs font-medium text-white/70">
                {session?.user?.email}
              </p>
              <p className="font-mono text-[8px] uppercase tracking-[0.14em] text-emerald-300/70">
                Authorized
              </p>
            </div>
            <div
              className="grid size-8 place-items-center rounded-full border border-white/10 bg-white/5 text-xs font-semibold text-white/65"
              aria-hidden="true"
            >
              JP
            </div>
            <form
              action={async () => {
                "use server";
                await signOut({ redirectTo: "/admin/sign-in" });
              }}
            >
              <button
                type="submit"
                className="rounded-full border border-white/10 px-3 py-1.5 text-xs font-medium text-white/55 transition hover:border-white/20 hover:bg-white/5 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral"
              >
                Sign out
              </button>
            </form>
          </div>
        </div>
      </header>
      {children}
    </div>
  );
}
