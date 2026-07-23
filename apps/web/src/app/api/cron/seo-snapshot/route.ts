import { NextRequest, NextResponse } from "next/server";
import { getKeywordDashboard } from "@/lib/keyword-targets";
import { runSeoSnapshot } from "@/lib/seo-sync.server";

export const maxDuration = 300;

export async function GET(request: NextRequest) {
  const cronSecret = process.env.CRON_SECRET;
  if (
    !cronSecret ||
    request.headers.get("authorization") !== `Bearer ${cronSecret}`
  ) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const dashboard = getKeywordDashboard();
  const result = await runSeoSnapshot(dashboard.rows);
  return NextResponse.json(result, { status: result.ok ? 200 : 500 });
}
