# Architecture — Video Magic

---

## System Overview

```
Browser (Next.js 16)
    │
    ├─ GET /  → Landing page (RSC)
    ├─ GET /create → 3-step wizard (client)
    ├─ POST /api/checkout → proxy → FastAPI /stripe/checkout
    ├─ POST /api/webhook → proxy → FastAPI /stripe/webhook
    └─ GET /api/progress/[id] → proxy SSE → FastAPI /projects/{id}/progress

FastAPI (Python)
    │
    ├─ POST /stripe/checkout → create project → Stripe Checkout Session
    ├─ POST /stripe/webhook → verify sig → start BackgroundTask
    ├─ GET /projects/{id} → SQLite read
    ├─ GET /projects/{id}/progress → SSE stream (asyncio.Queue)
    ├─ PATCH /projects/{id}/spec → merge spec → restart pipeline
    └─ GET /storage/{id}/final.mp4 → StaticFiles

Pipeline (BackgroundTask in FastAPI)
    ├─ 1. Gemini Flash → parse_document() → JSON spec
    ├─ 2. Imagen 4 → generate_character() → PNG
    ├─ 3. Pillow → make_title_card() + make_lower_third() × N + make_cta_card()
    ├─ 4. Veo 3.1 → generate_scene() × N → MP4 per scene
    ├─ 5. ElevenLabs → generate_voiceover() → MP3
    ├─ 6. ffmpeg → stitch_scenes() → stitched.mp4
    ├─ 7. ffmpeg → composite_overlays() → overlaid.mp4
    └─ 8. ffmpeg → mix_voiceover() → final.mp4
```

---

## Component Map

### Frontend (`frontend/`)

```
app/
  page.tsx                    # Landing page — RSC, no client JS
  layout.tsx                  # Root layout + globals.css
  create/page.tsx             # Wizard — client, manages WizardState
  project/[id]/page.tsx       # Project view — client, SSE, tabs
  api/
    checkout/route.ts         # Proxy to FastAPI /stripe/checkout
    webhook/route.ts          # Proxy to FastAPI /stripe/webhook
    progress/[id]/route.ts    # SSE proxy to FastAPI /projects/{id}/progress

components/
  PricingCards.tsx            # Static pricing grid
  WizardUpload.tsx            # Step 1 — document text input
  WizardBrand.tsx             # Step 2 — brand name + color picker
  WizardDuration.tsx          # Step 3 — duration select + checkout
  ProgressTracker.tsx         # SSE-driven animated stage list
  ScriptEditor.tsx            # Editable doc_spec → PATCH + re-run
  VideoPlayer.tsx             # HTML5 video + download button
```

### Backend (`backend/`)

```
main.py                       # FastAPI app, CORS, StaticFiles, startup
models.py                     # SQLite: projects + jobs tables, CRUD
progress.py                   # asyncio.Queue SSE bus
storage.py                    # Path helpers for project file layout
api/
  projects.py                 # GET/PATCH /projects/{id}, SSE route
  stripe_routes.py            # POST /stripe/checkout + /webhook
  generate.py                 # Pipeline orchestrator (BackgroundTask)
pipeline/
  document_parser.py          # Gemini Flash → JSON spec
  character_gen.py            # Imagen 4 → character PNG
  scene_gen.py                # Veo 3.1 → MP4 per scene (poll + URI)
  text_overlay.py             # Pillow PNGs + ffmpeg overlay composite
  voiceover.py                # ElevenLabs SDK v2
  assembler.py                # ffmpeg concat + duck/mix
```

---

## Data Flow: Payment → Video

```
1. User submits wizard → POST /api/checkout
2. Backend creates project (status=pending, spec=JSON)
3. Backend returns Stripe Checkout URL
4. User pays → Stripe sends POST /stripe/webhook
5. Webhook verifies sig → calls bg.add_task(run_pipeline, id, spec)
6. User is on /project/{id} — SSE connected to /projects/{id}/progress
7. Pipeline runs:
     Each stage:
       - upsert_job() → SQLite
       - emit_async() → asyncio.Queue → SSE → browser
       - ProgressTracker updates UI
8. Pipeline writes final.mp4 to /storage/{id}/final.mp4
9. update_project(status="done", video_url="/storage/{id}/final.mp4")
10. emit_async(stage="done", pct=100, detail=video_url)
11. Browser receives "done" event → shows VideoPlayer
```

---

## Database Schema

### `projects`
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PK | UUID |
| status | TEXT | `pending` / `running` / `done` / `error` |
| spec | TEXT | JSON: `{duration, brand_name, brand_color, document_text, doc_spec?}` |
| video_url | TEXT | Relative path: `/storage/{id}/final.mp4` |
| error | TEXT | Error message if status=error |
| created_at | TEXT | ISO8601 UTC |
| updated_at | TEXT | ISO8601 UTC |

### `jobs`
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PK | UUID |
| project_id | TEXT FK | → projects.id |
| stage | TEXT | Stage key (e.g. `scene_0`, `voiceover`) |
| pct | INTEGER | 0–100 |
| status | TEXT | `pending` / `running` / `done` / `error` |
| detail | TEXT | Human-readable detail or error |
| created_at | TEXT | ISO8601 UTC |
| updated_at | TEXT | ISO8601 UTC |

---

## Storage Layout

```
storage/projects/{project_id}/
  character.png               # Imagen 4 brand character
  voiceover.mp3               # ElevenLabs narration
  concat.txt                  # ffmpeg concat list
  stitched.mp4                # scenes concatenated (intermediate)
  overlaid.mp4                # text overlays composited (intermediate)
  final.mp4                   # ★ served to user
  scenes/
    scene_00.mp4              # Veo clip 0
    scene_01.mp4              # Veo clip 1
    ...
  overlays/
    title_card.png            # Pillow full-frame title
    lower_00.png              # Pillow lower-third, scene 0
    lower_01.png              # ...
    cta_card.png              # Pillow CTA overlay
```

---

## SSE Progress Bus

```python
# backend/progress.py
_queues: dict[str, list[asyncio.Queue]]

emit_async(project_id, stage, pct, detail)  # puts JSON on all subscriber queues
subscribe(project_id)                        # async generator yielding "data: {...}\n\n"
```

Multiple browser tabs on the same project get independent Queue subscriptions. The generator auto-closes after `pct == 100` or `stage == "error"`, with a 30s keepalive ping.

---

## Text Overlay Architecture

**Rule:** Veo prompts contain **zero readable words**.

```
Pillow generates:
  title_card.png  → 1920×1080 RGBA, shown t=0 to t=3
  lower_N.png     → 1920×194 RGBA, shown at scene boundaries
  cta_card.png    → 1920×1080 RGBA, shown t=(total-3) to t=end

ffmpeg filter_complex:
  [0:v][1:v]overlay=0:0:enable='between(t,0,3.00)'[v0]
  [v0][2:v]overlay=0:H-194:enable='between(t,0.5,8.0)'[v1]
  ...
  → libx264 encode
```

Result: text is 100% accurate because Pillow renders it — not a video model.

---

## Render Deployment Architecture

```
Cloudflare DNS
  videomagic.servicevision.io  →  CNAME  →  video-magic-frontend.onrender.com

Render (Oregon)
  video-magic-frontend (Node 20, Standard)
    npm run start (Next.js)
    Env: BACKEND_URL → internal service reference
    ↓ proxies /api/backend/* and SSE

  video-magic-api (Python 3.11, Standard)
    uvicorn main:app
    Disk: /opt/render/project/storage  (20 GB persistent)
    SQLite: /opt/render/project/video_magic.db
```
