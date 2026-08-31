import type { Metadata, Viewport } from "next";
import { GoogleAnalytics } from "@next/third-parties/google";
import { GeistMono } from "geist/font/mono";
import { GeistSans } from "geist/font/sans";
import {
  defaultSiteTitle,
  getSiteUrl,
  indexingEnabled,
  siteName,
  siteTitleTemplate,
} from "@/lib/site";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: getSiteUrl(),
  title: {
    default: defaultSiteTitle,
    template: siteTitleTemplate,
  },
  description:
    "Turn structured hymns and classical art songs into practical editions in the key and page size your musicians need.",
  applicationName: siteName,
  category: "music",
  keywords: [
    "music transposition",
    "sheet music transposer",
    "hymn sheet music",
    "hymn transposer",
    "art song transposer",
    "lieder sheet music",
    "SATB",
    "bass clef hymn",
  ],
  robots: {
    index: indexingEnabled(),
    follow: indexingEnabled(),
  },
  openGraph: {
    type: "website",
    siteName,
    title: defaultSiteTitle,
    description:
      "Printable hymns and classical art songs in the key your musician needs.",
    url: "/",
  },
};

export const viewport: Viewport = {
  colorScheme: "light",
  themeColor: "#f6f1e7",
};

const GA_MEASUREMENT_ID_PATTERN = /^G-[A-Z0-9]+$/;

function googleAnalyticsMeasurementId(): string | null {
  const measurementId =
    process.env.NEXT_PUBLIC_GOOGLE_ANALYTICS_MEASUREMENT_ID?.trim();

  if (!measurementId) return null;

  if (!GA_MEASUREMENT_ID_PATTERN.test(measurementId)) {
    throw new Error(
      "NEXT_PUBLIC_GOOGLE_ANALYTICS_MEASUREMENT_ID must be a GA4 measurement ID such as G-XXXXXXXXXX.",
    );
  }

  return measurementId;
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const measurementId = googleAnalyticsMeasurementId();

  return (
    <html lang="en" className={`${GeistSans.variable} ${GeistMono.variable}`}>
      <body className="min-h-screen antialiased">{children}</body>
      {measurementId ? <GoogleAnalytics gaId={measurementId} /> : null}
    </html>
  );
}
