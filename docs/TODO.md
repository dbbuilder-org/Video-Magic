> **Superseded by:** [ROADMAP-2026-03-02](ROADMAP-2026-03-02.md) — Updated 2026-03-02

# TODO — Video Magic

**Date:** 2026-03-01
**Status:** MVP shipped. Ready for deployment.

---

## Immediate (before first real user)

- [ ] **Create Stripe products** — create 3 prices in Stripe Dashboard, add price IDs to Render env vars
- [ ] **Set all Render env vars** — GEMINI_API_KEY, ELEVENLABS_API_KEY, all STRIPE_* vars
- [ ] **Deploy to Render** — push repo, link `render.yaml` in Render Dashboard
- [ ] **Cloudflare DNS** — add CNAME `videomagic` → Render frontend URL on servicevision.io zone
- [ ] **SSL verify** — confirm `videomagic.servicevision.io` returns HTTPS
- [ ] **Stripe webhook** — add `https://videomagic.servicevision.io/api/webhook` in Stripe Dashboard
- [ ] **End-to-end test** — buy a real 10s video, verify pipeline completes

---

## Known Issues / Tech Debt

- [ ] **ffmpeg overlay filter chain** — `composite_overlays()` in `text_overlay.py` builds a chained filter_complex that may break with >4 inputs on some ffmpeg versions. Add integration test.
- [ ] **Progress bus cleanup** — `progress.py` doesn't evict stale queues for abandoned projects. Add TTL-based cleanup.
- [ ] **Veo quota** — Free tier is ~7 videos/day. Need production quota increase via Google Cloud. File quota increase request before launch.
- [ ] **SSE reconnect** — `ProgressTracker.tsx` doesn't implement EventSource auto-reconnect on network drop. Add `es.onerror` retry with backoff.
- [ ] **Database path on Render** — SQLite at `/opt/render/project/video_magic.db` is on the ephemeral disk. Move to persistent disk or consider PlanetScale/Turso for production.
- [ ] **Missing `.env.local.example`** — frontend env example file not yet created.

---

## Post-Deploy Polish

- [ ] Add `loading.tsx` to `/project/[id]` route for better Suspense UX
- [ ] Add `error.tsx` boundary to `/project/[id]`
- [ ] OG meta tags on landing page for social sharing
- [ ] Add favicon and `apple-icon` assets
- [ ] Test on mobile viewport (wizard is not mobile-optimized yet)

---

## Completed

- [x] FastAPI backend skeleton + models + progress bus
- [x] Full 8-stage pipeline (parse → character → overlays → Veo × N → VO → stitch → composite → mix)
- [x] Next.js 16 frontend: landing, wizard, project view
- [x] All 7 components: PricingCards, WizardUpload, WizardBrand, WizardDuration, ProgressTracker, ScriptEditor, VideoPlayer
- [x] Stripe Checkout + webhook routes (frontend proxy + backend handler)
- [x] SSE progress stream (asyncio.Queue → EventSource)
- [x] Script editor with PATCH + re-run
- [x] render.yaml deployment config
- [x] Full doc suite: REQUIREMENTS, SETUP, ARCHITECTURE, DATAMODEL, ROADMAP, TODO
