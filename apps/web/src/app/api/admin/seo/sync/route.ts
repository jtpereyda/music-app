import { NextResponse } from "next/server";
import { auth } from "@/auth";
import { isAuthorizedAdmin } from "@/lib/admin-auth";
import { getKeywordDashboard } from "@/lib/keyword-targets";
import { runSeoSnapshot } from "@/lib/seo-sync.server";

export const maxDuration = 300;

export async function POST() {
  const session = await auth();
  if (!isAuthorizedAdmin(session?.user?.email)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const dashboard = getKeywordDashboard();
  const result = await runSeoSnapshot(dashboard.rows);
  return NextResponse.json(result, { status: result.ok ? 200 : 500 });
}
