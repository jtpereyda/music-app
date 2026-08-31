import { AppFooter } from "@/components/app-footer";
import { AppHeader } from "@/components/app-header";
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
      <MicrosoftClarity />
    </>
  );
}
