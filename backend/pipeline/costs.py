"""API cost constants and per-call estimation helpers."""
from __future__ import annotations

# ── Rates (USD per unit, 2026-03) ────────────────────────────────────────────
GEMINI_FLASH_INPUT_PER_TOKEN  = 0.075 / 1_000_000   # $0.075 / 1M tokens
GEMINI_FLASH_OUTPUT_PER_TOKEN = 0.300 / 1_000_000   # $0.30  / 1M tokens
IMAGEN4_PER_IMAGE             = 0.04                  # $0.04  / image
VEO31_PER_SECOND              = 0.35                  # $0.35  / second of video
ELEVENLABS_TURBO_PER_CHAR     = 0.30 / 1_000          # $0.30  / 1K characters


def est_gemini_flash(input_text: str, output_text: str = "") -> tuple[float, float, float]:
    """Return (input_tokens, output_tokens, cost_usd) estimated from text lengths (4 chars ≈ 1 token)."""
    in_tok  = len(input_text)  / 4
    out_tok = len(output_text) / 4
    cost = (in_tok * GEMINI_FLASH_INPUT_PER_TOKEN +
            out_tok * GEMINI_FLASH_OUTPUT_PER_TOKEN)
    return in_tok, out_tok, cost


def est_imagen4(n_images: int = 1) -> float:
    return n_images * IMAGEN4_PER_IMAGE


def est_veo31(seconds: float = 8.0) -> float:
    return seconds * VEO31_PER_SECOND


def est_elevenlabs(script: str) -> float:
    return len(script) * ELEVENLABS_TURBO_PER_CHAR
