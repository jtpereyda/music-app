const localUrl = "http://localhost:3000";

export const siteName = "Transposify";
export const siteTitleTemplate = `%s | ${siteName}`;
export const defaultSiteTitle = `Practical Music, Shaped to Fit | ${siteName}`;

export function withSiteName(title: string): string {
  return `${title} | ${siteName}`;
}

export function freePdfTitle(subject: string): string {
  return `${subject} | Free PDF`;
}

function normalizeUrl(value: string): URL {
  const withProtocol = value.startsWith("http") ? value : `https://${value}`;
  return new URL(withProtocol);
}

export function getSiteUrl(): URL {
  const configured =
    process.env.SITE_URL ??
    process.env.VERCEL_PROJECT_PRODUCTION_URL ??
    process.env.VERCEL_URL ??
    localUrl;
  return normalizeUrl(configured);
}

export function indexingEnabled(): boolean {
  return process.env.SITE_INDEXABLE === "true";
}
