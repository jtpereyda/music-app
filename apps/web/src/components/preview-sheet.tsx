"use client";

import type {
  Clef,
  Hymn,
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
  hymn: Hymn;
  targetKey: TargetKey;
  outputPart: OutputPart;
  clef: Clef;
  octavePlacement: OctavePlacement;
  pageSize: PageSize;
  isRendering: boolean;
  previewUrl?: string;
  previewState: PreviewState;
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

  return (
    <section
      id="edition-preview"
      className="relative flex min-h-[560px] scroll-mt-4 flex-1 flex-col overflow-hidden rounded-[28px] border border-ink/10 bg-[#dfe4e4] shadow-[0_24px_65px_rgba(29,39,50,0.12)] lg:min-h-[720px]"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-ink/10 bg-white/70 px-4 py-3 backdrop-blur sm:px-5">
        <div className="flex items-center gap-2.5">
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
            {hymn.tuneName} · {hymn.meter}
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
                    ? "O  for  a  song  prepared  in  just  the  right  key"
                    : "A  clear  part  to  place  before  every  singer"}
                </text>
              </g>
            ))}
          </svg>

          <div className="absolute bottom-[3.5%] left-[7%] right-[7%] flex items-center justify-between border-t border-ink/10 pt-2 font-mono text-[6px] uppercase tracking-[0.12em] text-ink/35 sm:text-[8px]">
            <span>{hymn.textAuthor}</span>
            <span>Preview · not final engraving</span>
          </div>
        </div>
      </div>
    </section>
  );
}
