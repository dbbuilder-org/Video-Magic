import { auth } from "@clerk/nextjs/server";
import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000";

export async function POST(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { userId } = await auth();
  if (!userId) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }

  const { id } = await params;
  let res: Response;
  try {
    res = await fetch(`${BACKEND}/projects/${id}/reprocess`, {
      method: "POST",
      headers: { "X-User-Id": userId },
    });
  } catch {
    return NextResponse.json({ detail: "Backend unreachable" }, { status: 503 });
  }
  const ct = res.headers.get("content-type") ?? "";
  if (!ct.includes("application/json")) {
    return NextResponse.json({ detail: "Backend unavailable" }, { status: 503 });
  }
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
