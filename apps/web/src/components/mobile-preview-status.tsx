"use client";

import { useEffect, useState } from "react";
import type { PreviewState } from "@/components/preview-sheet";

interface MobilePreviewStatusProps {
  enabled: boolean;
  state: PreviewState;
}

const previewTargetId = "edition-preview";

export function MobilePreviewStatus({
  enabled,
  state,
}: MobilePreviewStatusProps) {
  const [isPreviewVisible, setIsPreviewVisible] = useState(false);

  useEffect(() => {
    const preview = document.getElementById(previewTargetId);
    if (!preview) {
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => setIsPreviewVisible(entry.isIntersecting),
      {
        rootMargin: "-10% 0px -20% 0px",
        threshold: 0.1,
      },
    );
    observer.observe(preview);

    return () => observer.disconnect();
  }, []);

  function showPreview() {
    const preview = document.getElementById(previewTargetId);
    const reduceMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    preview?.scrollIntoView({
      behavior: reduceMotion ? "auto" : "smooth",
      block: "start",
    });
  }

  if (
    !enabled ||
    isPreviewVisible ||
    (state !== "loading" && state !== "ready")
  ) {
    return null;
  }

  if (state === "loading") {
    return (
      <div
        className="fixed bottom-[calc(1rem+env(safe-area-inset-bottom))] right-4 z-50 flex items-center gap-2.5 rounded-full bg-ink px-4 py-3 text-sm font-semibold text-white shadow-[0_12px_35px_rgba(29,39,50,0.28)] xl:hidden"
        role="status"
        aria-live="polite"
      >
        <span
          className="size-4 animate-spin rounded-full border-2 border-white/30 border-t-white"
          aria-hidden="true"
        />
        Rendering preview…
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={showPreview}
      aria-controls={previewTargetId}
      className="group fixed bottom-[calc(1rem+env(safe-area-inset-bottom))] right-4 z-50 flex items-center gap-2.5 rounded-full bg-coral px-4 py-3 text-sm font-semibold text-white shadow-[0_12px_35px_rgba(231,104,77,0.34)] outline-none transition hover:-translate-y-0.5 hover:bg-[#d95f45] focus-visible:ring-2 focus-visible:ring-coral focus-visible:ring-offset-4 xl:hidden"
    >
      <span className="relative flex size-2" aria-hidden="true">
        <span className="absolute inline-flex size-full animate-ping rounded-full bg-white/70" />
        <span className="relative inline-flex size-2 rounded-full bg-white" />
      </span>
      Preview ready
      <svg
        viewBox="0 0 20 20"
        fill="none"
        className="size-4 transition-transform group-hover:translate-y-0.5"
        aria-hidden="true"
      >
        <path
          d="M10 4v11m0 0 4-4m-4 4-4-4"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </button>
  );
}
