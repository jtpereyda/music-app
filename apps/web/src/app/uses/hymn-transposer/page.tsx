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
  title: "Free Sheet Music Transposer for Hymns",
  description:
    "Transpose sheet music online from Transposify’s hymn catalog. Choose a key, full SATB or one voice, clef, range, and page size, then download a fresh PDF.",
  alternates: { canonical: "/uses/hymn-transposer" },
  openGraph: {
    title: "Free Sheet Music Transposer for Hymns",
    description:
      "Choose a catalog hymn, key, voice, clef, and page size, then preview and download a newly engraved PDF.",
    type: "website",
    url: "/uses/hymn-transposer",
  },
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
