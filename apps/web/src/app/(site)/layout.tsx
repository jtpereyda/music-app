import { Suspense } from "react";
import { AppFooter } from "@/components/app-footer";
import { AppHeader } from "@/components/app-header";
import { FirstPartyPageView } from "@/components/first-party-page-view";
import { MicrosoftClarity } from "@/components/microsoft-clarity";

export default function SiteLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <>
      <AppHeader />
      <main>{children}</main>
      <AppFooter />
      <Suspense fallback={null}>
        <FirstPartyPageView />
      </Suspense>
      <MicrosoftClarity />
    </>
  );
}
