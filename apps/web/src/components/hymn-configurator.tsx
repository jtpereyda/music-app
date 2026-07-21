"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { HymnSearch } from "@/components/hymn-search";
import { MobilePreviewStatus } from "@/components/mobile-preview-status";
import {
  PreviewSheet,
  type PreviewState,
} from "@/components/preview-sheet";
import {
  clefOptions,
  getKeyLabel,
  keys,
  octavePlacementOptions,
  outputOptions,
  pageSizes,
  type Clef,
  type EditionConfig,
  type Hymn,
  type OctavePlacement,
  type OutputPart,
  type PageSize,
  type TargetKey,
} from "@/lib/catalog";

interface HymnConfiguratorProps {
  initialHymn: Hymn;
  catalog: readonly Hymn[];
  renderApiConnected: boolean;
  showCatalogLink?: boolean;
  navigateOnHymnSelect?: boolean;
  initialEdition?: EditionConfig;
  urlBaseEdition?: EditionConfig;
}

interface RenderStatus {
  tone: "idle" | "success" | "error";
  message: string;
}

function artifactUrl(
  renderApiConnected: boolean,
  hymn: Hymn,
  artifact: "preview.svg" | "score.pdf",
  targetKey: TargetKey,
  outputPart: OutputPart,
  clef: Clef,
  octavePlacement: OctavePlacement,
  pageSize: PageSize,
): string | undefined {
  if (!renderApiConnected) {
    return undefined;
  }
  const query = new URLSearchParams({
    key: targetKey,
    line: outputPart,
    clef,
    octave: octavePlacement,
    page_size: pageSize,
  });
  return `/api/render/${encodeURIComponent(hymn.id)}/${artifact}?${query}`;
}

