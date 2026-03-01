"""Pipeline orchestrator — BackgroundTask that runs all stages in order."""
import asyncio
import traceback
from pathlib import Path

from models import update_project, upsert_job
from progress import emit_async
from storage import (
    character_path,
    final_path,
    overlays_dir,
    project_dir,
    scene_path,
    scenes_dir,
    voiceover_path,
)
from pipeline.assembler import get_video_duration, mix_voiceover, stitch_scenes
from pipeline.character_gen import generate_character
from pipeline.document_parser import parse_document
from pipeline.scene_gen import generate_scene
from pipeline.text_overlay import (
    composite_overlays,
    make_cta_card,
    make_lower_third,
    make_title_card,
)
from pipeline.voiceover import generate_voiceover


async def _emit(project_id: str, stage: str, pct: int, detail: str = "") -> None:
    upsert_job(project_id, stage, pct, "running", detail)
    await emit_async(project_id, stage, pct, detail)


async def _emit_done(project_id: str, stage: str, pct: int) -> None:
    upsert_job(project_id, stage, pct, "done")
    await emit_async(project_id, stage, pct)


async def run_pipeline(project_id: str, spec: dict) -> None:
    """Execute the full video generation pipeline."""
    try:
        await _run_pipeline_inner(project_id, spec)
    except Exception as exc:
        tb = traceback.format_exc()
        update_project(project_id, status="error", error=str(exc))
        upsert_job(project_id, "error", 0, "error", tb[:2000])
        await emit_async(project_id, "error", 0, str(exc))


async def _run_pipeline_inner(project_id: str, spec: dict) -> None:
    update_project(project_id, status="running")
    loop = asyncio.get_event_loop()

    duration: int = spec.get("duration", 30)
    brand_name: str = spec.get("brand_name", "Video Magic")
    brand_color: str = spec.get("brand_color", "#1A56DB")
    document_text: str = spec.get("document_text", "")
    doc_spec: dict = spec.get("doc_spec", {})

    # ── Stage 1: Parse document (5%) ────────────────────────────────────────
    await _emit(project_id, "parse_document", 5, "Extracting key messages...")

    if not doc_spec:
        doc_spec = await loop.run_in_executor(
            None, parse_document, document_text, duration, brand_name, brand_color
        )
        update_project(project_id, spec={**spec, "doc_spec": doc_spec})

    await _emit_done(project_id, "parse_document", 12)

    scenes = doc_spec.get("scenes", [])
    title = doc_spec.get("title", brand_name)
    tagline = doc_spec.get("tagline", "")
    cta = doc_spec.get("cta", "")
    brand_description = doc_spec.get("brand_description", "")

    # ── Stage 2: Character image (20%) ──────────────────────────────────────
    await _emit(project_id, "character_gen", 20, "Generating brand character...")

    char_path = character_path(project_id)
    await loop.run_in_executor(
        None, generate_character, brand_name, brand_description, char_path
    )
    await _emit_done(project_id, "character_gen", 27)

    # ── Stage 3: Text overlay PNGs (32%) ────────────────────────────────────
    await _emit(project_id, "text_overlays", 32, "Creating text overlay assets...")

    ov_dir = overlays_dir(project_id)
    title_png = ov_dir / "title_card.png"
    await loop.run_in_executor(
        None, make_title_card, title, tagline, brand_color, brand_name, title_png
    )

    lower_third_pngs = []
    for scene in scenes:
        caption = scene.get("caption", "")
        png = ov_dir / f"lower_{scene['index']:02d}.png"
        await loop.run_in_executor(None, make_lower_third, caption, brand_color, png)
        lower_third_pngs.append(png)

    cta_png = ov_dir / "cta_card.png"
    if cta:
        await loop.run_in_executor(None, make_cta_card, cta, brand_color, cta_png)
    await _emit_done(project_id, "text_overlays", 32)

    # ── Stage 4: Scene videos (35–75%) ──────────────────────────────────────
    scene_paths = []
    scene_count = len(scenes)
    pct_start, pct_end = 35, 75
    pct_per_scene = (pct_end - pct_start) / max(scene_count, 1)

    for i, scene in enumerate(scenes):
        scene_pct_start = int(pct_start + i * pct_per_scene)
        scene_pct_end = int(pct_start + (i + 1) * pct_per_scene)
        stage_key = f"scene_{i}"
        await _emit(project_id, stage_key, scene_pct_start, f"Generating scene {i+1}/{scene_count}...")

        sp = scene_path(project_id, i)

        def _poll_cb(elapsed: int, _key=stage_key, _start=scene_pct_start, _end=scene_pct_end) -> None:
            frac = min(elapsed / 300, 0.95)
            pct = int(_start + frac * (_end - _start))
            upsert_job(project_id, _key, pct, "running", f"{elapsed}s elapsed")

        await loop.run_in_executor(
            None, generate_scene, scene["visual_action"], sp, _poll_cb
        )
        scene_paths.append(sp)
        await _emit_done(project_id, stage_key, scene_pct_end)

    # ── Stage 5: Voiceover (82%) ─────────────────────────────────────────────
    await _emit(project_id, "voiceover", 82, "Generating voiceover narration...")

    vo_script = "\n\n".join(s.get("vo_text", "") for s in scenes if s.get("vo_text"))
    vo_path = voiceover_path(project_id)
    await loop.run_in_executor(None, generate_voiceover, vo_script, vo_path)
    await _emit_done(project_id, "voiceover", 82)

    # ── Stage 6: Stitch scenes (88%) ─────────────────────────────────────────
    await _emit(project_id, "stitch", 88, "Stitching scenes together...")

    stitched = project_dir(project_id) / "stitched.mp4"
    await loop.run_in_executor(None, stitch_scenes, scene_paths, stitched)
    await _emit_done(project_id, "stitch", 88)

    # ── Stage 7: Overlay text (93%) ──────────────────────────────────────────
    await _emit(project_id, "overlay", 93, "Compositing text overlays...")

    total_dur = await loop.run_in_executor(None, get_video_duration, stitched)
    scene_dur = total_dur / max(scene_count, 1)

    lower_thirds_timed = [
        (lower_third_pngs[i], i * scene_dur + 0.5, (i + 1) * scene_dur - 0.5)
        for i in range(min(len(lower_third_pngs), scene_count))
    ]

    overlaid = project_dir(project_id) / "overlaid.mp4"
    await loop.run_in_executor(
        None,
        composite_overlays,
        stitched,
        overlaid,
        title_png if title_png.exists() else None,
        min(3.0, scene_dur),
        lower_thirds_timed,
        cta_png if cta and cta_png.exists() else None,
        max(total_dur - 3.0, total_dur * 0.85),
        total_dur,
    )
    await _emit_done(project_id, "overlay", 93)

    # ── Stage 8: Mix voiceover (100%) ────────────────────────────────────────
    await _emit(project_id, "mix", 100, "Mixing voiceover into final video...")

    fp = final_path(project_id)
    if vo_path.exists():
        await loop.run_in_executor(None, mix_voiceover, overlaid, vo_path, fp)
    else:
        import shutil as _shutil
        _shutil.copy2(overlaid, fp)

    video_url = f"/storage/{project_id}/final.mp4"
    update_project(project_id, status="done", video_url=video_url)
    await emit_async(project_id, "done", 100, video_url)
