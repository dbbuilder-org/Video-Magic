"""Gemini Flash — parse document into key messages and scene breakdown."""
import json
import os
from typing import Any

from google import genai
from google.genai import types


def _client() -> genai.Client:
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


PARSE_SYSTEM = """You are a professional video scriptwriter. Given a document excerpt and metadata,
extract the key messages and produce a structured video script as JSON.

Return ONLY valid JSON in this exact shape:
{
  "title": "<compelling 5-8 word title>",
  "tagline": "<one-line tagline, max 10 words>",
  "key_messages": ["<message 1>", "<message 2>", ...],
  "scenes": [
    {
      "index": 0,
      "caption": "<lower-third text, max 8 words>",
      "visual_action": "<describe the VISUAL ACTION only — no readable words in prompt, describe motion and imagery>",
      "vo_text": "<voiceover narration for this scene, 1-3 sentences>"
    }
  ],
  "cta": "<call-to-action text, e.g. 'Visit acme.com/demo'>",
  "brand_description": "<visual style for character/brand: colors, mood, industry>"
}

Scene count must match the duration: 10s→1 scene, 30s→3 scenes, 60s→6 scenes.
visual_action must contain ZERO readable words — describe motion, color, objects only.
"""


def parse_document(text: str, duration: int, brand_name: str, brand_color: str = "#1A56DB") -> dict[str, Any]:
    """Parse document text into structured video spec using Gemini Flash."""
    client = _client()

    scene_count = {10: 1, 30: 3, 60: 6}.get(duration, 3)

    user_prompt = (
        f"Brand: {brand_name}\n"
        f"Brand color: {brand_color}\n"
        f"Video duration: {duration} seconds ({scene_count} scene{'s' if scene_count > 1 else ''})\n\n"
        f"Document:\n{text[:8000]}"
    )

    resp = client.models.generate_content(
        model="gemini-2.0-flash-001",
        contents=[
            types.Content(role="user", parts=[types.Part(text=user_prompt)])
        ],
        config=types.GenerateContentConfig(
            system_instruction=PARSE_SYSTEM,
            temperature=0.4,
            response_mime_type="application/json",
        ),
    )

    raw = resp.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)
