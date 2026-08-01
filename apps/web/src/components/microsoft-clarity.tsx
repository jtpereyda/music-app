import Script from "next/script";

const PROJECT_ID_PATTERN = /^[a-z0-9]+$/;

function getProjectId() {
  const projectId = process.env.NEXT_PUBLIC_CLARITY_PROJECT_ID?.trim();

  if (!projectId) return null;

  if (!PROJECT_ID_PATTERN.test(projectId)) {
    throw new Error(
      "NEXT_PUBLIC_CLARITY_PROJECT_ID must contain only lowercase letters and numbers.",
    );
  }

  return projectId;
}

export function MicrosoftClarity() {
  const projectId = getProjectId();

  if (!projectId) return null;

  return (
    <Script id="microsoft-clarity" strategy="afterInteractive">
      {`
        (function(c,l,a,r,i,t,y){
          c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};
          t=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i;
          y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);
        })(window,document,"clarity","script",${JSON.stringify(projectId)});
      `}
    </Script>
  );
}
