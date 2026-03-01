"""Veo 3.1 — generate scene video, poll, and download."""
import os
import time
import urllib.request
from pathlib import Path
from typing import Callable

from google import genai
from google.genai import types

POLL_INTERVAL = 10
MAX_POLL_WAIT = 360
VIDEO_MODEL = "veo-3.1-generate-preview"


def _client() -> genai.Client:
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def _download_uri(uri: str, out_path: Path) -> bool:
    api_key = os.environ["GEMINI_API_KEY"]
    sep = "&" if "?" in uri else "?"
    url = f"{uri}{sep}key={api_key}"
    try:
        urllib.request.urlretrieve(url, str(out_path))
        return True
    except Exception as e:
        print(f"    URI download failed: {e}")
        return False


def generate_scene(
    prompt: str,
    out_path: Path,
    on_poll: Callable[[int], None] | None = None,
) -> Path:
    """Generate a single scene video using Veo 3.1.

    on_poll(elapsed_seconds) is called after each poll iteration so callers
    can emit progress updates.
    """
    if out_path.exists():
        return out_path

    client = _client()

    # Veo 3.1 prompts must contain ZERO readable words per the text-overlay rule.
    operation = client.models.generate_videos(
        model=VIDEO_MODEL,
        prompt=prompt,
        config=types.GenerateVideosConfig(
            aspect_ratio="16:9",
        ),
    )

    elapsed = 0
    while operation.done is not True:
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL
        operation = client.operations.get(operation)
        if on_poll:
            on_poll(elapsed)
        if elapsed >= MAX_POLL_WAIT:
            raise TimeoutError(f"Veo timed out after {elapsed}s")

    if not operation.response or not operation.response.generated_videos:
        error_msg = getattr(operation, "error", "No video returned")
        raise RuntimeError(f"Veo returned no video: {error_msg}")

    video = operation.response.generated_videos[0].video

    if hasattr(video, "video_bytes") and video.video_bytes:
        out_path.write_bytes(video.video_bytes)
        return out_path

    if hasattr(video, "uri") and video.uri:
        if _download_uri(video.uri, out_path):
            return out_path

    raise RuntimeError("Could not retrieve video bytes or URI from Veo response")
