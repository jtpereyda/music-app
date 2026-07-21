import { FlagshipUseCase } from "@/components/flagship-use-case";
import { TransposifyHero } from "@/components/transposify-hero";
import { TransposifyPrinciples } from "@/components/transposify-principles";

export default function HomePage() {
  return (
    <>
      <TransposifyHero />
      <FlagshipUseCase />
      <TransposifyPrinciples />
    </>
  );
}
