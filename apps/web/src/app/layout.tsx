import type { Metadata, Viewport } from "next";
import { GeistMono } from "geist/font/mono";
import { GeistSans } from "geist/font/sans";
import { AppFooter } from "@/components/app-footer";
import { AppHeader } from "@/components/app-header";
import { getSiteUrl, indexingEnabled } from "@/lib/site";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: getSiteUrl(),
  title: {
    default: "Transposify — Practical music, shaped to fit",
    template: "%s · Transposify",
  },
  description:
    "Turn structured scores into practical editions. Try Transposify’s live hymn tool to choose a key, SATB line, clef, and print-ready page size.",
  applicationName: "Transposify",
  category: "music",
  keywords: [
    "music transposition",
    "sheet music transposer",
    "hymn sheet music",
    "hymn transposer",
    "SATB",
    "bass clef hymn",
  ],
  robots: {
    index: indexingEnabled(),
    follow: indexingEnabled(),
  },
  openGraph: {
    type: "website",
    siteName: "Transposify",
    title: "Transposify — Practical music, shaped to fit",
    description:
      "Printable hymn sheet music in the key, voice, and clef your musician needs.",
    url: "/",
  },
};

export const viewport: Viewport = {
  colorScheme: "light",
  themeColor: "#f6f1e7",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${GeistSans.variable} ${GeistMono.variable}`}>
      <body className="min-h-screen antialiased">
        <AppHeader />
        <main>{children}</main>
        <AppFooter />
      </body>
    </html>
  );
}
