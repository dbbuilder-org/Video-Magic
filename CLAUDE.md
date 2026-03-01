# CLAUDE.md — Video Magic

## Commands

```bash
# Backend (FastAPI)
cd backend && pip install -r requirements.txt
cp .env.example .env   # fill in API keys
uvicorn main:app --reload --port 8000

# Frontend (Next.js 16)
cd frontend && npm install
cp .env.local.example .env.local   # set BACKEND_URL
npm run dev

# Stripe webhook (local dev)
stripe listen --forward-to localhost:8000/stripe/webhook
```

## Architecture

- **Frontend:** Next.js 16 + Tailwind, `frontend/`
- **Backend:** FastAPI (Python), `backend/`
- **DB:** SQLite via `sqlite3` (no ORM), `video_magic.db`
- **Storage:** `storage/projects/<id>/` per project (videos gitignored)
- **Progress:** asyncio.Queue SSE bus (`backend/progress.py`)

## Pipeline Stages

1. Gemini Flash → parse document → structured JSON spec (5–12%)
2. Imagen 4 → brand character PNG (20–27%)
3. Pillow → title card, lower-thirds, CTA card PNGs (32%)
4. Veo 3.1 → scene videos (35–75%) — ~50s poll per scene
5. ElevenLabs → voiceover MP3 (82%)
6. ffmpeg concat → stitched MP4 (88%)
7. ffmpeg overlay → text composited (93%)
8. ffmpeg mix → final MP4 with ducked audio (100%)

## Critical Rule: Text Accuracy

Veo prompts must contain **zero readable words**. All text renders
via Pillow PNG overlays composited by ffmpeg. Never put text labels
in Veo scene prompts — describe visual action and motion only.

## Key File Paths

- `backend/pipeline/scene_gen.py` — Veo 3.1 generate + poll + URI download
- `backend/pipeline/text_overlay.py` — Pillow text PNGs + ffmpeg composite
- `backend/pipeline/voiceover.py` — ElevenLabs SDK v2 pattern
- `backend/pipeline/assembler.py` — ffmpeg stitch + duck/mix
- `backend/api/generate.py` — full pipeline orchestrator
- `backend/models.py` — SQLite CRUD (no ORM)
- `backend/progress.py` — SSE bus

## Environment Variables (backend)

| Var | Description |
|-----|-------------|
| GEMINI_API_KEY | Google AI key for Gemini Flash + Imagen 4 + Veo 3.1 |
| ELEVENLABS_API_KEY | ElevenLabs for voiceover |
| ELEVENLABS_VOICE_ID | Default: nPczCjzI2devNBz1zQrb (Brian) |
| STRIPE_SECRET_KEY | Stripe secret |
| STRIPE_WEBHOOK_SECRET | Stripe webhook signing secret |
| STRIPE_PRICE_10S/30S/60S | Stripe Price IDs |
| APP_URL | Frontend URL for Stripe redirects |
| STORAGE_DIR | Where to write video files (default: ./storage/projects) |

## Render Deployment

- Services defined in `render.yaml` at repo root
- Backend: Python web service on Render
- Frontend: Node.js web service on Render
- `videomagic.servicevision.io` → Cloudflare CNAME → Render external URL

## Veo 3.1 Quota Note

Free tier: ~7 videos/day before 429 RESOURCE_EXHAUSTED. Working config:
- `aspect_ratio="16:9"` only
- No `duration_seconds`, `fps`, `generate_audio`, `person_generation` params
