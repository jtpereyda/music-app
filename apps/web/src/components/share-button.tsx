"use client";

import { useState } from "react";

interface ShareButtonProps {
  title: string;
  text: string;
  variant?: "primary" | "toolbar";
}

type ShareFeedback = "idle" | "shared" | "copied" | "error";

export function ShareButton({
  title,
  text,
  variant = "toolbar",
}: ShareButtonProps) {
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
  const isSuccess = feedback === "shared" || feedback === "copied";
  const className =
    variant === "primary"
      ? "group inline-grid size-12 shrink-0 place-items-center rounded-xl border border-ink/10 bg-white text-ink/60 shadow-sm outline-none transition hover:-translate-y-px hover:border-ink/25 hover:text-ink focus-visible:ring-2 focus-visible:ring-coral focus-visible:ring-offset-4 sm:inline-flex sm:w-auto sm:gap-2 sm:px-4 sm:text-sm sm:font-semibold"
      : "group inline-grid size-8 shrink-0 place-items-center rounded-full border border-ink/10 bg-white text-ink/60 outline-none transition hover:-translate-y-px hover:border-ink/25 hover:text-ink focus-visible:ring-2 focus-visible:ring-coral focus-visible:ring-offset-2 sm:inline-flex sm:w-auto sm:gap-1.5 sm:px-3 sm:text-[11px] sm:font-semibold";

  return (
    <button
      type="button"
      onClick={sharePage}
      title={label}
      className={className}
    >
      <span
        className="transition-transform group-hover:-translate-y-0.5"
        aria-hidden="true"
      >
        <svg viewBox="0 0 24 24" fill="none" className="size-4">
          {isSuccess ? (
            <path
              d="m6.5 12.5 3.5 3.5 7.5-8"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          ) : feedback === "error" ? (
            <path
              d="M12 7v6m0 4h.01"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
            />
          ) : (
            <path
              d="M12 16V4m0 0 4 4m-4-4L8 8M5 13v5a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-5"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )}
        </svg>
      </span>
      <span className="sr-only sm:not-sr-only" aria-live="polite">
        {label}
      </span>
    </button>
  );
}
