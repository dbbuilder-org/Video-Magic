> **Superseded by:** [ROADMAP-2026-03-02](ROADMAP-2026-03-02.md) — Updated 2026-03-02

# Roadmap — Video Magic

**Last updated:** 2026-03-01 (rev 2)

---

## v1.1 — Auth + Social (shipped 2026-03-01)

- [x] Clerk auth — sign-in / sign-up pages with branded appearance
- [x] Middleware route protection (`/create`, `/project/:id`)
- [x] User brand profile — saved across projects, pre-filled in wizard
- [x] Referral system — unique codes, $5 credit on first referred purchase
- [x] Credit display + auto-apply at Stripe checkout (dynamic Stripe coupon)
- [x] Ownership enforcement on all project API routes (`X-User-Id` header)
- [x] `UserButton` in nav on landing + create + project pages

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

## Sprint 0 — Cost Tracking (CRITICAL — do before first real user)

**Every video generation call costs real money. We must track and alert on costs.**

### What to build
- [ ] **`api_costs` table** — log every external API call: `(project_id, provider, model, units, unit_type, cost_usd, created_at)`. Units = tokens for Gemini, seconds for Veo, characters for ElevenLabs.
- [ ] **Cost constants** — define in `backend/costs.py`:
  - Gemini Flash 2.0: input $0.075/1M tokens, output $0.30/1M tokens
  - Imagen 4: $0.04 per image
  - Veo 3.1: pricing TBD (check Google AI pricing page before launch)
  - ElevenLabs turbo v2.5: $0.0005/character
- [ ] **`pipeline/cost_logger.py`** — call `log_cost(project_id, provider, model, units, unit_type)` after each API call; auto-converts to USD using constants
- [ ] **`GET /projects/{id}/cost-breakdown`** — returns itemized + total cost per project
- [ ] **`GET /admin/costs`** — total costs by day/week, cost per video by duration, gross margin (price_charged - api_costs)
- [ ] **Margin alert** — if `api_cost > price_charged * 0.6`, emit a warning log. A 60s video must not cost more than $12 in API calls on a $19.99 sale.
- [ ] **Render env var** `COST_ALERT_EMAIL` — send email when margin < 40% (use Resend)

### Estimated API cost per video (updated pricing: $9.99 / $19.99 / $29.99)
| Duration | Scenes | Gemini Flash | Imagen 4 | Veo 3.1 est. | ElevenLabs | **Total est.** | Price | **Margin** |
|----------|--------|-------------|----------|-------------|-----------|--------------|-------|-----------|
| 10s | 2 | ~$0.02 | $0.04 | ~$2.00 | ~$0.05 | **~$2.11** | $9.99 | **~79%** |
| 30s | 4 | ~$0.03 | $0.04 | ~$4.00 | ~$0.10 | **~$4.17** | $19.99 | **~79%** |
| 60s | 8 | ~$0.04 | $0.04 | ~$8.00 | ~$0.18 | **~$8.26** | $29.99 | **~72%** |

**Gross margins ~72–79%.** Veo pricing is not yet published; $1/scene is an estimate. Monitor via Sprint 0 cost tracking.

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
