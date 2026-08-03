import type { Metadata } from "next";
import { HowItWorks } from "@/components/how-it-works";
import { HymnConfigurator } from "@/components/hymn-configurator";
import { LandingIntro } from "@/components/landing-intro";
import { catalogItems } from "@/lib/catalog";
import {
  getCatalogSnapshot,
  renderApiConfigured,
} from "@/lib/catalog.server";
import { withSiteName } from "@/lib/site";

const pageTitle = "Free Sheet Music Transposer";

export const metadata: Metadata = {
  title: pageTitle,
  description:
    "Transpose hymns and classical art songs online. Choose a score and key, preview the result, and download a freshly engraved PDF.",
  alternates: { canonical: "/uses/hymn-transposer" },
  openGraph: {
    title: withSiteName(pageTitle),
    description:
      "Choose a hymn or art song, set the key and page size, then preview and download a newly engraved PDF.",
    type: "website",
    url: "/uses/hymn-transposer",
  },
};

export const dynamic = "force-dynamic";

export default async function HymnTransposerPage() {
  const snapshot = await getCatalogSnapshot();
  const initialHymn =
    snapshot.items.find((item) => item.id === "amazing-grace") ??
    snapshot.items[0] ??
    catalogItems[0];

  return (
    <>
      <LandingIntro />
      <HymnConfigurator
        initialHymn={initialHymn}
        catalog={snapshot.items}
        renderApiConnected={renderApiConfigured()}
        showCatalogLink
      />
      <HowItWorks />
    </>
  );
}
