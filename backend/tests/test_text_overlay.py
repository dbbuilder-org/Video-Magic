"""Integration tests for composite_overlays() — specifically the >4 input case.

The ffmpeg filter_complex chain is built programmatically; this suite verifies
it is well-formed for 1, 4, and 8 overlay inputs (title + N lower-thirds + CTA)
by mocking subprocess.run and inspecting the generated command.
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pipeline.text_overlay import composite_overlays


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fake_png(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    return path


def _run_composite(tmp_path: Path, n_lower_thirds: int) -> tuple[list, str]:
    """Call composite_overlays with n_lower_thirds + title + CTA, return (cmd, filter_complex)."""
    base = tmp_path / "base.mp4"
    base.write_bytes(b"\x00" * 64)

    title = _fake_png(tmp_path / "title.png")
    cta = _fake_png(tmp_path / "cta.png")
    lower_thirds = []
    for i in range(n_lower_thirds):
        p = _fake_png(tmp_path / f"lower_{i:02d}.png")
        lower_thirds.append((p, float(i * 5 + 3), float(i * 5 + 7)))

    out = tmp_path / "overlaid.mp4"

    with patch("pipeline.text_overlay.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        composite_overlays(
            base,
            out,
            title_png=title,
            title_duration=3.0,
            lower_thirds=lower_thirds,
            cta_png=cta,
            cta_start=float(n_lower_thirds * 5 + 3),
            total_duration=float(n_lower_thirds * 5 + 6),
            video_w=1920,
            video_h=1080,
        )
        cmd = mock_run.call_args[0][0]

    # Extract -filter_complex value from the cmd list
    fc_idx = cmd.index("-filter_complex")
    filter_complex = cmd[fc_idx + 1]
    return cmd, filter_complex


# ── Basic structure ───────────────────────────────────────────────────────────

def test_composite_no_overlays_uses_copy(tmp_path):
    """When no overlay PNGs exist, falls back to stream copy."""
    base = tmp_path / "base.mp4"
    base.write_bytes(b"\x00" * 64)
    out = tmp_path / "out.mp4"

    with patch("pipeline.text_overlay.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        composite_overlays(
            base, out,
            title_png=None, title_duration=3.0,
            lower_thirds=[],
            cta_png=None, cta_start=0, total_duration=10.0,
        )
        cmd = mock_run.call_args[0][0]

    assert "-filter_complex" not in cmd
    assert "-c" in cmd and "copy" in cmd


def test_composite_title_only(tmp_path):
    """Single title overlay: 1 scale + 1 overlay in filter_complex."""
    base = tmp_path / "base.mp4"
    base.write_bytes(b"\x00" * 64)
    title = _fake_png(tmp_path / "title.png")
    out = tmp_path / "out.mp4"

    with patch("pipeline.text_overlay.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        composite_overlays(
            base, out,
            title_png=title, title_duration=3.0,
            lower_thirds=[],
            cta_png=None, cta_start=0, total_duration=10.0,
        )
        cmd = mock_run.call_args[0][0]

    fc_idx = cmd.index("-filter_complex")
    fc = cmd[fc_idx + 1]
    assert fc.count("scale=") == 1
    assert fc.count("overlay=") == 1
    assert "[v0]" in fc
    assert cmd.count("-i") == 2  # base + title


# ── Four inputs (30s / 4 scenes) ─────────────────────────────────────────────

def test_composite_four_inputs(tmp_path):
    """30s video: title + 4 lower-thirds + CTA = 6 overlay inputs."""
    cmd, fc = _run_composite(tmp_path, n_lower_thirds=4)

    n_overlays = 6  # title + 4 lower + cta
    assert cmd.count("-i") == n_overlays + 1  # +1 for base video
    assert fc.count("scale=") == n_overlays
    assert fc.count("overlay=") == n_overlays
    # Chain terminates at v5
    assert f"[v{n_overlays - 1}]" in fc
    # All enable= time windows are present
    assert fc.count("enable=") == n_overlays


# ── Eight inputs (60s / 6 scenes) ────────────────────────────────────────────

def test_composite_eight_inputs(tmp_path):
    """60s video: title + 6 lower-thirds + CTA = 8 overlay inputs (critical regression case)."""
    cmd, fc = _run_composite(tmp_path, n_lower_thirds=6)

    n_overlays = 8  # title + 6 lower + cta
    assert cmd.count("-i") == n_overlays + 1  # +1 for base video
    assert fc.count("scale=") == n_overlays
    assert fc.count("overlay=") == n_overlays
    # Final label in chain
    assert f"[v{n_overlays - 1}]" in fc
    # Every overlay has an enable window
    assert fc.count("enable=") == n_overlays
    # Filter is not truncated — all labels present
    for i in range(n_overlays):
        assert f"[s{i}]" in fc
        assert f"[v{i}]" in fc


def test_composite_eight_inputs_map_uses_last_label(tmp_path):
    """The -map flag points to the last chained video label."""
    cmd, fc = _run_composite(tmp_path, n_lower_thirds=6)

    map_idx = cmd.index("-map")
    assert cmd[map_idx + 1] == "[v7]"


def test_composite_eight_inputs_audio_preserved(tmp_path):
    """Audio stream is mapped from the base video."""
    cmd, fc = _run_composite(tmp_path, n_lower_thirds=6)

    # Expect a second -map 0:a? for audio
    map_indices = [i for i, v in enumerate(cmd) if v == "-map"]
    maps = [cmd[i + 1] for i in map_indices]
    assert "0:a?" in maps


# ── Timing correctness ────────────────────────────────────────────────────────

def test_lower_third_y_position(tmp_path):
    """Lower-thirds are placed at video_h - lower_h from top (bottom 18%)."""
    cmd, fc = _run_composite(tmp_path, n_lower_thirds=2)
    lower_h = int(1080 * 0.18)
    expected_y = 1080 - lower_h
    # At least one overlay should reference this y position
    assert f"overlay=0:{expected_y}" in fc


def test_title_overlay_at_y_zero(tmp_path):
    """Full-frame overlays (title, CTA) are placed at y=0."""
    cmd, fc = _run_composite(tmp_path, n_lower_thirds=0)
    # With no lower-thirds, title and CTA both land at y=0
    assert "overlay=0:0" in fc


def test_between_time_windows_present(tmp_path):
    """Each overlay's enable clause uses between(t,start,end)."""
    cmd, fc = _run_composite(tmp_path, n_lower_thirds=2)
    assert "between(t," in fc


# ── Error handling ────────────────────────────────────────────────────────────

def test_composite_raises_on_ffmpeg_error(tmp_path):
    """RuntimeError raised when ffmpeg exits non-zero."""
    base = tmp_path / "base.mp4"
    base.write_bytes(b"\x00" * 64)
    title = _fake_png(tmp_path / "title.png")
    out = tmp_path / "out.mp4"

    with patch("pipeline.text_overlay.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stderr="error: invalid option")
        with pytest.raises(RuntimeError, match="ffmpeg overlay failed"):
            composite_overlays(
                base, out,
                title_png=title, title_duration=3.0,
                lower_thirds=[],
                cta_png=None, cta_start=0, total_duration=10.0,
            )
