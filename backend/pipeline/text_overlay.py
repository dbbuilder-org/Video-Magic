"""Pillow — generate text overlay PNGs; ffmpeg composite at timestamps."""
import subprocess
import shutil
import textwrap
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageDraw, ImageFont


FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
W, H = 1920, 1080
LOWER_H = int(H * 0.18)   # Lower-third bar height
TITLE_H = H                # Full-frame title card


def _fit_text(draw: ImageDraw.Draw, text: str, max_width: int, start_size: int) -> tuple[ImageFont.FreeTypeFont | ImageFont.ImageFont, list[str]]:
    """Return (font, lines) that fit within max_width by wrapping then shrinking."""
    for size in range(start_size, 20, -4):
        font = _font(size)
        # Try progressively more aggressive wrapping
        for max_chars in range(60, 10, -5):
            lines = textwrap.wrap(text, width=max_chars) or [text]
            if all(draw.textbbox((0, 0), ln, font=font)[2] <= max_width for ln in lines):
                return font, lines
    font = _font(24)
    return font, textwrap.wrap(text, width=40) or [text]


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load system font with fallback."""
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def make_title_card(
    title: str,
    tagline: str,
    brand_color: str,
    brand_name: str,
    out_path: Path,
) -> Path:
    """Full-frame title card PNG with brand color background."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Semi-transparent dark background
    overlay = Image.new("RGBA", (W, H), (10, 20, 40, 200))
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    # Brand color accent bar at top
    try:
        r, g, b = int(brand_color[1:3], 16), int(brand_color[3:5], 16), int(brand_color[5:7], 16)
    except Exception:
        r, g, b = 26, 86, 219
    draw.rectangle([(0, 0), (W, 12)], fill=(r, g, b, 255))
    draw.rectangle([(0, H - 12), (W, H)], fill=(r, g, b, 255))

    # Title text — auto-wrap and shrink to fit
    title_font, title_lines = _fit_text(draw, title, int(W * 0.88), 96)
    tagline_font = _font(48)
    brand_font = _font(36)

    line_h = draw.textbbox((0, 0), "Ag", font=title_font)[3] + 8
    total_title_h = line_h * len(title_lines)
    ty = H // 2 - total_title_h // 2 - 40
    for ln in title_lines:
        bbox = draw.textbbox((0, 0), ln, font=title_font)
        tw = bbox[2] - bbox[0]
        draw.text(((W - tw) // 2, ty), ln, font=title_font, fill=(255, 255, 255, 255))
        ty += line_h

    # Center tagline
    tagline_y = ty + 20
    if tagline:
        _, tagline_lines = _fit_text(draw, tagline, int(W * 0.80), 48)
        tl_h = draw.textbbox((0, 0), "Ag", font=tagline_font)[3] + 6
        for ln in tagline_lines:
            bbox = draw.textbbox((0, 0), ln, font=tagline_font)
            tw = bbox[2] - bbox[0]
            draw.text(((W - tw) // 2, tagline_y), ln, font=tagline_font, fill=(200, 220, 255, 220))
            tagline_y += tl_h

    # Brand name bottom-right
    draw.text((W - 320, H - 80), brand_name, font=brand_font, fill=(r, g, b, 200))

    img.save(out_path, "PNG")
    return out_path


def make_lower_third(
    caption: str,
    brand_color: str,
    out_path: Path,
) -> Path:
    """Lower-third caption bar — transparent PNG, placed at bottom 18%."""
    img = Image.new("RGBA", (W, LOWER_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    try:
        r, g, b = int(brand_color[1:3], 16), int(brand_color[3:5], 16), int(brand_color[5:7], 16)
    except Exception:
        r, g, b = 26, 86, 219

    # Background bar
    draw.rectangle([(0, 0), (W, LOWER_H)], fill=(r, g, b, 210))

    # Caption text — auto-wrap to fit
    font, lines = _fit_text(draw, caption, int(W * 0.88), 56)
    line_h = draw.textbbox((0, 0), "Ag", font=font)[3] + 6
    total_h = line_h * len(lines)
    cy = (LOWER_H - total_h) // 2
    for ln in lines:
        bbox = draw.textbbox((0, 0), ln, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(((W - tw) // 2, cy), ln, font=font, fill=(255, 255, 255, 255))
        cy += line_h

    img.save(out_path, "PNG")
    return out_path


def make_cta_card(
    cta_text: str,
    brand_color: str,
    out_path: Path,
) -> Path:
    """CTA overlay card — full-frame, shown last 3 seconds."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    overlay = Image.new("RGBA", (W, H), (5, 10, 25, 220))
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    try:
        r, g, b = int(brand_color[1:3], 16), int(brand_color[3:5], 16), int(brand_color[5:7], 16)
    except Exception:
        r, g, b = 26, 86, 219

    # Accent border
    draw.rectangle([(80, 80), (W - 80, H - 80)], outline=(r, g, b, 255), width=4)

    font_large = _font(80)
    font_small = _font(44)

    # CTA text
    bbox = draw.textbbox((0, 0), cta_text, font=font_large)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, H // 2 - 60), cta_text, font=font_large, fill=(255, 255, 255, 255))

    hint = "Get Started Today"
    bbox = draw.textbbox((0, 0), hint, font=font_small)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, H // 2 + 60), hint, font=font_small, fill=(r, g, b, 220))

    img.save(out_path, "PNG")
    return out_path


def composite_overlays(
    base_video: Path,
    out_path: Path,
    title_png: Path | None,
    title_duration: float,
    lower_thirds: Sequence[tuple[Path, float, float]],  # (png, start_s, end_s)
    cta_png: Path | None,
    cta_start: float,
    total_duration: float,
    video_w: int = 1920,
    video_h: int = 1080,
) -> Path:
    """Use ffmpeg overlay filter to composite all text PNGs onto base video.
    Overlays are scaled to the actual video dimensions before compositing."""
    lower_h = int(video_h * 0.18)

    inputs = [FFMPEG, "-y", "-i", str(base_video)]
    # Each entry: (input_idx, is_full_frame, start_s, end_s)
    overlay_inputs: list[tuple[int, bool, float, float]] = []
    input_idx = 1

    if title_png and title_png.exists():
        inputs += ["-i", str(title_png)]
        overlay_inputs.append((input_idx, True, 0.0, title_duration))
        input_idx += 1

    for png, start, end in lower_thirds:
        if png.exists():
            inputs += ["-i", str(png)]
            overlay_inputs.append((input_idx, False, start, end))
            input_idx += 1

    if cta_png and cta_png.exists():
        inputs += ["-i", str(cta_png)]
        overlay_inputs.append((input_idx, True, cta_start, total_duration))
        input_idx += 1

    if not overlay_inputs:
        cmd = [FFMPEG, "-y", "-i", str(base_video), "-c", "copy", str(out_path)]
        subprocess.run(cmd, check=True, capture_output=True)
        return out_path

    # Scale each overlay to video dims, then chain overlays
    scale_parts = []
    overlay_parts = []
    current = "[0:v]"

    for i, (img_idx, is_full, start_s, end_s) in enumerate(overlay_inputs):
        scaled = f"[s{i}]"
        if is_full:
            scale_parts.append(f"[{img_idx}:v]scale={video_w}:{video_h}{scaled}")
            y_pos = 0
        else:
            scale_parts.append(f"[{img_idx}:v]scale={video_w}:{lower_h}{scaled}")
            y_pos = video_h - lower_h

        label_out = f"[v{i}]"
        enable = f"between(t,{start_s:.2f},{end_s:.2f})"
        overlay_parts.append(
            f"{current}{scaled}overlay=0:{y_pos}:enable='{enable}'{label_out}"
        )
        current = label_out

    filter_complex = ";".join(scale_parts + overlay_parts)
    last_label = f"[v{len(overlay_inputs)-1}]"

    cmd = inputs + [
        "-filter_complex", filter_complex,
        "-map", last_label,
        "-map", "0:a?",
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k",
        str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg overlay failed:\n{result.stderr[-1000:]}")
    return out_path
