# Roadmap — Video Magic

**Last updated:** 2026-03-01

---

## MVP (v1.0) — Shipped

- [x] 3-step wizard (Upload → Brand → Duration/Pay)
- [x] Stripe Checkout (3 price tiers: $9.99 / $14.99 / $19.99)
- [x] Gemini Flash document parser → structured scene JSON
- [x] Imagen 4 brand character generation
- [x] Pillow title card + lower-thirds + CTA overlays (100% accurate text)
- [x] Veo 3.1 scene generation (1/3/6 clips) with poll + URI download
- [x] ElevenLabs voiceover (Brian voice, turbo v2.5)
- [x] ffmpeg stitch + overlay composite + VO duck+mix
- [x] SSE real-time progress tracker
- [x] Script editor + free re-run
- [x] SQLite database (projects + jobs)
- [x] FastAPI backend + Next.js 16 frontend
- [x] Render deployment config (`render.yaml`)
- [x] Cloudflare DNS: `videomagic.servicevision.io`

---

## Sprint 1 — Quality & Polish (est. 8 SP)

- [ ] PDF upload via Gemini Files API (mulitpart form in FastAPI)
- [ ] Font loading improvement — download Inter/Roboto to `backend/assets/fonts/`
- [ ] Aspect ratio: 9:16 option for Reels/Shorts (requires Veo config change)
- [ ] Preview mode: generate title card PNG + script without paying
- [ ] Email notification on completion (Resend SDK)

## Sprint 2 — Auth & Accounts (est. 12 SP)

- [ ] Magic-link auth (Resend email → JWT)
- [ ] User account: view all past projects
- [ ] Project library page with thumbnails (ffmpeg frame extract)
- [ ] Multiple voiceover voices (dropdown in WizardBrand)

## Sprint 3 — Scale & Performance (est. 10 SP)

- [ ] Job queue: replace BackgroundTask with ARQ (Redis-backed) for durability
- [ ] Multi-worker support: Render auto-scale workers
- [ ] Storage: migrate from Render disk to R2 (Cloudflare) for CDN delivery
- [ ] Video thumbnail generation for library view
- [ ] Retry logic for Veo 429 quota exhaustion (exponential backoff)

## Sprint 4 — New Formats (est. 15 SP)

- [ ] YouTube intro (16:9, 15s, animated logo + brand colors, no Veo needed)
- [ ] Slide-to-video: accept PowerPoint/Google Slides, one scene per slide
- [ ] Batch mode: generate multiple durations from one document, bundle pricing
- [ ] White-label: custom domain per client, logo on title card

## Sprint 5 — Analytics & Revenue (est. 6 SP)

- [ ] Stripe Customer Portal: view purchase history, re-download
- [ ] Usage dashboard: videos generated, revenue, avg processing time
- [ ] Affiliate / referral code system
- [ ] Annual subscription tier: unlimited re-runs at $49/month

---

## Deferred / Under Consideration

- Timeline editor (drag scenes, trim clips) — complex, low ROI in v1
- Background music library — licensing complexity
- Subtitles/captions file (SRT) export — medium complexity
- Enterprise: SSO, team seats, usage limits
- On-premise Docker deployment
