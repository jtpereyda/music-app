"use client";

import type {
  CatalogItem,
  Clef,
  OctavePlacement,
  OutputPart,
  PageSize,
  TargetKey,
} from "@/lib/catalog";
import {
  clefOptions,
  getKeyLabel,
  getOctavePlacementLabel,
  outputOptions,
  pageSizes,
} from "@/lib/catalog";

export type PreviewState = "static" | "loading" | "ready" | "error";

interface PreviewSheetProps {
  hymn: CatalogItem;
  targetKey: TargetKey;
  outputPart: OutputPart;
  clef: Clef;
  octavePlacement: OctavePlacement;
  pageSize: PageSize;
  isRendering: boolean;
  previewUrl?: string;
  previewState: PreviewState;
  onDownload: () => void;
  onPreviewReady: (url: string) => void;
  onPreviewError: (url: string) => void;
}

const systemOffsets = [102, 185, 268, 351] as const;
const noteXPositions = [80, 120, 162, 208, 250, 300, 344, 390, 432, 474] as const;

export function PreviewSheet({
  hymn,
  targetKey,
  outputPart,
  clef,
  octavePlacement,
  pageSize,
  isRendering,
  previewUrl,
  previewState,
  onDownload,
  onPreviewReady,
  onPreviewError,
}: PreviewSheetProps) {
  const outputLabel =
    outputOptions.find((option) => option.value === outputPart)?.label ?? outputPart;
  const clefLabel =
    clefOptions.find((option) => option.value === clef)?.label ?? clef;
  const octavePlacementLabel = getOctavePlacementLabel(octavePlacement);
  const pageSizeLabel =
    pageSizes.find((option) => option.value === pageSize)?.label ?? pageSize;
  const scoreCredit =
    hymn.contentType === "art_song"
      ? [hymn.composer, hymn.collectionTitle].filter(Boolean).join(" · ")
      : [hymn.tuneName, hymn.meter].filter(Boolean).join(" · ");
  const creatorCredit =
    hymn.contentType === "art_song" ? hymn.lyricist : hymn.textAuthor;

  return (
    <section
      id="edition-preview"
      className="relative flex min-h-[560px] scroll-mt-4 flex-1 flex-col overflow-hidden rounded-[28px] border border-ink/10 bg-[#dfe4e4] shadow-[0_24px_65px_rgba(29,39,50,0.12)] lg:min-h-[720px]"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-ink/10 bg-white/70 px-4 py-3 backdrop-blur sm:px-5">
        <div className="flex flex-wrap items-center gap-2.5">
          <span
            className={`size-2 rounded-full ${
              isRendering ? "animate-pulse bg-coral" : "bg-[#4f8e6b]"
            }`}
          />
          <span className="text-xs font-medium text-ink">
            {isRendering
              ? "Preparing your PDF…"
              : previewState === "ready"
                ? "Live engraved preview"
                : previewState === "loading"
                  ? "Engraving live preview…"
                  : previewState === "error"
                    ? "Preview unavailable"
                    : "Layout preview"}
          </span>
          <button
            type="button"
            onClick={onDownload}
            disabled={isRendering}
            className="group inline-flex h-8 items-center gap-1.5 rounded-full bg-coral px-3 text-[11px] font-semibold text-white shadow-[0_5px_14px_rgba(231,104,77,0.24)] outline-none transition hover:-translate-y-px hover:bg-[#d95f45] focus-visible:ring-2 focus-visible:ring-coral focus-visible:ring-offset-2 disabled:cursor-wait disabled:opacity-65 disabled:hover:translate-y-0"
          >
            {isRendering ? (
              <span className="size-3.5 animate-spin rounded-full border-2 border-white/35 border-t-white" />
            ) : (
              <svg
                viewBox="0 0 24 24"
                fill="none"
                className="size-3.5 transition-transform group-hover:translate-y-0.5"
                aria-hidden="true"
              >
                <path
                  d="M12 3v12m0 0 4-4m-4 4-4-4M5 19h14"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            )}
            {isRendering ? "Rendering…" : "Download PDF"}
          </button>
          <span className="hidden text-xs text-ink/40 sm:inline">
            {previewState === "ready"
              ? " · generated from canonical MusicXML"
              : previewState === "error"
                ? " · showing the static layout fallback"
                : previewState === "loading"
                  ? " · requesting a canonical MusicXML render"
                  : " · connect the render API for live notation"}
          </span>
        </div>
        <span className="rounded-full border border-ink/10 bg-white px-2.5 py-1 font-mono text-[9px] uppercase tracking-[0.12em] text-ink/50">
          {pageSizeLabel}
        </span>
      </div>

      <div className="preview-grid relative grid flex-1 place-items-center overflow-hidden px-4 py-8 sm:px-8 sm:py-10 lg:px-12">
        <div
          className={`relative w-full max-w-[620px] overflow-hidden bg-paper px-[7%] pb-[9%] pt-[8%] shadow-[0_22px_65px_rgba(29,39,50,0.18)] transition-all duration-300 ${
            pageSize === "a4" ? "aspect-[210/297]" : "aspect-[8.5/11]"
          }`}
        >
          {previewUrl ? (
            // The static mock remains beneath the image so a failed response
            // never replaces the score with raw API error text.
            // eslint-disable-next-line @next/next/no-img-element
            <img
              key={previewUrl}
              src={previewUrl}
              alt={`Engraved sheet music preview of ${hymn.title}`}
              className={`absolute inset-0 z-10 size-full bg-white object-contain transition-opacity ${
                previewState === "ready" ? "opacity-100" : "opacity-0"
              }`}
              onLoad={() => onPreviewReady(previewUrl)}
              onError={() => onPreviewError(previewUrl)}
            />
          ) : null}
          <div className="absolute left-0 top-0 h-1 w-full bg-coral" />
          <p className="text-center font-mono text-[7px] uppercase tracking-[0.2em] text-ink/40 sm:text-[9px]">
            {scoreCredit}
          </p>
          <h2 className="mx-auto mt-2 max-w-[90%] text-center text-[clamp(1rem,3vw,1.7rem)] font-medium tracking-[-0.035em] text-ink">
            {hymn.title}
          </h2>
          <div className="mt-2 flex items-center justify-center gap-2 font-mono text-[7px] uppercase tracking-[0.11em] text-ink/45 sm:text-[9px]">
            <span>{getKeyLabel(targetKey)}</span>
            <span>·</span>
            <span>{outputLabel}</span>
            <span>·</span>
            <span>{clefLabel} clef</span>
            <span>·</span>
            <span>{octavePlacementLabel} register</span>
          </div>

          <svg
            viewBox="0 0 560 445"
            className="mt-[3%] w-full text-ink"
            role="img"
            aria-label={`Static layout preview for ${hymn.title}, ${outputLabel}, ${getKeyLabel(targetKey)}, ${octavePlacementLabel} register`}
          >
            {systemOffsets.map((offset, systemIndex) => (
              <g key={offset}>
                {[0, 9, 18, 27, 36].map((lineOffset) => (
                  <line
                    key={lineOffset}
                    x1="45"
                    x2="520"
                    y1={offset + lineOffset}
                    y2={offset + lineOffset}
                    stroke="currentColor"
                    strokeWidth="1"
                    opacity="0.55"
                  />
                ))}
                <text
                  x="50"
                  y={offset + 32}
                  fontFamily="serif"
                  fontSize="45"
                  fill="currentColor"
                  opacity="0.75"
                >
                  {clef === "bass" ? "𝄢" : clef === "alto" || clef === "tenor" ? "𝄡" : "𝄞"}
                </text>
                {noteXPositions.map((x, noteIndex) => {
                  const pattern = [24, 15, 6, 18, 27, 9, 21, 12, 3, 15] as const;
                  const y = offset + pattern[(noteIndex + systemIndex * 2) % pattern.length];
                  return (
                    <g key={x}>
                      <ellipse
                        cx={x}
                        cy={y}
                        rx="5.6"
                        ry="4.1"
                        fill="currentColor"
                        opacity={systemIndex === 0 && noteIndex === 6 ? "0.85" : "0.62"}
                        transform={`rotate(-15 ${x} ${y})`}
                      />
                      <line
                        x1={x + 5}
                        x2={x + 5}
                        y1={y}
                        y2={y - 24}
                        stroke="currentColor"
                        strokeWidth="1.4"
                        opacity="0.62"
                      />
                    </g>
                  );
                })}
                <text
                  x="82"
                  y={offset + 59}
                  fontFamily="var(--font-geist-sans)"
                  fontSize="8.5"
                  letterSpacing="0.7"
                  fill="currentColor"
                  opacity="0.42"
                >
                  {systemIndex === 0
                    ? "A  score  prepared  in  just  the  right  key"
                    : "Clear  notation  for  practice  and  performance"}
                </text>
              </g>
            ))}
          </svg>

          <div className="absolute bottom-[3.5%] left-[7%] right-[7%] flex items-center justify-between border-t border-ink/10 pt-2 font-mono text-[6px] uppercase tracking-[0.12em] text-ink/35 sm:text-[8px]">
            <span>{creatorCredit}</span>
            <span>Preview · not final engraving</span>
          </div>
        </div>
      </div>
    </section>
  );
}
