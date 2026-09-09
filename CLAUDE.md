# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Backend (FastAPI)
cd backend && pip install -r requirements.txt
cp .env.example .env   # fill in API keys
uvicorn main:app --reload --port 8000

# Frontend (Next.js 15)
cd frontend && npm install
cp .env.local.example .env.local   # set BACKEND_URL + Clerk keys
npm run dev          # port 3000
npm run build        # production build
npm run lint         # eslint

# Stripe webhook (local dev)
stripe listen --forward-to localhost:8000/stripe/webhook
```

```bash
# Backend tests
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements-test.txt
.venv/bin/python -m pytest tests/ -q      # 97 tests
```

The frontend has no test suite — manual browser testing only.

## Architecture

```
frontend/   Next.js 15 + React 19 + Tailwind + Clerk auth
backend/    FastAPI (Python) + SQLite (no ORM) + SSE progress bus
storage/    projects/<id>/{scenes/,overlays/,final.mp4} — gitignored
```

**API proxy**: `/api/backend/*` is served by `frontend/app/api/backend/[...path]/route.ts`, an
authenticated proxy. It resolves the Clerk session server-side, sets `X-User-Id` from it, **drops any
client-supplied `X-User-*` header**, and attaches `X-Proxy-Secret`. There is deliberately **no
rewrite** in `next.config.ts` — see the comment there before adding one back.

**Auth model**: the backend still derives identity from `X-User-Id` and never calls Clerk. That is
only sound because `api/proxy_guard.py` rejects any guarded request whose `X-Proxy-Secret` does not
match `BACKEND_PROXY_SECRET`, so the header can only have been set by the proxy. Both sides **fail
closed** when the variable is unset (proxy 503, backend 503). Public paths: `/health`,
`/stripe/webhook`, `/storage`, and the docs routes.

> **Why it is built this way.** The backend is deployed as its own public web service (`render.yaml`),
> so before the gate existed anyone could call it directly with a chosen `X-User-Id` and read or
> modify another user's profile, credits, referral code and projects — `_require_owner` compares the
> header against the user id in the path, and a direct caller controls both. A chosen
> `X-User-Email` on `stripe/free-checkout` also granted free generation, since entitlement is
> decided by email domain (`FREE_DOMAINS`). Keep both halves: the proxy is what makes the header
> true, and the gate is what makes the proxy unavoidable.

**Database**: SQLite with WAL mode, raw parameterized SQL in `backend/models.py`. Tables: `projects`, `jobs`, `user_profiles`, `referral_codes`, `referrals`, `user_credits`.

**Progress**: `backend/progress.py` — `asyncio.Queue` per project_id. Use `emit()` from sync/thread context, `emit_async()` from async context. Frontend subscribes via SSE at `/api/progress/[id]`.

## Pipeline Stages (backend/api/generate.py)

Runs as a FastAPI `BackgroundTask` triggered by Stripe webhook:

1. **Document parse** (5–12%): Gemini Flash 2.0 → structured JSON spec (title, scenes, vo_text, etc.)
2. **Character gen** (20–27%): Imagen 4.0 → brand character PNG
3. **Text overlays** (32%): Pillow → title card, 4–8 lower-thirds, CTA card PNGs
4. **Scene gen** (35–75%): Veo 3.1 → one video per scene, polls every 10s (max 360s)
5. **Voiceover** (82%): ElevenLabs SDK v2 → MP3 (`eleven_turbo_v2_5`)
6. **Stitch** (88%): ffmpeg concat demuxer → stitched MP4
7. **Overlay** (93%): ffmpeg complex filter composites timed text PNGs onto video
8. **Mix** (100%): ffmpeg audio duck (voiceover 100%, native 15%) → final MP4

Each stage checks if its output file already exists before regenerating (idempotent).

## Critical Rule: No Text in Veo Prompts

Veo 3.1 prompts must contain **zero readable words**. All on-screen text is rendered via Pillow PNG overlays composited by ffmpeg in stage 7. Never describe text labels in Veo scene prompts — describe only visual action and motion.

## Key File Paths

| File | Purpose |
|------|---------|
| `backend/main.py` | FastAPI app, CORS, static `/storage` mount, health check |
| `backend/models.py` | All SQLite CRUD — no ORM, parameterized SQL only |
| `backend/progress.py` | SSE bus: `emit()`, `emit_async()`, `subscribe()` |
| `backend/storage.py` | Path helpers: `project_dir()`, `final_path()`, etc. |
| `backend/api/generate.py` | Full 8-stage pipeline orchestrator |
| `backend/api/stripe_routes.py` | Checkout creation, webhook handler, pricing endpoint |
| `backend/api/projects.py` | Project CRUD + SSE proxy endpoint |
| `backend/api/users.py` | Profile, credits, referral code endpoints |
| `backend/pipeline/document_parser.py` | Gemini Flash → JSON spec |
| `backend/pipeline/character_gen.py` | Imagen 4.0 → character PNG |
| `backend/pipeline/scene_gen.py` | Veo 3.1 generate + poll + URI download |
| `backend/pipeline/text_overlay.py` | Pillow text PNGs + ffmpeg composite |
| `backend/pipeline/voiceover.py` | ElevenLabs SDK v2 MP3 generation |
| `backend/pipeline/assembler.py` | ffmpeg stitch + audio duck/mix |
| `frontend/app/api/backend/[...path]/route.ts` | Authenticated catch-all proxy; sets identity from the Clerk session |
| `frontend/app/api/checkout/route.ts` | Auth'd proxy: POST checkout → backend |
| `backend/api/proxy_guard.py` | Shared-secret gate; fails closed when unset |
| `frontend/app/api/progress/[id]/route.ts` | SSE proxy to backend (duplex: "half") |
| `frontend/middleware.ts` | Clerk auth; public routes: `/`, `/sign-in`, `/sign-up`, `/api/webhook` |

## Payment Flow

1. Wizard completes → `POST /api/checkout` → backend creates project (status=`pending`), applies credits as Stripe coupon, returns checkout URL
2. User pays → Stripe fires `checkout.session.completed` webhook to `POST /api/webhook`
3. Webhook handler: verifies signature, deducts `pending_credit_cents`, applies $5 referral credit to referrer, starts pipeline BackgroundTask
4. Referral: first paid video by referred user triggers one-time $5 credit to referrer

## Environment Variables

**Backend** (`.env`):

| Var | Description |
|-----|-------------|
| `GEMINI_API_KEY` | Google AI key for Gemini Flash + Imagen 4 + Veo 3.1 |
| `ELEVENLABS_API_KEY` | ElevenLabs voiceover |
| `ELEVENLABS_VOICE_ID` | Default: `nPczCjzI2devNBz1zQrb` (Brian) |
| `STRIPE_SECRET_KEY` | Stripe secret key |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret |
| `STRIPE_PRICE_10S/30S/60S` | Stripe Price IDs |
| `APP_URL` | Frontend URL for Stripe redirects |
| `DATABASE_PATH` | SQLite path (default: `./video_magic.db`) |
| `STORAGE_DIR` | Video output dir (default: `./storage/projects`) |
| `BACKEND_PROXY_SECRET` | **Required.** Shared with the frontend; unset = all guarded routes 503 |

**Frontend** (`.env.local`):
- `BACKEND_URL` — FastAPI URL (e.g., `http://localhost:8000`)
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`
- `NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in`, `NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up`
- `BACKEND_PROXY_SECRET` — **required**; must match the backend's. Unset = the proxy 503s

## Deployment

- `render.yaml` defines both services (Oregon region, starter plan)
- Backend: Python web service, 1 GB disk at `/opt/render/project/storage/projects`, health check `/health`
- Frontend: Node.js web service, root dir `frontend/`
- Domain: `videomagic.servicevision.io` → Cloudflare CNAME → Render external URL

## Veo 3.1 Constraints

Free tier: ~7 videos/day (429 RESOURCE_EXHAUSTED). Working params:
- `aspect_ratio="16:9"` only
- Do NOT pass `duration_seconds`, `fps`, `generate_audio`, or `person_generation`
- Model: `veo-3.1-generate-preview`
