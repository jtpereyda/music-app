"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export function SeoSyncButton() {
  const router = useRouter();
  const [state, setState] = useState<"idle" | "running" | "done" | "error">(
    "idle",
  );

  async function sync() {
    setState("running");
    try {
      const response = await fetch("/api/admin/seo/sync", { method: "POST" });
      if (!response.ok) throw new Error("Sync failed");
      setState("done");
      router.refresh();
    } catch {
      setState("error");
    }
  }

  const label =
    state === "running"
      ? "Syncing…"
      : state === "done"
        ? "Synced"
        : state === "error"
          ? "Retry sync"
          : "Sync now";

  return (
    <button
      type="button"
      onClick={sync}
      disabled={state === "running"}
      className="inline-flex min-h-14 items-center gap-2 rounded-2xl border border-white/10 bg-white/[0.055] px-5 text-sm font-semibold text-white/70 transition hover:-translate-y-0.5 hover:border-white/20 hover:bg-white/[0.08] hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/80 disabled:cursor-wait disabled:opacity-55"
    >
      <span
        className={`size-1.5 rounded-full ${
          state === "error"
            ? "bg-rose-300"
            : state === "running"
              ? "animate-pulse bg-amber-200"
              : "bg-emerald-300"
        }`}
      />
      {label}
    </button>
  );
}
