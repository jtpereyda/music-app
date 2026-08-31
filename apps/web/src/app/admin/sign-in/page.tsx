import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { auth, signIn } from "@/auth";
import { isAuthorizedAdmin } from "@/lib/admin-auth";

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
    <main className="grid min-h-screen place-items-center bg-[#10171d] px-5 py-16 text-[#eef0eb]">
      <div className="w-full max-w-xs">
        <h1 className="text-xl font-medium tracking-[-0.03em]">Admin</h1>
        <p className="mt-2 text-sm text-white/45">Sign in to continue.</p>

        {hasError ? (
          <div
            role="alert"
            className="mt-6 rounded-lg border border-white/10 bg-white/5 px-4 py-3 text-sm leading-5 text-white/70"
          >
            That account is not authorized.
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
            className="flex w-full items-center justify-center gap-3 rounded-lg bg-white px-5 py-3 text-sm font-medium text-[#182127] transition hover:bg-white/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/70 focus-visible:ring-offset-4 focus-visible:ring-offset-[#10171d]"
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
            Sign in with Google
          </button>
        </form>
      </div>
    </main>
  );
}
