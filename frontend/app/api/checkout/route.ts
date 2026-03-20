import { auth, currentUser } from "@clerk/nextjs/server";
import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000";

const FREE_EMAILS = new Set(["dbbuilderio@gmail.com"]);
const FREE_DOMAINS = new Set(["servicevision.net"]);

function isFreeUser(email: string): boolean {
  const lower = email.toLowerCase();
  if (FREE_EMAILS.has(lower)) return true;
  const domain = lower.split("@")[1];
  return !!domain && FREE_DOMAINS.has(domain);
}

export async function POST(req: NextRequest) {
  const { userId } = await auth();
  if (!userId) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }

  const body = await req.json();

  const user = await currentUser();
  const primaryEmail = user?.emailAddresses?.[0]?.emailAddress ?? "";
  const free = isFreeUser(primaryEmail);

  const endpoint = free
    ? `${BACKEND}/stripe/free-checkout`
    : `${BACKEND}/stripe/checkout`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-User-Id": userId,
  };
  if (free) {
    headers["X-User-Email"] = primaryEmail;
  }

  const res = await fetch(endpoint, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
