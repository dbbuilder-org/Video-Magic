# Setup Guide — Video Magic

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.11+ | `brew install python` |
| Node.js | 20+ | `brew install node` |
| ffmpeg | any recent | `brew install ffmpeg` |
| Stripe CLI | latest | `brew install stripe/stripe-cli/stripe` |

---

## 1. Clone & Structure

```bash
git clone <your-repo> ~/dev2/Video-Magic
cd ~/dev2/Video-Magic
```

---

## 2. Backend Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
```

Edit `backend/.env`:

```env
GEMINI_API_KEY=AIzaS...          # Google AI Studio → https://aistudio.google.com/apikey
ELEVENLABS_API_KEY=sk_...         # ElevenLabs → https://elevenlabs.io/app/settings/api-keys
STRIPE_SECRET_KEY=sk_test_...     # Stripe Dashboard → Developers → API keys
STRIPE_WEBHOOK_SECRET=whsec_...   # Created when you run `stripe listen` below
STRIPE_PRICE_10S=price_...        # Stripe Dashboard → Products → create 3 prices
STRIPE_PRICE_30S=price_...
STRIPE_PRICE_60S=price_...
APP_URL=http://localhost:3000
```

### Create Stripe Products

In Stripe Dashboard:
1. Products → Add product → "10-Second Video" → $9.99 one-time
2. Products → Add product → "30-Second Video" → $14.99 one-time
3. Products → Add product → "60-Second Video" → $19.99 one-time

Copy the `price_...` IDs into `.env`.

### Start Backend

```bash
cd backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000
# API docs: http://localhost:8000/docs
```

---

## 3. Frontend Setup

```bash
cd frontend
npm install

# Create env file
cat > .env.local <<EOF
BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
EOF

npm run dev
# http://localhost:3000
```

---

## 4. Stripe Webhook (local)

```bash
stripe login
stripe listen --forward-to http://localhost:8000/stripe/webhook
# Copy the whsec_... into backend/.env as STRIPE_WEBHOOK_SECRET
# Restart the backend after updating .env
```

---

## 5. Test the Full Flow

1. Open http://localhost:3000
2. Click "Create Your Video"
3. Paste some text (e.g., a product description)
4. Set brand name + color
5. Choose duration
6. Click Pay — Stripe test card: `4242 4242 4242 4242`, any future date + CVV
7. You land on `/project/{id}` and the pipeline starts
8. Watch progress in real time

> **Note:** Veo generation takes 1–5 minutes per scene. Total time: 5–20 minutes.

---

## 6. Development Tips

```bash
# Skip Stripe for local testing — trigger pipeline directly:
curl -X POST http://localhost:8000/stripe/webhook \
  -H "Content-Type: application/json" \
  -H "stripe-signature: test" \
  -d '{"type":"checkout.session.completed","data":{"object":{"metadata":{"project_id":"YOUR_ID"}}}}'

# Check project state:
curl http://localhost:8000/projects/{id}

# Watch SSE stream:
curl -N http://localhost:8000/projects/{id}/progress
```

---

## 7. Render Deployment

See [SETUP.md#render] or `render.yaml` in the root. Quick steps:

```bash
# Install Render CLI
brew install render

# Link repo in Render Dashboard → New → Blueprint → point to repo
# Render reads render.yaml and creates both services

# Set env vars in Render Dashboard → Environment (sync: false vars)
# Then deploy:
render deploy
```

After deploy, add Cloudflare CNAME:
- `videomagic.servicevision.io` → CNAME → your Render frontend service URL
- Set SSL/TLS to Full in Cloudflare

Update Render env vars:
- `APP_URL` → `https://videomagic.servicevision.io`
- `CORS_ORIGINS` → `https://videomagic.servicevision.io`

Update Stripe webhook endpoint in Stripe Dashboard to `https://videomagic.servicevision.io/api/webhook`.

---

## Environment Variables Reference

### Backend (`.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google AI key (Gemini Flash + Imagen 4 + Veo 3.1) |
| `ELEVENLABS_API_KEY` | Yes | ElevenLabs API key |
| `ELEVENLABS_VOICE_ID` | No | Default: `nPczCjzI2devNBz1zQrb` (Brian) |
| `STRIPE_SECRET_KEY` | Yes | Stripe secret key (`sk_live_...` or `sk_test_...`) |
| `STRIPE_WEBHOOK_SECRET` | Yes | Stripe webhook signing secret |
| `STRIPE_PRICE_10S` | Yes | Stripe Price ID for $9.99 |
| `STRIPE_PRICE_30S` | Yes | Stripe Price ID for $14.99 |
| `STRIPE_PRICE_60S` | Yes | Stripe Price ID for $19.99 |
| `APP_URL` | Yes | Frontend URL for Stripe redirect |
| `CORS_ORIGINS` | No | Comma-separated origins; default: `http://localhost:3000` |
| `STORAGE_DIR` | No | Video storage path; default: `./storage/projects` |
| `DATABASE_PATH` | No | SQLite path; default: `./video_magic.db` |

### Frontend (`.env.local`)

| Variable | Required | Description |
|----------|----------|-------------|
| `BACKEND_URL` | Yes | Backend API URL (server-side) |
| `NEXT_PUBLIC_BACKEND_URL` | Yes | Backend API URL (client-side, for video URLs) |
