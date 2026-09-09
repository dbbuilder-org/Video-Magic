"""Shared-secret gate for the Next.js proxy.

The backend derives identity from ``X-User-Id`` and, on the checkout routes,
entitlement from ``X-User-Email``. Those headers are only trustworthy if the
request cannot have come from anywhere but the Next.js proxy, which sets them
from the Clerk session. This middleware is what establishes that.

Fails closed on purpose: if ``BACKEND_PROXY_SECRET`` is unset the app refuses
every guarded request rather than waving them through, because an unset
environment variable is exactly how this protection would otherwise be lost in
a deploy.
"""
import hmac
import os

from fastapi import Request
from fastapi.responses import JSONResponse

#: Paths that are reachable without the proxy secret.
#:
#: - ``/health`` is an unauthenticated liveness probe and returns no user data.
#: - ``/stripe/webhook`` is called by Stripe, not by our frontend, and
#:   authenticates itself with a signature.
#: - ``/storage`` serves generated video assets by unguessable project id.
#: - the OpenAPI/docs routes carry no user data.
PUBLIC_PREFIXES = (
    "/health",
    "/stripe/webhook",
    "/storage",
    "/docs",
    "/redoc",
    "/openapi.json",
)


def _is_public(path: str) -> bool:
    return any(path == p or path.startswith(p + "/") for p in PUBLIC_PREFIXES)


async def require_proxy_secret(request: Request, call_next):
    """Reject any guarded request that did not come through the Next.js proxy."""
    if request.method == "OPTIONS" or _is_public(request.url.path):
        return await call_next(request)

    expected = os.environ.get("BACKEND_PROXY_SECRET")
    if not expected:
        return JSONResponse(
            {"detail": "Server misconfigured: BACKEND_PROXY_SECRET is not set"},
            status_code=503,
        )

    supplied = request.headers.get("X-Proxy-Secret", "")
    # compare_digest to keep the comparison constant-time.
    if not hmac.compare_digest(supplied, expected):
        return JSONResponse({"detail": "Forbidden"}, status_code=403)

    return await call_next(request)
