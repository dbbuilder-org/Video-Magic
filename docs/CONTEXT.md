# Video Magic — Full Project Context

**Created:** 2026-03-01
**Owner:** Chris Therriault <chris@servicevision.net>
**Repo:** https://github.com/dbbuilder-org/Video-Magic
**Live URL:** https://videomagic.servicevision.io (Cloudflare CNAME → Render)

---

## What It Is

Video Magic is a SaaS that turns any document (pasted text, product brief, policy doc, pitch deck excerpt) into a branded animated video with voiceover. The user pays once, gets a video in 5–20 minutes, and can edit the script and re-run as many times as they want at no extra charge.

**Core insight:** AI video models (Veo, Sora) cannot render readable text reliably. Video Magic routes all text through Pillow-generated PNG overlays composited by ffmpeg. Veo prompts contain zero readable words — they describe only visual motion and imagery. This guarantees 100% accurate title cards, lower-thirds, and CTAs on every render.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15 + Tailwind CSS + TypeScript |
| Auth | Clerk (`@clerk/nextjs` v6) |
| Backend | FastAPI (Python 3.11+) |
| Database | SQLite (WAL mode, no ORM) |
| Video generation | Google Veo 3.1 (`veo-3.1-generate-preview`) |
| Image generation | Imagen 4 (`imagen-4.0-generate-001`) |
| Document parsing | Gemini Flash 2.0 (`gemini-2.0-flash-001`) |
| Text overlays | Pillow (Python) |
| Video assembly | ffmpeg (local binary) |
| Voiceover | ElevenLabs SDK v2 |
| Payments | Stripe Checkout + webhooks |
| Deployment | Render.com (starter plan) |
| DNS | Cloudflare CNAME → Render |
| Source | GitHub: `dbbuilder-org/Video-Magic` |

---

## Pricing (current)

| Duration | Scenes | Price | Est. API cost | Est. margin |
|----------|--------|-------|--------------|-------------|
| 10 seconds | 2 Veo clips | $9.99 | ~$2.11 | ~79% |
| 30 seconds | 4 Veo clips | $19.99 | ~$4.17 | ~79% |
| 60 seconds | 8 Veo clips | $29.99 | ~$8.26 | ~72% |

API cost breakdown per video: Veo ~$1/scene (estimate — not yet published), Imagen 4 $0.04/image, Gemini Flash ~$0.001/call, ElevenLabs $0.0005/character.

**Important:** Veo 3.1 pricing is not publicly documented. These are estimates. Sprint 0 (cost tracking) must be implemented before accepting real-money orders.

---

## Deployment

### Render (current — testing)

| Service | Plan | Cost |
|---------|------|------|
| `video-magic-api` | Starter (512 MB) | $7/mo |
| `video-magic-frontend` | Starter (512 MB) | $7/mo |
| Disk (storage) | 1 GB | $0.25/mo |
| **Total** | | **~$14.25/mo** |

Configured in `render.yaml` at repo root. Starter is sufficient because:
- Veo polling is pure I/O (sleep + GET) — negligible RAM
- ffmpeg peak RAM for 1080p MP4: ~250 MB
- Next.js SSR at this scale fits in 512 MB

**Scale trigger:** If backend OOMs on 60s (8-scene) video → bump `video-magic-api` to Standard ($25/mo). Keep frontend on Starter.

### Cloudflare DNS
- Zone: `servicevision.io`
- Record: `videomagic` CNAME → Render frontend URL (DNS-only or proxied)
- SSL: Full mode in Cloudflare

### Environment Variables

**Backend (set in Render Dashboard):**
```
GEMINI_API_KEY          Google AI Studio key (Veo + Imagen + Gemini Flash)
ELEVENLABS_API_KEY      ElevenLabs key
ELEVENLABS_VOICE_ID     nPczCjzI2devNBz1zQrb (Brian — default)
STRIPE_SECRET_KEY       sk_live_... or sk_test_...
STRIPE_WEBHOOK_SECRET   whsec_... (from Stripe Dashboard)
STRIPE_PRICE_10S        price_... for $9.99
STRIPE_PRICE_30S        price_... for $19.99
STRIPE_PRICE_60S        price_... for $29.99
APP_URL                 https://videomagic.servicevision.io
CORS_ORIGINS            https://videomagic.servicevision.io
STORAGE_DIR             /opt/render/project/storage/projects
DATABASE_PATH           /opt/render/project/video_magic.db
```

**Frontend (set in Render Dashboard):**
```
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY   pk_test_Y29zbWljLWxsYW1hLTk1LmNsZXJrLmFjY291bnRzLmRldiQ
CLERK_SECRET_KEY                    sk_test_jFBU3L4IB2DzUe6Qwom6E2gZZIepCNo4vJC7mCOy49
NEXT_PUBLIC_CLERK_SIGN_IN_URL       /sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL       /sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL /create
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL /create
BACKEND_URL                         (auto-set from video-magic-api service)
NEXT_PUBLIC_BACKEND_URL             (auto-set from video-magic-api service)
```

