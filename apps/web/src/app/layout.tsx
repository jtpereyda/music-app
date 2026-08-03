import type { Metadata, Viewport } from "next";
import { GeistMono } from "geist/font/mono";
import { GeistSans } from "geist/font/sans";
import { AppFooter } from "@/components/app-footer";
import { AppHeader } from "@/components/app-header";
import { MicrosoftClarity } from "@/components/microsoft-clarity";
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
        <MicrosoftClarity />
      </body>
    </html>
  );
}
