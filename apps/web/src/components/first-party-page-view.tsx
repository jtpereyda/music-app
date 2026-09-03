"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";

type PrivacyAwareNavigator = Navigator & {
  globalPrivacyControl?: boolean;
};

function analyticsAllowed(): boolean {
  const privacyNavigator = navigator as PrivacyAwareNavigator;
  return (
    navigator.doNotTrack !== "1" &&
    window.doNotTrack !== "1" &&
    !privacyNavigator.globalPrivacyControl
  );
}

export function FirstPartyPageView() {
  const pathname = usePathname();
  const lastTrackedPath = useRef<string | null>(null);

  useEffect(() => {
    if (
      !pathname ||
      lastTrackedPath.current === pathname ||
      !analyticsAllowed()
    ) {
      return;
    }

    lastTrackedPath.current = pathname;
    void fetch("/api/analytics/page-view", {
      method: "POST",
      body: JSON.stringify({
        path: pathname,
        referrer: document.referrer || null,
      }),
      credentials: "same-origin",
      headers: { "content-type": "application/json" },
      keepalive: true,
    }).catch(() => undefined);
  }, [pathname]);

  return null;
}
