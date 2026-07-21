import { NextRequest, NextResponse } from "next/server";
import { hymns } from "@/lib/catalog";

const renderApiUrl = (
  process.env.RENDER_API_URL ?? process.env.NEXT_PUBLIC_RENDER_API_URL
)?.replace(/\/$/, "");
const hymnIds = new Set(hymns.map((hymn) => hymn.id));
const artifacts = new Set(["preview.svg", "score.pdf"]);
const forwardedParameters = new Set([
  "key",
  "line",
  "clef",
  "octave",
  "page_size",
  "page",
]);

interface RouteContext {
  params: Promise<{
    hymnId: string;
    artifact: string;
  }>;
}

export async function GET(request: NextRequest, context: RouteContext) {
  const { hymnId, artifact } = await context.params;
  if (!hymnIds.has(hymnId) || !artifacts.has(artifact)) {
    return NextResponse.json({ detail: "Render artifact not found." }, { status: 404 });
  }
  if (!renderApiUrl) {
    return NextResponse.json(
      { detail: "The render API is not configured." },
      { status: 503 },
    );
  }

  const upstreamUrl = new URL(
    `/v1/hymns/${encodeURIComponent(hymnId)}/${artifact}`,
    `${renderApiUrl}/`,
  );
  for (const [name, value] of request.nextUrl.searchParams) {
    if (forwardedParameters.has(name)) {
      upstreamUrl.searchParams.append(name, value);
    }
  }

  try {
    const upstream = await fetch(upstreamUrl, { cache: "no-store" });
    const headers = new Headers();
    for (const name of [
      "content-type",
      "content-disposition",
      "etag",
      "x-hymn-id",
      "x-page-count",
      "x-octave-algorithm",
      "x-octave-placement",
      "x-octave-shift",
    ]) {
      const value = upstream.headers.get(name);
      if (value) {
        headers.set(name, value);
      }
    }
    headers.set("cache-control", "private, max-age=0, must-revalidate");
    return new NextResponse(upstream.body, {
      status: upstream.status,
      headers,
    });
  } catch {
    return NextResponse.json(
      { detail: "The render API could not be reached." },
      { status: 502 },
    );
  }
}
