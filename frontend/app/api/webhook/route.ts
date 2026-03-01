import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  const body = await req.arrayBuffer();
  const sig = req.headers.get("stripe-signature") || "";

  const res = await fetch(`${BACKEND}/stripe/webhook`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "stripe-signature": sig,
    },
    body: Buffer.from(body),
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
