/**
 * Authenticated proxy to the FastAPI backend.
 *
 * This route replaces the `/api/backend/:path*` rewrite that used to live in
 * next.config.ts. That rewrite handed the request to the backend untouched,
 * which meant the caller chose their own `X-User-Id` — and the backend's
 * ownership check compares that header against the user id in the path, so a
 * caller supplying both simply passed it. A signed-in user could read or
 * modify any other user's profile, referral code, credits and projects, and
 * could reach `stripe/free-checkout` with a spoofed `X-User-Email` to get
 * generation for free.
 *
 * The rules here:
 *  - Identity comes from the Clerk session, server-side, and nothing else.
 *  - Client-supplied `X-User-*` headers are dropped, never forwarded. A caller
 *    cannot express an identity claim at all.
 *  - Every proxied request carries BACKEND_PROXY_SECRET, so the backend can
 *    tell a request that passed through here from one that did not.
 *  - The Stripe webhook is not reachable through this proxy: it must stay
 *    public and is authenticated by its own signature.
 */
import { auth, currentUser } from "@clerk/nextjs/server";
import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000";

/** Paths that must never be proxied, matched against the joined path. */
const DENIED = [/^stripe\/webhook$/];

/**
 * Headers worth passing through. Everything else — and in particular anything
 * beginning with `x-user-` — is dropped so that the caller cannot assert an
 * identity. An allowlist is used rather than a denylist because a new
 * identity-bearing header added later would otherwise be forwarded by default.
 */
const FORWARDED = new Set(["content-type", "accept"]);

/** Endpoints that need the caller's email address to make a decision. */
const NEEDS_EMAIL = [/^stripe\/(free-)?checkout$/];

async function proxy(req: NextRequest, segments: string[]) {
  const { userId } = await auth();
  if (!userId) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }

  const path = segments.map(encodeURIComponent).join("/");
  if (DENIED.some((re) => re.test(path))) {
    return NextResponse.json({ detail: "Not found" }, { status: 404 });
  }

  const secret = process.env.BACKEND_PROXY_SECRET;
  if (!secret) {
    // Fail closed. Without the secret the backend cannot distinguish this
    // proxy from a direct caller, which is the whole point of the header.
    console.error("BACKEND_PROXY_SECRET is not set; refusing to proxy");
    return NextResponse.json({ detail: "Proxy misconfigured" }, { status: 503 });
  }

  const headers = new Headers();
  for (const [key, value] of req.headers) {
    if (FORWARDED.has(key.toLowerCase())) headers.set(key, value);
  }
  headers.set("X-User-Id", userId);
  headers.set("X-Proxy-Secret", secret);

  if (NEEDS_EMAIL.some((re) => re.test(path))) {
    const user = await currentUser();
    const email = user?.emailAddresses?.[0]?.emailAddress ?? "";
    if (email) headers.set("X-User-Email", email);
  }

  const search = req.nextUrl.search;
  const body =
    req.method === "GET" || req.method === "HEAD" ? undefined : await req.text();

  const res = await fetch(`${BACKEND}/${path}${search}`, {
    method: req.method,
    headers,
    body,
  });

  const text = await res.text();
  return new NextResponse(text, {
    status: res.status,
    headers: {
      "content-type": res.headers.get("content-type") ?? "application/json",
    },
  });
}

type Ctx = { params: Promise<{ path: string[] }> };

export async function GET(req: NextRequest, ctx: Ctx) {
  return proxy(req, (await ctx.params).path);
}
export async function POST(req: NextRequest, ctx: Ctx) {
  return proxy(req, (await ctx.params).path);
}
export async function PUT(req: NextRequest, ctx: Ctx) {
  return proxy(req, (await ctx.params).path);
}
export async function PATCH(req: NextRequest, ctx: Ctx) {
  return proxy(req, (await ctx.params).path);
}
export async function DELETE(req: NextRequest, ctx: Ctx) {
  return proxy(req, (await ctx.params).path);
}