export function HymnConfigurator({
  initialHymn,
  catalog,
  renderApiConnected,
  showCatalogLink = false,
  navigateOnHymnSelect = false,
  initialEdition,
  urlBaseEdition,
}: HymnConfiguratorProps) {
  const router = useRouter();
  const [selectedHymn, setSelectedHymn] = useState(initialHymn);
  const [targetKey, setTargetKey] = useState<TargetKey>(
    initialEdition?.targetKey ?? initialHymn.originalKey,
  );
  const [outputPart, setOutputPart] = useState<OutputPart>(
    initialEdition?.outputPart ?? "satb",
  );
  const [clef, setClef] = useState<Clef>(
    initialEdition?.clef ?? "original",
  );
  const [singleLineOctavePlacement, setSingleLineOctavePlacement] =
    useState<OctavePlacement>(initialEdition?.octavePlacement ?? "auto");
  const [pageSize, setPageSize] = useState<PageSize>(
    initialEdition?.pageSize ?? "letter",
  );
  const [isRendering, setIsRendering] = useState(false);
  const [previewResult, setPreviewResult] = useState<{
    url: string;
    state: "ready" | "error";
  }>();
  const [status, setStatus] = useState<RenderStatus>({
    tone: "idle",
    message: renderApiConnected
      ? "Your edition is ready to configure."
      : "Preview mode is ready. Connect the render API to download.",
  });
  const isSatb = outputPart === "satb";
  const effectiveOctavePlacement: OctavePlacement = isSatb
    ? "original"
    : singleLineOctavePlacement;

  useEffect(() => {
    if (!urlBaseEdition || selectedHymn.id !== initialHymn.id) {
      return;
    }

    const params = new URLSearchParams(window.location.search);
    const values = [
      ["key", targetKey, urlBaseEdition.targetKey],
      ["line", outputPart, urlBaseEdition.outputPart],
      ["clef", clef, urlBaseEdition.clef],
      ["octave", effectiveOctavePlacement, urlBaseEdition.octavePlacement],
      ["page_size", pageSize, urlBaseEdition.pageSize],
    ] as const;

    for (const [name, value, baseValue] of values) {
      if (value === baseValue) {
        params.delete(name);
      } else {
        params.set(name, value);
      }
    }

    const query = params.toString();
    const nextUrl = `${window.location.pathname}${query ? `?${query}` : ""}${window.location.hash}`;
    window.history.replaceState(window.history.state, "", nextUrl);
  }, [
    clef,
    effectiveOctavePlacement,
    initialHymn.id,
    outputPart,
    pageSize,
    selectedHymn.id,
    targetKey,
    urlBaseEdition,
  ]);

  function selectHymn(hymn: Hymn) {
    if (navigateOnHymnSelect && hymn.id !== selectedHymn.id) {
      router.push(`/hymns/${hymn.slug}#make-an-edition`);
      return;
    }
    setSelectedHymn(hymn);
    setTargetKey(hymn.originalKey);
    setOutputPart("satb");
    setClef("original");
    setSingleLineOctavePlacement("auto");
    setStatus({
      tone: "idle",
      message: `Loaded ${hymn.title} in its source key.`,
    });
  }

  async function downloadPdf() {
    const url = artifactUrl(
      renderApiConnected,
      selectedHymn,
      "score.pdf",
      targetKey,
      outputPart,
      clef,
      effectiveOctavePlacement,
      pageSize,
    );
    if (!url) {
      setStatus({
        tone: "error",
        message: "Connect the render service to enable PDF downloads.",
      });
      return;
    }

    try {
      setIsRendering(true);
      setStatus({
        tone: "idle",
        message: "The render service is engraving your download.",
      });

      const response = await fetch(url);
      const contentType = response.headers.get("content-type") ?? "";
      if (!response.ok || !contentType.startsWith("application/pdf")) {
        throw new Error(`The render service returned HTTP ${response.status}.`);
      }

      const blobUrl = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download =
        `${selectedHymn.slug}-${targetKey}-${outputPart}-` +
        `${effectiveOctavePlacement}.pdf`;
      document.body.append(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(blobUrl), 1_000);

      setStatus({
        tone: "success",
        message: "Your print-ready PDF download has started.",
      });
    } catch {
      setStatus({
        tone: "error",
        message:
          "The PDF could not be rendered. Check the render service and try again.",
      });
    } finally {
      setIsRendering(false);
    }
  }

  const outputLabel =
    outputOptions.find((option) => option.value === outputPart)?.label ?? outputPart;
  const previewUrl = artifactUrl(
    renderApiConnected,
    selectedHymn,
    "preview.svg",
    targetKey,
    outputPart,
    clef,
    effectiveOctavePlacement,
    pageSize,
  );
  const previewState: PreviewState = !previewUrl
    ? "static"
    : previewResult?.url === previewUrl
      ? previewResult.state
      : "loading";

  return (
    <section
      id="make-an-edition"
      className="bg-[#edf0ef] px-4 py-8 sm:px-6 sm:py-12 lg:px-8 lg:py-16"
    >
      <div className="mx-auto w-full max-w-[1440px]">
        <div className="mb-6 flex flex-col gap-3 sm:mb-8 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-coral">
              Edition builder
            </p>
            <h2 className="mt-2 text-2xl font-medium tracking-[-0.035em] text-ink sm:text-3xl">
              Make the part fit the musician.
            </h2>
          </div>
          <div className="flex items-center gap-2 font-mono text-[9px] uppercase tracking-[0.12em] text-ink/45">
            <span
              className={`size-1.5 rounded-full ${
                renderApiConnected ? "bg-[#4f8e6b]" : "bg-amber-500"
              }`}
            />
            {renderApiConnected ? "Render API connected" : "Preview-only mode"}
          </div>
        </div>

        <div className="grid gap-5 xl:grid-cols-[390px_minmax(0,1fr)] xl:items-start">
          <aside className="rounded-[24px] border border-ink/10 bg-cream p-4 shadow-[0_14px_40px_rgba(29,39,50,0.08)] sm:p-6 xl:sticky xl:top-5">
            <div className="flex items-center justify-between border-b border-ink/10 pb-4">
              <div>
                <p className="text-sm font-semibold text-ink">Configure PDF</p>
                <p className="mt-0.5 text-xs text-ink/50">Six choices, one clean part.</p>
              </div>
              <span className="grid size-8 place-items-center rounded-full border border-ink/10 bg-white font-mono text-[10px] text-ink/50">
                01
              </span>
            </div>

            <div className="mt-5 space-y-6">
              <HymnSearch
                catalog={catalog}
                selectedHymn={selectedHymn}
                onSelect={selectHymn}
              />

              <div className="rounded-xl border border-ink/10 bg-white/65 px-3.5 py-3">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs text-ink/45">Tune</p>
                    <p className="mt-0.5 text-sm font-medium text-ink">
                      {selectedHymn.tuneName}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-ink/45">Source key</p>
                    <p className="mt-0.5 font-mono text-xs text-ink">
                      {getKeyLabel(selectedHymn.originalKey)}
                    </p>
                  </div>
                </div>
                {showCatalogLink ? (
                  <Link
                    href={`/hymns/${selectedHymn.slug}`}
                    className="mt-3 inline-flex text-xs font-medium text-blue underline decoration-blue/25 underline-offset-4 transition hover:decoration-blue"
                  >
                    View this hymn’s page
                  </Link>
                ) : null}
              </div>

              <div>
                <label
                  htmlFor="target-key"
                  className="mb-2 block text-xs font-medium uppercase tracking-[0.12em] text-ink/55"
                >
                  Target key
                </label>
                <div className="relative">
                  <select
                    id="target-key"
                    value={targetKey}
                    onChange={(event) =>
                      setTargetKey(event.target.value as TargetKey)
                    }
                    className="h-12 w-full appearance-none rounded-xl border border-ink/15 bg-white px-3.5 pr-10 text-sm font-medium text-ink shadow-sm outline-none transition focus:border-blue/60 focus:ring-4 focus:ring-blue/10"
                  >
                    {keys.map((key) => (
                      <option key={key.value} value={key.value}>
                        {key.label}
                      </option>
                    ))}
                  </select>
                  <svg
                    viewBox="0 0 20 20"
                    className="pointer-events-none absolute right-3.5 top-1/2 size-4 -translate-y-1/2 text-ink/45"
                    fill="currentColor"
                    aria-hidden="true"
                  >
                    <path d="m5.25 7.5 4.75 5 4.75-5H5.25Z" />
                  </svg>
                </div>
              </div>

              <fieldset>
                <legend className="mb-2 text-xs font-medium uppercase tracking-[0.12em] text-ink/55">
                  Music line
                </legend>
                <div className="grid grid-cols-5 gap-1 rounded-xl border border-ink/10 bg-ink/[0.045] p-1">
                  {outputOptions
                    .filter((option) =>
                      selectedHymn.availableLines.includes(option.value),
                    )
                    .map((option) => (
                      <label
                        key={option.value}
                        className={`relative cursor-pointer rounded-lg px-1 py-2.5 text-center text-xs font-medium outline-none transition focus-within:ring-2 focus-within:ring-blue focus-within:ring-offset-2 ${
                          outputPart === option.value
                            ? "bg-white text-ink shadow-sm"
                            : "text-ink/50 hover:text-ink"
                        }`}
                        title={option.label}
                      >
                        <input
                          type="radio"
                          name="output-part"
                          value={option.value}
                          checked={outputPart === option.value}
                          onChange={() => setOutputPart(option.value)}
                          className="sr-only"
                        />
                        <span aria-hidden="true">{option.shortLabel}</span>
                        <span className="sr-only">{option.label}</span>
                      </label>
                    ))}
                </div>
                <p className="mt-2 text-xs text-ink/45">
                  {outputLabel} will be included in the PDF.
                </p>
                {!selectedHymn.lyricsAvailableFor.includes(outputPart) ? (
                  <p className="mt-2 rounded-lg bg-amber-50 px-3 py-2 text-[11px] leading-4 text-amber-900">
                    This isolated voice is note-only in the source. Lyrics remain
                    available on the soprano line and full SATB score.
                  </p>
                ) : null}
              </fieldset>

              <div>
                <label
                  htmlFor="clef"
                  className="mb-2 block text-xs font-medium uppercase tracking-[0.12em] text-ink/55"
                >
                  Clef
                </label>
                <div className="relative">
                  <select
                    id="clef"
                    value={clef}
                    onChange={(event) => setClef(event.target.value as Clef)}
                    className="h-12 w-full appearance-none rounded-xl border border-ink/15 bg-white px-3.5 pr-10 text-sm font-medium text-ink shadow-sm outline-none transition focus:border-blue/60 focus:ring-4 focus:ring-blue/10"
                  >
                    {clefOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                  <svg
                    viewBox="0 0 20 20"
                    className="pointer-events-none absolute right-3.5 top-1/2 size-4 -translate-y-1/2 text-ink/45"
                    fill="currentColor"
                    aria-hidden="true"
                  >
                    <path d="m5.25 7.5 4.75 5 4.75-5H5.25Z" />
                  </svg>
                </div>
                <p className="mt-2 text-xs leading-5 text-ink/45">
                  Clef changes notation only. Pitches stay exactly where they belong.
                </p>
              </div>

              <fieldset
                disabled={isSatb}
                aria-describedby="pitch-register-help"
                className={isSatb ? "opacity-65" : undefined}
              >
                <legend className="mb-2 w-full">
                  <span className="flex items-center justify-between gap-3">
                    <span className="text-xs font-medium uppercase tracking-[0.12em] text-ink/55">
                      Pitch register
                    </span>
                    {isSatb ? (
                      <span className="font-mono text-[9px] uppercase tracking-[0.11em] text-ink/45">
                        SATB · Original
                      </span>
                    ) : null}
                  </span>
                </legend>
                <div className="grid grid-cols-2 gap-2">
                  {octavePlacementOptions.map((option) => (
                    <label
                      key={option.value}
                      className={`rounded-xl border px-3.5 py-3 outline-none transition ${
                        isSatb
                          ? "cursor-not-allowed border-ink/10 bg-white/55"
                          : "cursor-pointer focus-within:ring-2 focus-within:ring-blue focus-within:ring-offset-2"
                      } ${
                        effectiveOctavePlacement === option.value
                          ? "border-coral bg-coral/[0.06] shadow-[0_0_0_3px_rgba(231,104,77,0.08)]"
                          : "border-ink/10 bg-white hover:border-ink/25"
                      }`}
                    >
                      <input
                        type="radio"
                        name="octave-placement"
                        value={option.value}
                        checked={effectiveOctavePlacement === option.value}
                        onChange={() =>
                          setSingleLineOctavePlacement(option.value)
                        }
                        className="sr-only"
                      />
                      <span className="block text-xs font-semibold text-ink">
                        {option.label}
                      </span>
                      <span className="mt-1 block font-mono text-[9px] text-ink/40">
                        {option.detail}
                      </span>
                    </label>
                  ))}
                </div>
                <p
                  id="pitch-register-help"
                  className="mt-2 text-xs leading-5 text-ink/45"
                >
                  {isSatb
                    ? "Full SATB retains its original register and voicing. Your single-line choice is saved."
                    : "Register changes sounding pitch by octaves. Clef—including treble 8vb—only changes notation."}
                </p>
              </fieldset>

              <fieldset>
                <legend className="mb-2 text-xs font-medium uppercase tracking-[0.12em] text-ink/55">
                  Page size
                </legend>
                <div className="grid grid-cols-2 gap-2">
                  {pageSizes.map((option) => (
                    <label
                      key={option.value}
                      className={`cursor-pointer rounded-xl border px-3.5 py-3 outline-none transition focus-within:ring-2 focus-within:ring-blue focus-within:ring-offset-2 ${
                        pageSize === option.value
                          ? "border-coral bg-coral/[0.06] shadow-[0_0_0_3px_rgba(231,104,77,0.08)]"
                          : "border-ink/10 bg-white hover:border-ink/25"
                      }`}
                    >
                      <input
                        type="radio"
                        name="page-size"
                        value={option.value}
                        checked={pageSize === option.value}
                        onChange={() => setPageSize(option.value)}
                        className="sr-only"
                      />
                      <span className="block text-xs font-semibold text-ink">
                        {option.label}
                      </span>
                      <span className="mt-1 block font-mono text-[9px] text-ink/40">
                        {option.dimensions}
                      </span>
                    </label>
                  ))}
                </div>
              </fieldset>
            </div>

            <div className="mt-6 border-t border-ink/10 pt-5">
              <button
                type="button"
                onClick={downloadPdf}
                disabled={isRendering}
                className="group flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-coral px-5 text-sm font-semibold text-white shadow-[0_8px_20px_rgba(231,104,77,0.28)] outline-none transition hover:-translate-y-px hover:bg-[#d95f45] focus-visible:ring-2 focus-visible:ring-coral focus-visible:ring-offset-4 disabled:cursor-wait disabled:opacity-65 disabled:hover:translate-y-0"
              >
                {isRendering ? (
                  <span className="size-4 animate-spin rounded-full border-2 border-white/35 border-t-white" />
                ) : (
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    className="size-4 transition-transform group-hover:translate-y-0.5"
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
                {isRendering ? "Rendering PDF…" : "Download PDF"}
              </button>
              <p
                className={`mt-3 min-h-8 text-center text-xs leading-5 ${
                  status.tone === "error"
                    ? "text-red-700"
                    : status.tone === "success"
                      ? "text-[#34704f]"
                      : "text-ink/45"
                }`}
                role="status"
                aria-live="polite"
              >
                {status.message}
              </p>
            </div>
          </aside>

          <PreviewSheet
            hymn={selectedHymn}
            targetKey={targetKey}
            outputPart={outputPart}
            clef={clef}
            octavePlacement={effectiveOctavePlacement}
            pageSize={pageSize}
            isRendering={isRendering}
            previewUrl={previewUrl}
            previewState={previewState}
            onPreviewReady={(url) =>
              setPreviewResult({ url, state: "ready" })
            }
            onPreviewError={(url) =>
              setPreviewResult({ url, state: "error" })
            }
          />
        </div>
      </div>
      <MobilePreviewStatus
        enabled={Boolean(previewUrl)}
        state={previewState}
      />
    </section>
  );
}
