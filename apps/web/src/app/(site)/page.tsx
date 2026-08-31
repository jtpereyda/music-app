import type { Metadata } from "next";
import { FlagshipUseCase } from "@/components/flagship-use-case";
import { SheetMusicPaths } from "@/components/sheet-music-paths";
import { TransposifyHero } from "@/components/transposify-hero";
import { TransposifyPrinciples } from "@/components/transposify-principles";

export const metadata: Metadata = {
  alternates: { canonical: "/" },
};

export default function HomePage() {
  return (
    <>
      <TransposifyHero />
      <SheetMusicPaths />
      <FlagshipUseCase />
      <TransposifyPrinciples />
    </>
  );
}
