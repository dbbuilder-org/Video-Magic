# Data Model — Video Magic

---

## SQLite Tables

### `projects`

```sql
CREATE TABLE projects (
    id          TEXT PRIMARY KEY,        -- UUID v4
    status      TEXT NOT NULL DEFAULT 'pending',
                                         -- pending | running | done | error
    spec        TEXT NOT NULL DEFAULT '{}',
                                         -- JSON blob (see Spec Schema below)
    video_url   TEXT,                    -- /storage/{id}/final.mp4
    error       TEXT,                    -- last error message
    created_at  TEXT NOT NULL,           -- ISO8601 UTC, e.g. 2026-03-01T14:22:00Z
    updated_at  TEXT NOT NULL
);
```

### `jobs`

```sql
CREATE TABLE jobs (
    id          TEXT PRIMARY KEY,        -- UUID v4
    project_id  TEXT NOT NULL REFERENCES projects(id),
    stage       TEXT NOT NULL,           -- stage key, e.g. "scene_0", "voiceover"
    pct         INTEGER NOT NULL DEFAULT 0,  -- 0–100
    status      TEXT NOT NULL DEFAULT 'pending',
                                         -- pending | running | done | error
    detail      TEXT,                    -- human-readable or error traceback
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE INDEX idx_jobs_project_id ON jobs(project_id);
```

---

## Project Spec JSON Schema

The `spec` column stores a JSON object that evolves through the pipeline:

```json
{
  "duration": 30,
  "brand_name": "Acme Corp",
  "brand_color": "#1A56DB",
  "document_text": "... raw input text ...",
  "doc_spec": {
    "title": "Acme Corp — The Future of Widgets",
    "tagline": "Faster. Smarter. Better.",
    "key_messages": [
      "40% reduction in costs",
      "Ships in 3 days"
    ],
    "scenes": [
      {
        "index": 0,
        "caption": "40% Cost Reduction",
        "visual_action": "Animated bar chart bars growing upward in bold colors, confetti bursting, celebration energy",
        "vo_text": "Acme Corp reduces your operational costs by 40% in the first quarter."
      }
    ],
    "cta": "Visit acme.com/demo",
    "brand_description": "Professional B2B SaaS, clean blues and whites, confident modern aesthetic"
  }
}
```

### Spec Fields

| Field | Type | Stage Set | Description |
|-------|------|-----------|-------------|
| `duration` | int | Wizard | 10, 30, or 60 |
| `brand_name` | string | Wizard | Company/brand name |
| `brand_color` | string | Wizard | Hex color, e.g. `#1A56DB` |
| `document_text` | string | Wizard | Raw input, max 8,000 chars |
| `doc_spec` | object | Pipeline stage 1 | Set by Gemini Flash parser |
| `doc_spec.title` | string | Stage 1 | 5–8 word title for title card |
| `doc_spec.tagline` | string | Stage 1 | One-line tagline, max 10 words |
| `doc_spec.key_messages` | string[] | Stage 1 | Bullet points from document |
| `doc_spec.scenes` | object[] | Stage 1 | Per-scene spec (see below) |
| `doc_spec.cta` | string | Stage 1 | CTA text for closing card |
| `doc_spec.brand_description` | string | Stage 1 | Visual style for Imagen 4 |

### Scene Object

| Field | Type | Description |
|-------|------|-------------|
| `index` | int | 0-based scene index |
| `caption` | string | Lower-third text, max 8 words |
| `visual_action` | string | Veo prompt — **NO readable words** — motion/imagery only |
| `vo_text` | string | ElevenLabs narration for this scene |

---

## Stage Keys

| Key | Description | Target % |
|-----|-------------|---------|
| `parse_document` | Gemini Flash parsing | 12 |
| `character_gen` | Imagen 4 character | 27 |
| `text_overlays` | Pillow PNG generation | 32 |
| `scene_0` | Veo clip 0 | 45 |
| `scene_1` | Veo clip 1 | 55 |
| `scene_2` | Veo clip 2 | 65 |
| `scene_3` | Veo clip 3 | 68 |
| `scene_4` | Veo clip 4 | 71 |
| `scene_5` | Veo clip 5 | 75 |
| `voiceover` | ElevenLabs VO | 82 |
| `stitch` | ffmpeg concat | 88 |
| `overlay` | ffmpeg composite | 93 |
| `mix` | ffmpeg duck+mix | 100 |
| `done` | Complete | 100 |
| `error` | Failed | — |

---

## SSE Event Shape

```json
{ "stage": "scene_0", "pct": 45, "detail": "120s elapsed" }
```

Clients disconnect when `pct === 100` or `stage === "error"`.

---

## File Storage

All paths relative to `STORAGE_DIR` (default: `./storage/projects`):

```
{project_id}/
  character.png        Imagen 4 output
  voiceover.mp3        ElevenLabs output
  concat.txt           ffmpeg input list
  stitched.mp4         Intermediate: scenes joined
  overlaid.mp4         Intermediate: text composited
  final.mp4            ★ Final deliverable
  scenes/
    scene_00.mp4
    scene_01.mp4
    ...
  overlays/
    title_card.png
    lower_00.png
    lower_01.png
    ...
    cta_card.png
```

---

## Status Lifecycle

```
pending  →  running  →  done
                ↓
              error
```

Re-run resets status to `running` and clears `error`. `video_url` is only set on `done`.
