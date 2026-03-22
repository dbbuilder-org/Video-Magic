"""ffmpeg — stitch scenes, composite overlays, mix voiceover."""
import os
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
        "-ar", "44100", "-ac", "2",   # normalise audio so mismatched Veo streams don't break concat
        str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg stitch failed:\n{result.stderr[-1000:]}")
    return out_path


TAIL_SILENCE_S = float(os.environ.get("VIDEO_TAIL_SILENCE_S", "1.5"))


def mix_voiceover(video_path: Path, vo_path: Path, out_path: Path) -> Path:
    """Mute native Veo audio, mix in voiceover at full volume.
    Always adds TAIL_SILENCE_S seconds of freeze-frame + silence after VO ends."""
    vid_dur = get_video_duration(video_path)
    vo_dur = get_video_duration(vo_path)
    # Extend video to: max(video, VO) + tail silence
    target_dur = max(vid_dur, vo_dur) + TAIL_SILENCE_S
    extra = target_dur - vid_dur  # always >= TAIL_SILENCE_S

    video_filter = f"[0:v]tpad=stop_mode=clone:stop_duration={extra:.2f}[vout]"
    v_map = "[vout]"

    # Pad VO audio with silence so amix sees the full target duration
    audio_filter = (
        f"[1:a]apad=pad_dur={TAIL_SILENCE_S:.2f}[vopad];"
        "[0:a]volume=0.0[bg];"
        "[bg][vopad]amix=inputs=2:duration=longest[aout]"
    )

    if video_filter:
        filter_complex = f"{video_filter};{audio_filter}"
    else:
        filter_complex = audio_filter

    cmd = [
        FFMPEG, "-y",
        "-i", str(video_path),
        "-i", str(vo_path),
        "-filter_complex", filter_complex,
        "-map", v_map,
        "-map", "[aout]",
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k",
        str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg mix failed:\n{result.stderr[-1000:]}")
    return out_path


def get_video_dimensions(video_path: Path) -> tuple[int, int]:
    """Return (width, height) of the video using ffprobe."""
    ffprobe = shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe"
    cmd = [
        ffprobe, "-v", "quiet",
        "-select_streams", "v:0",
        "-print_format", "json",
        "-show_streams",
        str(video_path),
    ]
    import json
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        streams = json.loads(result.stdout).get("streams", [])
        if streams:
            return int(streams[0]["width"]), int(streams[0]["height"])
    return 1920, 1080  # fallback


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
