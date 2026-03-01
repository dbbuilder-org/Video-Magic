"""Pillow — generate text overlay PNGs; ffmpeg composite at timestamps."""
import subprocess
import shutil
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageDraw, ImageFont


FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
W, H = 1920, 1080
LOWER_H = int(H * 0.18)   # Lower-third bar height
TITLE_H = H                # Full-frame title card


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

    # Title text
    title_font = _font(96)
    tagline_font = _font(48)
    brand_font = _font(36)

    # Center title
    bbox = draw.textbbox((0, 0), title, font=title_font)
    tw = bbox[2] - bbox[0]
    ty = H // 2 - 120
    draw.text(((W - tw) // 2, ty), title, font=title_font, fill=(255, 255, 255, 255))

    # Center tagline
    bbox = draw.textbbox((0, 0), tagline, font=tagline_font)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, ty + 130), tagline, font=tagline_font, fill=(200, 220, 255, 220))

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

    # Caption text
    font = _font(56)
    bbox = draw.textbbox((0, 0), caption, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text(((W - tw) // 2, (LOWER_H - th) // 2), caption, font=font, fill=(255, 255, 255, 255))

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
) -> Path:
    """Use ffmpeg overlay filter to composite all text PNGs onto base video."""
    # Build filter_complex
    inputs = [FFMPEG, "-y", "-i", str(base_video)]
    overlay_inputs = []
    filter_parts = []
    input_idx = 1

    if title_png and title_png.exists():
        inputs += ["-i", str(title_png)]
        overlay_inputs.append((input_idx, 0, title_duration))
        input_idx += 1

    for png, start, end in lower_thirds:
        if png.exists():
            inputs += ["-i", str(png)]
            overlay_inputs.append((input_idx, start, end))
            input_idx += 1

    if cta_png and cta_png.exists():
        inputs += ["-i", str(cta_png)]
        overlay_inputs.append((input_idx, cta_start, total_duration))
        input_idx += 1

    if not overlay_inputs:
        # No overlays — just copy
        cmd = [FFMPEG, "-y", "-i", str(base_video), "-c", "copy", str(out_path)]
        subprocess.run(cmd, check=True, capture_output=True)
        return out_path

    # Build chained overlay filter
    current = "[0:v]"
    for i, (img_idx, start_s, end_s) in enumerate(overlay_inputs):
        label_in = current
        label_out = f"[v{i}]"
        y_pos = 0 if i == 0 and title_png else f"H-{LOWER_H}"
        if img_idx == 1 and title_png:
            # title card: full overlay
            y_pos = 0
        elif cta_png and img_idx == len(overlay_inputs):
            y_pos = 0
        else:
            y_pos = f"H-{LOWER_H}"

        enable = f"between(t,{start_s:.2f},{end_s:.2f})"
        filter_parts.append(
            f"{label_in}[{img_idx}:v]overlay=0:{y_pos}:enable='{enable}'{label_out}"
        )
        current = label_out

    filter_complex = ";".join(filter_parts)
    # Rename last label to [vout]
    filter_complex = filter_complex.rsplit(current, 1)[0] + current.replace(current, "[vout]")
    # Simpler approach: just chain
    filter_complex = ";".join(filter_parts)
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
