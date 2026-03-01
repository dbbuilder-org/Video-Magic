import { auth } from "@clerk/nextjs/server";
import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000";

export async function GET(req: NextRequest) {
  const { userId } = await auth();
  if (!userId) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }

  const res = await fetch(`${BACKEND}/projects?user_id=${encodeURIComponent(userId)}`, {
    headers: { "X-User-Id": userId },
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
