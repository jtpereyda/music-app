import type { MetadataRoute } from "next";
import { getSiteUrl, indexingEnabled } from "@/lib/site";

export default function robots(): MetadataRoute.Robots {
  const canIndex = indexingEnabled();

  return {
    rules: {
      userAgent: "*",
      allow: canIndex ? "/" : undefined,
      disallow: canIndex ? ["/admin/", "/api/"] : "/",
    },
    sitemap: new URL("/sitemap.xml", getSiteUrl()).toString(),
  };
}
