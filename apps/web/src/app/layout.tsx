import type { Metadata, Viewport } from "next";
import { GeistMono } from "geist/font/mono";
import { GeistSans } from "geist/font/sans";
import { AppFooter } from "@/components/app-footer";
import { AppHeader } from "@/components/app-header";
import "./globals.css";

export const metadata: Metadata = {
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
    index: false,
    follow: false,
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
