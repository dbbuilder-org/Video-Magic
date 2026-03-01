"""ElevenLabs v2 — generate voiceover MP3."""
import os
from pathlib import Path


def generate_voiceover(script: str, out_path: Path) -> Path:
    """Generate narration using ElevenLabs SDK v2."""
    if out_path.exists():
        return out_path

    api_key = os.environ.get("ELEVENLABS_API_KEY", "")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY not set")

    from elevenlabs.client import ElevenLabs

    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "nPczCjzI2devNBz1zQrb")
    eleven = ElevenLabs(api_key=api_key)

    # SDK v2: text_to_speech.convert() returns a bytes iterator
    audio_iter = eleven.text_to_speech.convert(
        voice_id=voice_id,
        text=script,
        model_id="eleven_turbo_v2_5",
        output_format="mp3_44100_128",
        voice_settings={
            "stability": 0.70,
            "similarity_boost": 0.80,
            "speed": 0.90,
        },
    )
    audio_bytes = b"".join(audio_iter)
    out_path.write_bytes(audio_bytes)
    return out_path
