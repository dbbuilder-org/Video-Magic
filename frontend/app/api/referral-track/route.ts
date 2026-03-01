import { auth } from "@clerk/nextjs/server";
import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000";

/**
 * Called after Clerk sign-up when a referral code is present.
 * Registers the referral in the backend, then redirects to /create.
 */
export async function GET(req: NextRequest) {
  const { userId } = await auth();
  const code = req.nextUrl.searchParams.get("code");
  const next = req.nextUrl.searchParams.get("next") || "/create";

  if (userId && code) {
    try {
      await fetch(`${BACKEND}/users/referral/track`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-User-Id": userId,
        },
        body: JSON.stringify({ code }),
      });
    } catch {
      // Non-fatal — still redirect
    }
  }

  return NextResponse.redirect(new URL(next, req.url));
}
