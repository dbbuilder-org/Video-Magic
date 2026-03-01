"""ffmpeg — stitch scenes, composite overlays, mix voiceover."""
import shutil
import subprocess
from pathlib import Path
from typing import Sequence

FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"


def stitch_scenes(scene_paths: Sequence[Path], out_path: Path) -> Path:
    """Concatenate scene MP4 files using ffmpeg concat demuxer."""
    concat_list = out_path.parent / "concat.txt"
    with open(concat_list, "w") as f:
        for sp in scene_paths:
            f.write(f"file '{sp.absolute()}'\n")

    cmd = [
        FFMPEG, "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k",
        str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg stitch failed:\n{result.stderr[-1000:]}")
    return out_path


def mix_voiceover(video_path: Path, vo_path: Path, out_path: Path) -> Path:
    """Duck native audio to 15%, mix in voiceover at full volume."""
    cmd = [
        FFMPEG, "-y",
        "-i", str(video_path),
        "-i", str(vo_path),
        "-filter_complex",
        "[0:a]volume=0.15[bg]; [1:a]volume=1.0[vo]; [bg][vo]amix=inputs=2:duration=first[aout]",
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg mix failed:\n{result.stderr[-1000:]}")
    return out_path


def get_video_duration(video_path: Path) -> float:
    """Return video duration in seconds using ffprobe."""
    ffprobe = shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe"
    cmd = [
        ffprobe, "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        str(video_path),
    ]
    import json
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return 8.0  # fallback
    data = json.loads(result.stdout)
    return float(data["format"].get("duration", 8.0))
