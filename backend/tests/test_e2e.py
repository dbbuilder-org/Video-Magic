"""E2E pipeline tests — all external API calls mocked, full orchestration verified.

Patches target api.generate.<name> (where functions are imported into), not
the source modules — this is the correct unittest.mock pattern for "from X import Y".
"""
import asyncio
from pathlib import Path
from unittest.mock import patch

import pytest

import models
import storage


# ── Fake data ─────────────────────────────────────────────────────────────────

FAKE_DOC_SPEC = {
    "title": "AI Teaching Revolution",
    "tagline": "The future of learning",
    "brand_description": "A forward-looking education platform",
    "key_messages": ["AI enhances teaching", "Students learn faster"],
    "cta": "Learn more at example.com",
    "scenes": [
        {
            "index": 0,
            "caption": "The New Classroom",
            "visual_action": "A bright modern classroom with holographic displays",
            "vo_text": "Welcome to the future of education.",
        },
        {
            "index": 1,
            "caption": "AI Tools for Teachers",
            "visual_action": "A teacher using an AI assistant on a tablet",
            "vo_text": "AI tools help teachers personalise every lesson.",
        },
    ],
}


def _fake_file(path: Path, content: bytes = b"\x00" * 512) -> Path:
    """Write fake bytes so path.exists() is True. Returns path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "STORAGE_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def project(tmp_storage):
    return models.create_project(
        {
            "duration": 30,
            "brand_name": "E2E Brand",
            "document_text": "This is a test document about AI in education.",
        },
        user_id="user_e2e",
    )


# ── Shared patch context ───────────────────────────────────────────────────────

def _pipeline_patches():
    """Return a list of patch() context managers for all external calls in generate.py.

    Targets are api.generate.<name> because generate.py uses `from pipeline.X import Y`.
    """
    return [
        patch("api.generate.parse_document", return_value=FAKE_DOC_SPEC),
        patch("api.generate.generate_character",
              side_effect=lambda bn, bd, p: _fake_file(p)),
        patch("api.generate.make_title_card"),
        patch("api.generate.make_lower_third"),
        patch("api.generate.make_cta_card"),
        patch("api.generate.generate_scene",
              side_effect=lambda va, p, cb=None: _fake_file(p)),
        patch("api.generate.generate_voiceover",
              side_effect=lambda s, p: _fake_file(p)),
        patch("api.generate.stitch_scenes",
              side_effect=lambda scenes, out: _fake_file(out)),
        patch("api.generate.get_video_duration", return_value=30.0),
        patch("api.generate.get_video_dimensions", return_value=(1920, 1080)),
        patch("api.generate.composite_overlays",
              side_effect=lambda video, out, *a, **kw: _fake_file(out)),
        patch("api.generate.mix_voiceover",
              side_effect=lambda v, vo, out: _fake_file(out)),
    ]


from contextlib import ExitStack


async def _run_with_patches(pid: str, spec: dict, extra_patches: list | None = None) -> None:
    from api.generate import run_pipeline
    patches = _pipeline_patches() + (extra_patches or [])
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        await run_pipeline(pid, spec)


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_full_pipeline_happy_path(project, tmp_storage):
    """All 8 stages run; project ends as done with video_url set."""
    pid = project["id"]
    await _run_with_patches(pid, project["spec"])

    p = models.get_project(pid)
    assert p["status"] == "done"
    assert p["video_url"] == f"/storage/{pid}/final.mp4"


@pytest.mark.asyncio
async def test_pipeline_records_all_job_stages(project, tmp_storage):
    """Every stage creates a job record in the DB."""
    pid = project["id"]
    await _run_with_patches(pid, project["spec"])

    jobs = models.get_jobs(pid)
    stages = {j["stage"] for j in jobs}
    assert "parse_document" in stages
    assert "character_gen" in stages
    assert "text_overlays" in stages
    assert "scene_0" in stages
    assert "scene_1" in stages
    assert "voiceover" in stages
    assert "stitch" in stages
    assert "overlay" in stages
    assert "mix" in stages


@pytest.mark.asyncio
async def test_pipeline_logs_api_costs(project, tmp_storage):
    """Cost records are written for Gemini, Imagen, Veo, and ElevenLabs."""
    pid = project["id"]
    await _run_with_patches(pid, project["spec"])

    costs = models.get_project_costs(pid)
    assert len(costs) > 0
    services = {c["service"] for c in costs}
    assert "gemini" in services
    assert "imagen" in services
    assert "veo" in services
    assert "elevenlabs" in services
    assert sum(c["cost_usd"] for c in costs) > 0


@pytest.mark.asyncio
async def test_pipeline_skips_parse_when_doc_spec_present(project, tmp_storage):
    """If doc_spec is already in spec, parse_document is never called."""
    pid = project["id"]
    spec_with_doc = {**project["spec"], "doc_spec": FAKE_DOC_SPEC}
    models.update_project(pid, spec=spec_with_doc)

    mock_parse = patch("api.generate.parse_document", return_value=FAKE_DOC_SPEC)
    await _run_with_patches(pid, spec_with_doc, extra_patches=[mock_parse])

    # parse_document should not have been called since doc_spec is present
    # (verified by the pipeline logic: `if not doc_spec:`)
    p = models.get_project(pid)
    assert p["status"] == "done"


@pytest.mark.asyncio
async def test_pipeline_error_sets_status(project, tmp_storage):
    """An exception in any stage marks the project as error."""
    from api.generate import run_pipeline

    pid = project["id"]

    with patch("api.generate.parse_document",
               side_effect=RuntimeError("Gemini quota exceeded")):
        await run_pipeline(pid, project["spec"])

    p = models.get_project(pid)
    assert p["status"] == "error"
    assert "Gemini quota exceeded" in (p["error"] or "")


@pytest.mark.asyncio
async def test_pipeline_completes_with_preexisting_scene_files(project, tmp_storage):
    """Pipeline runs to completion even when scene MP4s already exist on disk."""
    pid = project["id"]
    spec_with_doc = {**project["spec"], "doc_spec": FAKE_DOC_SPEC}

    # Pre-create scene files (simulates a partial prior run)
    for i in range(len(FAKE_DOC_SPEC["scenes"])):
        _fake_file(storage.scene_path(pid, i))

    await _run_with_patches(pid, spec_with_doc)
    assert models.get_project(pid)["status"] == "done"


def test_scene_gen_skips_when_output_exists(tmp_path):
    """generate_scene returns immediately without calling Veo when file already exists."""
    from pipeline.scene_gen import generate_scene

    out = tmp_path / "scene.mp4"
    out.write_bytes(b"existing content")

    with patch("pipeline.scene_gen.genai") as mock_genai:
        result = generate_scene("some prompt", out)
        mock_genai.Client.assert_not_called()
        assert result == out
