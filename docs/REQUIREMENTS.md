# Requirements — Video Magic

**Version:** 1.0
**Date:** 2026-03-01
**Owner:** Chris Therriault

---

## Problem Statement

Content creators, marketers, and consultants need branded animated videos from their documents (white papers, product briefs, pitch decks, policy docs). Existing AI video tools suffer from two critical flaws:

1. **Text hallucination** — Veo and similar models cannot render readable text reliably. The text in the video is garbled or wrong.
2. **No structured workflow** — raw Veo access requires prompt engineering expertise; there is no document-in → video-out pipeline.

Video Magic solves both by layering Pillow-generated PNG overlays (title cards, lower-thirds, CTAs) composited via ffmpeg, while Veo handles only visual motion (zero text in Veo prompts).

---

## Functional Requirements

### FR-01: Document Ingestion
- Accept plain text input (paste or .txt upload) up to 8,000 characters
- Future: PDF upload via Gemini Files API

### FR-02: AI Script Generation
- Gemini Flash parses document → structured JSON spec:
  - `title`, `tagline`, `key_messages[]`, `scenes[]`, `cta`, `brand_description`
- Scene count driven by duration: 10s=1, 30s=3, 60s=6
- Scene `visual_action` must contain **zero readable words** (enforced by system prompt)

### FR-03: Brand Customization
- Brand name (text overlay on title card + CTA)
- Brand color (hex, used in all overlay PNGs)
- Presets: Navy, Cyan, Gold, Violet, Emerald, Rose

### FR-04: Video Generation Pipeline
- Stage 1: Gemini Flash document parse → 5–12%
- Stage 2: Imagen 4 brand character PNG → 20–27%
- Stage 3: Pillow text overlay PNGs → 32%
- Stage 4: Veo 3.1 per-scene MP4 (1–6 clips) → 35–75%
- Stage 5: ElevenLabs voiceover MP3 → 82%
- Stage 6: ffmpeg concat → 88%
- Stage 7: ffmpeg overlay composite → 93%
- Stage 8: ffmpeg VO duck+mix → 100%

### FR-05: Real-Time Progress
- Server-Sent Events (SSE) stream from FastAPI `/projects/{id}/progress`
- Next.js proxy at `/api/progress/[id]`
- Frontend `ProgressTracker` component shows animated stage list + overall % bar

### FR-06: Text Overlay Accuracy
- Title card: full-frame PNG, 1920×1080, brand color background, shown 0:00–0:03
- Lower-third: 1920×194 PNG (bottom 18%), brand color bar, per-scene caption
- CTA card: full-frame PNG, shown last 3 seconds
- All text rendered by Pillow with system font fallback chain
- ffmpeg `overlay` filter composites at precise timestamps

### FR-07: Voiceover
- ElevenLabs SDK v2 `text_to_speech.convert()`
- Voice: Brian (nPczCjzI2devNBz1zQrb) by default, configurable via env
- Model: `eleven_turbo_v2_5`, `mp3_44100_128`
- Duck native Veo audio to 15%, VO at 100% via ffmpeg amix

### FR-08: Stripe Checkout
- Three Stripe Price IDs (10s/$9.99, 30s/$14.99, 60s/$19.99)
- Hosted Checkout page → success redirect to `/project/{id}?session={SESSION_ID}`
- Webhook `checkout.session.completed` triggers pipeline

### FR-09: Script Editing & Re-run
- `PATCH /projects/{id}/spec` merges updated doc_spec
- Clears doc_spec to re-parse, or accepts pre-edited doc_spec
- Triggers pipeline re-run via BackgroundTask
- Re-runs included in original purchase at no extra charge

### FR-10: Video Delivery
- Final MP4 served via FastAPI StaticFiles at `/storage/{project_id}/final.mp4`
- In-browser HTML5 video player with download button
- CORS configured for frontend origin

---

## Non-Functional Requirements

### NFR-01: Performance
- Veo generation: ~50s per scene (API constraint, not app constraint)
- Total pipeline: 5–20 minutes depending on duration
- SSE heartbeat every 30s to keep connection alive

### NFR-02: Reliability
- Pipeline wrapped in try/except → stores error in DB + emits SSE error event
- User can re-run from any failure state via ScriptEditor

### NFR-03: Security
- Stripe webhook signature verified (`stripe.Webhook.construct_event`)
- No API keys in frontend code
- CORS restricted to production origin
- SQLite with WAL mode for concurrent reads

### NFR-04: Scalability (current scope)
- Single-server: Render Standard (2 CPU, 2 GB RAM)
- Storage: Render persistent disk 20 GB
- Horizontal scale: add Render worker services + job queue (future)

---

## Out of Scope (v1)

- User accounts / authentication
- PDF upload
- Multiple voiceover voices (UI)
- Video trimming / timeline editor
- Watermark removal
- Webhooks to external systems
