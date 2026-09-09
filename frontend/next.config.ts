import type { NextConfig } from "next";

/**
 * There is deliberately no rewrite for /api/backend/*.
 *
 * A rewrite forwards the request to the backend untouched, which let the caller
 * supply their own X-User-Id and defeat the backend's ownership check. The path
 * is now served by app/api/backend/[...path]/route.ts, which derives identity
 * from the Clerk session and drops client-supplied identity headers.
 */
const nextConfig: NextConfig = {};

export default nextConfig;
