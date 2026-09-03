import Script from "next/script";

const DEFAULT_CRISP_WEBSITE_ID = "dece6235-3e4e-4791-af3e-214b25891513";
const CRISP_WEBSITE_ID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function getCrispWebsiteId(): string {
  const websiteId =
    process.env.NEXT_PUBLIC_CRISP_WEBSITE_ID?.trim() ||
    DEFAULT_CRISP_WEBSITE_ID;

  if (!CRISP_WEBSITE_ID_PATTERN.test(websiteId)) {
    throw new Error(
      "NEXT_PUBLIC_CRISP_WEBSITE_ID must be a valid Crisp website UUID.",
    );
  }

  return websiteId;
}

export function CrispSupportChat() {
  const websiteId = getCrispWebsiteId();

  return (
    <Script id="crisp-support-chat" strategy="afterInteractive">
      {`
        window.$crisp = window.$crisp || [];
        window.CRISP_WEBSITE_ID = ${JSON.stringify(websiteId)};

        window.$crisp.push(["config", "color:theme", ["deep_orange"]]);
        window.$crisp.push(["config", "color:mode", ["light"]]);
        window.$crisp.push(["config", "layout:theme", ["colorized"]]);
        window.$crisp.push(["set", "session:segments", [["transposify"]]]);

        (function() {
          if (document.querySelector('script[data-transposify-crisp]')) return;

          var script = document.createElement("script");
          script.src = "https://client.crisp.chat/l.js";
          script.async = true;
          script.dataset.transposifyCrisp = "true";
          document.head.appendChild(script);
        })();
      `}
    </Script>
  );
}
