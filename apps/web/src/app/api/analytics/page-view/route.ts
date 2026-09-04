import { after, NextRequest, NextResponse } from "next/server";
import { recordFirstPartyPageView } from "@/lib/first-party-analytics.server";
import { normalizeInternalPath } from "@/lib/internal-path";

const SESSION_COOKIE = "transposify_analytics_session";
const SESSION_MAX_AGE_SECONDS = 30 * 60;
const MAX_PAYLOAD_LENGTH = 4096;
const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function noContent() {
  return new NextResponse(null, {
    status: 204,
    headers: { "cache-control": "no-store" },
  });
}

function normalizeReferrerHost(value: unknown): string | null {
  if (typeof value !== "string" || value.length > 2048) return null;

  try {
    const hostname = new URL(value).hostname.toLowerCase();
    return hostname && hostname.length <= 253 ? hostname : null;
  } catch {
    return null;
  }
}

function requestOptsOut(request: NextRequest): boolean {
  return (
    request.headers.get("dnt") === "1" ||
    request.headers.get("sec-gpc") === "1"
  );
}

function requestIsSameOrigin(request: NextRequest): boolean {
  const fetchSite = request.headers.get("sec-fetch-site");
  if (fetchSite === "cross-site") return false;

  const origin = request.headers.get("origin");
  return !origin || origin === request.nextUrl.origin;
}

export async function POST(request: NextRequest) {
  if (requestOptsOut(request)) return noContent();
  if (!requestIsSameOrigin(request)) {
    return NextResponse.json({ detail: "Cross-origin request denied." }, { status: 403 });
  }
  if (!request.headers.get("content-type")?.startsWith("application/json")) {
    return NextResponse.json({ detail: "JSON body required." }, { status: 415 });
  }

  const rawPayload = await request.text();
  if (rawPayload.length > MAX_PAYLOAD_LENGTH) {
    return NextResponse.json({ detail: "Payload too large." }, { status: 413 });
  }

  let payload: unknown;
  try {
    payload = JSON.parse(rawPayload);
  } catch {
    return NextResponse.json({ detail: "Invalid JSON body." }, { status: 400 });
  }

  if (!payload || typeof payload !== "object") {
    return NextResponse.json({ detail: "Invalid page view." }, { status: 400 });
  }

  const body = payload as { path?: unknown; referrer?: unknown };
  const path = normalizeInternalPath(body.path);
  if (!path) {
    return NextResponse.json({ detail: "Invalid page path." }, { status: 400 });
  }

  const existingSessionId = request.cookies.get(SESSION_COOKIE)?.value;
  const sessionId =
    existingSessionId && UUID_PATTERN.test(existingSessionId)
      ? existingSessionId
      : crypto.randomUUID();
  const referrerHost = normalizeReferrerHost(body.referrer);
  after(async () => {
    await recordFirstPartyPageView({ path, referrerHost, sessionId });
  });
  const response = noContent();

  response.cookies.set(SESSION_COOKIE, sessionId, {
    httpOnly: true,
    maxAge: SESSION_MAX_AGE_SECONDS,
    path: "/",
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
  });

  return response;
}