---

## Auth (Clerk)

- Middleware at `frontend/middleware.ts` — protects `/create`, `/project/:id`, `/api/*` except `/api/webhook`
- Sign-in: `/sign-in` — Clerk `<SignIn>` with dark brand appearance
- Sign-up: `/sign-up?ref=CODE` — shows referral banner when `ref` param present
- After sign-up with referral code → redirects to `/api/referral-track?code=X` → registers referral → redirects to `/create`
- `X-User-Id` header injected by Next.js API routes (after `auth()` server-side call) into all backend requests
- Clerk app: `cosmic-llama-95.clerk.accounts.dev`

---

## Pipeline — Full 8-Stage Flow

```
User submits wizard
  → POST /api/checkout (Next.js)
  → auth() gets Clerk userId, injects X-User-Id header
  → POST /stripe/checkout (FastAPI)
    → create_project(spec, user_id) in SQLite
    → upsert_user_profile() saves brand for next time
    → check user_credits → create Stripe coupon if credits > 0
    → stripe.checkout.Session.create() → return checkout_url

User pays on Stripe
  → Stripe sends POST /api/webhook (Next.js) → proxied to /stripe/webhook (FastAPI)
  → stripe.Webhook.construct_event() verifies signature
  → deduct_user_credits() if credit coupon was applied
  → apply_referral_credit() if first payment by referred user → referrer gets $5
  → bg.add_task(run_pipeline, project_id, spec)

Pipeline (BackgroundTask):
  Stage 1  parse_document     5→12%   Gemini Flash → JSON spec (title, tagline, scenes[], cta)
  Stage 2  character_gen     20→27%   Imagen 4 → brand character PNG
  Stage 3  text_overlays     32%      Pillow → title_card.png + lower_N.png × N + cta_card.png
  Stage 4  scene_0..N        35→75%   Veo 3.1 × scene_count (2/4/8); each: generate → poll → URI download
  Stage 5  voiceover         82%      ElevenLabs → voiceover.mp3
  Stage 6  stitch            88%      ffmpeg concat → stitched.mp4
  Stage 7  overlay           93%      ffmpeg overlay filter → overlaid.mp4
  Stage 8  mix               100%     ffmpeg amix (VO at 100%, native at 15%) → final.mp4

Each stage: upsert_job() in SQLite + emit_async() → asyncio.Queue → SSE → browser ProgressTracker
```

---

## Text Overlay Architecture (the key differentiator)

Veo cannot render readable text. All text is generated by Pillow and composited by ffmpeg after video generation.

**Assets generated per video:**
- `overlays/title_card.png` — 1920×1080 RGBA, shown t=0 to t=3s
- `overlays/lower_N.png` — 1920×194 RGBA (bottom 18%), one per scene, shown at scene boundaries
- `overlays/cta_card.png` — 1920×1080 RGBA, shown last 3 seconds

**ffmpeg filter_complex:** chained `overlay` calls with `enable='between(t,start,end)'`

**Font fallback chain:**
1. `/System/Library/Fonts/Supplemental/Arial Bold.ttf` (macOS)
2. `/System/Library/Fonts/Helvetica.ttc`
3. `/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf` (Linux/Render)
4. `ImageFont.load_default()` (last resort)

**Veo prompt rule — enforced in system prompt:**
> `visual_action` must contain ZERO readable words — describe motion, color, objects only.

---

## Veo 3.1 — Working Config

From `strata-ai` experience (generating 8-scene Agent Double-O-Data animation):

```python
operation = client.models.generate_videos(
    model="veo-3.1-generate-preview",
    prompt=scene["visual_action"],
    config=types.GenerateVideosConfig(
        aspect_ratio="16:9",
        # NO: duration_seconds, fps, generate_audio, person_generation
    ),
)
# Poll: operation.done is not True (not False — it's None while pending)
while operation.done is not True:
    time.sleep(10)
    operation = client.operations.get(operation)
# Download: video.video_bytes (direct) or video.uri (append ?key=API_KEY)
```

**Quota:** Free tier ~7 videos/day before 429 RESOURCE_EXHAUSTED. Daily reset. Must file quota increase request via Google Cloud before launch.

---

## ElevenLabs — Working Config

```python
# SDK v2 — text_to_speech.convert() returns a bytes iterator
audio_iter = eleven.text_to_speech.convert(
    voice_id="nPczCjzI2devNBz1zQrb",  # Brian — deep, resonant
    text=script,
    model_id="eleven_turbo_v2_5",
    output_format="mp3_44100_128",
    voice_settings={"stability": 0.70, "similarity_boost": 0.80, "speed": 0.90},
)
audio_bytes = b"".join(audio_iter)
```

