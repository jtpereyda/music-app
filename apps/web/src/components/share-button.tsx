"use client";

import { useState } from "react";

interface ShareButtonProps {
  title: string;
  text: string;
}

type ShareFeedback = "idle" | "shared" | "copied" | "error";

export function ShareButton({ title, text }: ShareButtonProps) {
  const [feedback, setFeedback] = useState<ShareFeedback>("idle");

  async function sharePage() {
    const url = window.location.href;
    const shareData = { title, text, url };

    if (
      typeof navigator.share === "function" &&
      (!navigator.canShare || navigator.canShare(shareData))
    ) {
      try {
        await navigator.share(shareData);
        setFeedback("shared");
        window.setTimeout(() => setFeedback("idle"), 2_000);
        return;
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
      }
    }

    try {
      await navigator.clipboard.writeText(url);
      setFeedback("copied");
    } catch {
      setFeedback("error");
    }
    window.setTimeout(() => setFeedback("idle"), 2_000);
  }

  const label =
    feedback === "shared"
      ? "Shared"
      : feedback === "copied"
        ? "Link copied"
        : feedback === "error"
          ? "Couldn’t share"
          : "Share";

  return (
    <button
      type="button"
      onClick={sharePage}
      className="group inline-flex items-center gap-2 rounded-full border border-ink/15 bg-white/45 px-5 py-2.5 text-sm font-semibold text-ink outline-none transition hover:-translate-y-px hover:border-ink/30 hover:bg-white focus-visible:ring-2 focus-visible:ring-coral focus-visible:ring-offset-4"
    >
      <span
        className="transition-transform group-hover:-translate-y-0.5"
        aria-hidden="true"
      >
        <svg viewBox="0 0 24 24" fill="none" className="size-4">
          <path
            d="M12 16V4m0 0 4 4m-4-4L8 8M5 13v5a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-5"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </span>
      <span aria-live="polite">{label}</span>
    </button>
  );
}
