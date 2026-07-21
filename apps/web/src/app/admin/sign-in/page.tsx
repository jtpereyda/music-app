import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { auth, signIn } from "@/auth";
import {
  AUTHORIZED_ADMIN_EMAIL,
  isAuthorizedAdmin,
} from "@/lib/admin-auth";

export const metadata: Metadata = {
  title: "Admin sign in",
  robots: { index: false, follow: false },
};

type SignInPageProps = {
  searchParams: Promise<{
    callbackUrl?: string | string[];
    error?: string | string[];
  }>;
};

function safeAdminCallback(value: string | string[] | undefined): string {
  const callback = Array.isArray(value) ? value[0] : value;
  return callback?.startsWith("/admin") && !callback.startsWith("//")
    ? callback
    : "/admin";
}

export default async function AdminSignInPage({
  searchParams,
}: SignInPageProps) {
  const [session, params] = await Promise.all([auth(), searchParams]);
  if (isAuthorizedAdmin(session?.user?.email)) redirect("/admin");

  const callbackUrl = safeAdminCallback(params.callbackUrl);
  const hasError = Boolean(params.error);

  return (
    <section className="relative grid min-h-[calc(100vh-8rem)] place-items-center overflow-hidden bg-[#10171d] px-5 py-16 text-[#eef0eb]">
      <div className="pointer-events-none absolute -left-28 top-12 size-80 rounded-full bg-blue/20 blur-3xl" />
      <div className="pointer-events-none absolute -right-20 bottom-6 size-72 rounded-full bg-coral/15 blur-3xl" />

      <div className="relative w-full max-w-md rounded-[2rem] border border-white/10 bg-white/[0.045] p-7 shadow-[0_30px_100px_rgba(0,0,0,0.32)] backdrop-blur-xl sm:p-9">
        <div className="grid size-11 place-items-center rounded-2xl bg-coral text-white shadow-[0_8px_28px_rgba(231,104,77,0.28)]">
          <svg
            viewBox="0 0 24 24"
            className="size-5"
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
        </div>

        <p className="mt-8 font-mono text-[9px] uppercase tracking-[0.18em] text-coral">
          Private workspace
        </p>
        <h1 className="mt-3 text-4xl font-medium tracking-[-0.055em]">
          Search control room
        </h1>
        <p className="mt-4 text-sm leading-6 text-white/50">
          Sign in to review Transposify’s target keywords, research coverage,
          and Ahrefs shortcuts.
        </p>

        {hasError ? (
          <div
            role="alert"
            className="mt-6 rounded-2xl border border-coral/25 bg-coral/10 px-4 py-3 text-sm leading-5 text-[#ffc9bd]"
          >
            That Google account is not authorized for this dashboard.
          </div>
        ) : null}

        <form
          className="mt-8"
          action={async () => {
            "use server";
            await signIn("google", { redirectTo: callbackUrl });
          }}
        >
          <button
            type="submit"
            className="flex w-full items-center justify-center gap-3 rounded-full bg-white px-5 py-3 text-sm font-semibold text-[#182127] shadow-sm transition hover:-translate-y-0.5 hover:bg-[#f7f7f3] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-coral focus-visible:ring-offset-4 focus-visible:ring-offset-[#10171d]"
          >
            <svg viewBox="0 0 24 24" className="size-4" aria-hidden="true">
              <path
                fill="#4285F4"
                d="M21.6 12.23c0-.71-.06-1.4-.18-2.07H12v3.92h5.38a4.6 4.6 0 0 1-2 3.02v2.54h3.24c1.9-1.75 2.98-4.32 2.98-7.41Z"
              />
              <path
                fill="#34A853"
                d="M12 22c2.7 0 4.98-.9 6.63-2.43l-3.24-2.54c-.9.6-2.05.96-3.39.96-2.61 0-4.82-1.76-5.61-4.13H3.04v2.62A10 10 0 0 0 12 22Z"
              />
              <path
                fill="#FBBC05"
                d="M6.39 13.86A6 6 0 0 1 6.08 12c0-.65.11-1.28.31-1.86V7.52H3.04A10 10 0 0 0 2 12c0 1.61.39 3.14 1.04 4.48l3.35-2.62Z"
              />
              <path
                fill="#EA4335"
                d="M12 6.01c1.47 0 2.79.5 3.83 1.5L18.7 4.64A9.64 9.64 0 0 0 12 2a10 10 0 0 0-8.96 5.52l3.35 2.62C7.18 7.77 9.39 6.01 12 6.01Z"
              />
            </svg>
            Continue with Google
          </button>
        </form>

        <p className="mt-5 text-center font-mono text-[9px] leading-4 text-white/30">
          Access restricted to {AUTHORIZED_ADMIN_EMAIL}
        </p>
      </div>
    </section>
  );
}
