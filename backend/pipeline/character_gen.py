"""Imagen 4 — generate brand character PNG."""
import io
import os
from pathlib import Path

from google import genai
from google.genai import types
from PIL import Image


def _client() -> genai.Client:
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def generate_character(brand_name: str, brand_description: str, out_path: Path) -> Path:
    """Generate a brand character image using Imagen 4."""
    if out_path.exists():
        return out_path

    client = _client()

    prompt = (
        f"Professional brand character for '{brand_name}'. "
        f"{brand_description}. "
        "Flat vector illustration style, clean geometric lines, bold colors. "
        "Full-body character, centered, transparent-friendly background (white). "
        "No text, no labels. Character only. Square 1:1 aspect ratio."
    )

    resp = client.models.generate_images(
        model="imagen-4.0-generate-001",
        prompt=prompt,
        config=types.GenerateImagesConfig(
            numberOfImages=1,
            aspectRatio="1:1",
            outputMimeType="image/png",
        ),
    )

    if resp.generated_images:
        img_bytes = resp.generated_images[0].image.image_bytes
        img = Image.open(io.BytesIO(img_bytes))
        img.save(out_path, "PNG")
        return out_path

    raise RuntimeError("Imagen 4 returned no images for character generation")