No `.generate()` method — that's SDK v1. Always use `text_to_speech.convert()`.

---

## Referral System

- Each user gets a unique 8-char alphanumeric code (`referral_codes` table)
- `GET /users/{id}/referral-code` → returns code + full `referral_url` (e.g. `https://videomagic.servicevision.io/sign-up?ref=ABC12345`)
- Sign-up with `?ref=CODE` → after Clerk auth → `GET /api/referral-track?code=X` → `register_referral()` in SQLite
- When referred user makes first payment → `apply_referral_credit()` → referrer gets 500 cents ($5) added to `user_credits`
- Credits applied at checkout: `get_user_credits()` → if > 0 → `stripe.Coupon.create(amount_off=credits)` → `stripe.checkout.Session.create(discounts=[{coupon}])`
- Credits deducted in webhook on `checkout.session.completed`
- `ReferralWidget` component shows in step 3 of wizard (copy link + available balance)

---

## User Brand Profiles

- `user_profiles` table: `(user_id PK, brand_name, brand_color, updated_at)`
- Saved automatically on checkout (`upsert_user_profile()` in stripe handler)
- Loaded on wizard mount via `GET /api/backend/users/{userId}/profile` with `X-User-Id` header
- Pre-fills brand name + color in step 2 of wizard

---

## Database Schema Summary

```sql
projects       (id, user_id, status, spec JSON, video_url, error, created_at, updated_at)
jobs           (id, project_id, stage, pct, status, detail, created_at, updated_at)
user_profiles  (user_id PK, brand_name, brand_color, updated_at)
referral_codes (code PK, user_id UNIQUE, created_at)
referrals      (id, referrer_id, referred_id, code, first_paid_at, credit_applied, created_at)
user_credits   (user_id PK, balance_cents, updated_at)
```

Projects `spec` column stores a JSON blob that evolves through the pipeline:
```json
{
  "duration": 30,
  "brand_name": "Acme Corp",
  "brand_color": "#1A56DB",
  "document_text": "...",
  "doc_spec": {
    "title": "...", "tagline": "...", "key_messages": [...],
    "scenes": [{"index": 0, "caption": "...", "visual_action": "...", "vo_text": "..."}],
    "cta": "...", "brand_description": "..."
  }
}
```

---

## File Layout

```
Video-Magic/
├── CLAUDE.md                        Project instructions for Claude Code
├── render.yaml                      Render.com deployment config (both services + disk)
├── .gitignore
├── backend/
│   ├── main.py                      FastAPI app, CORS, StaticFiles, router mounts
│   ├── models.py                    All SQLite tables + CRUD (no ORM)
│   ├── progress.py                  asyncio.Queue SSE bus
│   ├── storage.py                   Path helpers for project file layout
│   ├── requirements.txt
│   ├── .env.example
│   ├── api/
│   │   ├── generate.py              Pipeline orchestrator (BackgroundTask)
│   │   ├── projects.py              GET/PATCH /projects/:id, SSE route, ownership check
│   │   ├── stripe_routes.py         POST /stripe/checkout + /webhook, credit coupon logic
│   │   └── users.py                 Profile, referral code, credits, project list routes
│   └── pipeline/
│       ├── document_parser.py       Gemini Flash → JSON script spec
│       ├── character_gen.py         Imagen 4 → brand character PNG
│       ├── scene_gen.py             Veo 3.1 → MP4 per scene (poll + URI download)
│       ├── text_overlay.py          Pillow PNGs + ffmpeg composite
│       ├── voiceover.py             ElevenLabs SDK v2
│       └── assembler.py             ffmpeg stitch + duck/mix
├── frontend/
│   ├── middleware.ts                Clerk auth middleware (route protection)
│   ├── next.config.ts
│   ├── package.json                 @clerk/nextjs, next 15, react 19, tailwind
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── .env.local.example
│   ├── app/
│   │   ├── layout.tsx               ClerkProvider wrapper
│   │   ├── page.tsx                 Landing: hero, pricing, how-it-works
│   │   ├── globals.css
│   │   ├── create/page.tsx          3-step wizard with profile pre-fill
│   │   ├── project/[id]/page.tsx    SSE progress + script editor + video player
│   │   ├── sign-in/[[...sign-in]]/page.tsx
│   │   ├── sign-up/[[...sign-up]]/page.tsx   handles ?ref=CODE
│   │   └── api/
│   │       ├── checkout/route.ts    auth() → X-User-Id → proxy to /stripe/checkout
│   │       ├── webhook/route.ts     Stripe signature proxy (public route)
│   │       ├── projects/route.ts    List user's projects
│   │       ├── referral-track/route.ts  POST referral to backend after sign-up
│   │       └── progress/[id]/route.ts  SSE proxy to /projects/:id/progress
│   └── components/
│       ├── PricingCards.tsx
│       ├── WizardUpload.tsx
│       ├── WizardBrand.tsx
│       ├── WizardDuration.tsx
│       ├── ProgressTracker.tsx      SSE-driven animated stage list
│       ├── ScriptEditor.tsx         Editable doc_spec + PATCH + re-run
│       ├── VideoPlayer.tsx          HTML5 video + download
│       └── ReferralWidget.tsx       Copy referral link + credit balance display
├── docs/
│   ├── CONTEXT.md                   ← this file
│   ├── REQUIREMENTS.md
│   ├── SETUP.md
│   ├── ARCHITECTURE.md
│   └── DATAMODEL.md
│   ├── ROADMAP.md
│   └── TODO.md
└── storage/
    └── projects/                    Generated video files (gitignored)
```

