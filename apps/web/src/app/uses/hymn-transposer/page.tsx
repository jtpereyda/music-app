import type { Metadata } from "next";
import { HowItWorks } from "@/components/how-it-works";
import { HymnConfigurator } from "@/components/hymn-configurator";
import { LandingIntro } from "@/components/landing-intro";
import { hymns } from "@/lib/catalog";
import {
  getCatalogSnapshot,
  renderApiConfigured,
} from "@/lib/catalog.server";

export const metadata: Metadata = {
  title: "Hymn Transposer — Sheet music in the key and clef you need",
  description:
    "Choose a hymn, target key, full SATB or individual voice line, clef, and page size, then preview and download a freshly engraved PDF.",
};

export const dynamic = "force-dynamic";

export default async function HymnTransposerPage() {
  const snapshot = await getCatalogSnapshot();
  const initialHymn =
    snapshot.hymns.find((hymn) => hymn.id === "amazing-grace") ??
    snapshot.hymns[0] ??
    hymns[0];

  return (
    <>
      <LandingIntro />
      <HymnConfigurator
        initialHymn={initialHymn}
        catalog={snapshot.hymns}
        renderApiConnected={renderApiConfigured()}
        showCatalogLink
      />
      <HowItWorks />
    </>
  );
}