---

## Commits (chronological)

| Hash | Description |
|------|-------------|
| `0dc1da3` | feat: initial implementation — full pipeline, frontend, backend, docs |
| `545c82f` | feat: Clerk auth + user brand profiles + referral credits |
| `72cb120` | chore: downsize to starter plan — $14.25/mo vs $55/mo |
| `93291e3` | feat: update pricing and scene counts (10s/2sc, 30s/4sc, 60s/8sc) |

---

## Open Issues / Next Steps

### Must-do before first real-money order

1. **Create Stripe products** — 3 prices ($9.99, $19.99, $29.99) in Stripe Dashboard, copy Price IDs to Render env vars
2. **Set all Render env vars** — all `sync: false` vars above
3. **Deploy** — push repo, Blueprint → `render.yaml` in Render Dashboard
4. **Cloudflare DNS** — add `videomagic` CNAME → Render frontend URL on servicevision.io
5. **Stripe webhook** — add `https://videomagic.servicevision.io/api/webhook` in Stripe Dashboard → copy `whsec_` to Render
6. **Veo quota** — file quota increase request via Google Cloud Console before launch
7. **Sprint 0: Cost tracking** — log API costs per project; alert if margin < 40% (see ROADMAP.md Sprint 0 spec)

### Known tech debt

- `composite_overlays()` in `text_overlay.py` builds a chained ffmpeg `filter_complex` that may break with >4 inputs on some ffmpeg versions — needs integration test
- `progress.py` doesn't evict stale queues for abandoned projects (no TTL cleanup)
- SQLite at `/opt/render/project/video_magic.db` is on the persistent disk — good, but consider Turso/PlanetScale for multi-instance scale
- `ProgressTracker.tsx` has no SSE auto-reconnect on network drop
- No `loading.tsx` or `error.tsx` boundaries on `/project/[id]`
- Mobile viewport not optimized (wizard step widths)

---

## Cost History — StrataVault Test Run (reference)

We generated the full 8-scene "Agent Double-O-Data" animation for StrataVault as a test. Actual costs:

| Service | Usage | Cost |
|---------|-------|------|
| Veo 3.1 | 8 scenes | ~$8.00 (est.) |
| ElevenLabs turbo v2.5 | ~550 chars | ~$0.28 |
| Imagen 4 | 13 images (logos + infographics) | ~$0.52 |
| Gemini Flash | ~3,500 tokens | ~$0.001 |
| **Total** | | **~$8.80** |

This was the research/validation run that confirmed the full pipeline works. The Video Magic product automates exactly this workflow for paying customers.

---

## Key Design Decisions

### Why Pillow overlays instead of baking text into Veo?
Veo (and all current video generation models) cannot reliably render readable text. The generated letters are garbled, misspelled, or wrong. By generating text as Pillow PNGs and compositing with ffmpeg at precise timestamps, we guarantee 100% text accuracy on every render.

### Why SQLite instead of Postgres?
Single-server deployment on Render. SQLite in WAL mode handles concurrent reads fine. No connection pooling to configure. The entire DB is a single file on the persistent disk — trivial backup and restore. Migrate to Postgres/Turso when we need multi-instance scale.

### Why BackgroundTask instead of a real job queue?
Sufficient for testing and early revenue. BackgroundTasks run in the same process and die if the server restarts mid-pipeline. The video would be in an incomplete state and the user would need to re-run. Acceptable for early testing. Sprint 3 adds ARQ (Redis-backed) for durability.

### Why Starter plan on Render?
Veo generation is 95% waiting (polling sleep). The process uses ~10 MB RAM while polling. ffmpeg spikes to ~250 MB peak. Starter (512 MB) comfortably covers both. No reason to pay for Standard ($25/mo) until we see actual OOM errors.

### Why one-time payment instead of subscription?
Lower friction for first purchase. "Pay $9.99, get a video" is easier to sell than "sign up for $X/month." Re-runs included at no charge create goodwill. Subscription tier (Sprint 5) comes after proving the core value.
