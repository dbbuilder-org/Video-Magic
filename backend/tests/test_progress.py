"""Tests for the SSE progress bus — TTL cleanup and keep-alive behaviour.

The subscribe() generator registers its queue lazily on first __anext__ call,
so all tests that emit + receive must run the consumer and emitter concurrently
via asyncio.create_task.
"""
import asyncio
import json

import pytest

import progress


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _consume_until_done(project_id: str) -> list[str]:
    """Subscribe and collect all SSE chunks until pct=100 or stage=error."""
    chunks = []
    async for chunk in progress.subscribe(project_id):
        chunks.append(chunk)
    return chunks


# ── Emit / subscribe round-trip ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_emit_async_delivers_to_subscriber():
    pid = "test-emit-1"

    # Start consumer as a background task so its queue is registered
    task = asyncio.create_task(_consume_until_done(pid))
    await asyncio.sleep(0)  # let the generator advance to the first await

    await progress.emit_async(pid, "parse_document", 5, "starting")
    await progress.emit_async(pid, "done", 100)

    chunks = await task
    assert len(chunks) == 2
    data = json.loads(chunks[0].replace("data: ", "").strip())
    assert data["stage"] == "parse_document"
    assert data["pct"] == 5


@pytest.mark.asyncio
async def test_subscribe_exits_on_pct_100():
    pid = "test-exit-100"

    task = asyncio.create_task(_consume_until_done(pid))
    await asyncio.sleep(0)

    await progress.emit_async(pid, "done", 100)
    chunks = await task

    assert any("100" in c for c in chunks)
    assert pid not in progress._queues  # TTL cleaned up


@pytest.mark.asyncio
async def test_subscribe_exits_on_error_stage():
    pid = "test-exit-error"

    task = asyncio.create_task(_consume_until_done(pid))
    await asyncio.sleep(0)

    await progress.emit_async(pid, "error", 0, "something broke")
    chunks = await task

    assert len(chunks) == 1
    data = json.loads(chunks[0].replace("data: ", "").strip())
    assert data["stage"] == "error"
    assert pid not in progress._queues


@pytest.mark.asyncio
async def test_multiple_events_in_order():
    pid = "test-order"

    task = asyncio.create_task(_consume_until_done(pid))
    await asyncio.sleep(0)

    for stage, pct in [("parse_document", 5), ("character_gen", 20), ("voiceover", 82)]:
        await progress.emit_async(pid, stage, pct)
    await progress.emit_async(pid, "done", 100)

    chunks = await task
    assert len(chunks) == 4
    stages = [json.loads(c.replace("data: ", "").strip())["stage"] for c in chunks]
    assert stages == ["parse_document", "character_gen", "voiceover", "done"]


# ── TTL cleanup ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ttl_cleanup_removes_key_after_done():
    pid = "test-ttl-1"

    task = asyncio.create_task(_consume_until_done(pid))
    await asyncio.sleep(0)
    assert pid in progress._queues

    await progress.emit_async(pid, "done", 100)
    await task

    assert pid not in progress._queues


@pytest.mark.asyncio
async def test_ttl_cleanup_with_multiple_subscribers():
    pid = "test-ttl-multi"

    task1 = asyncio.create_task(_consume_until_done(pid))
    task2 = asyncio.create_task(_consume_until_done(pid))
    await asyncio.sleep(0)
    assert len(progress._queues[pid]) == 2

    await progress.emit_async(pid, "done", 100)
    await asyncio.gather(task1, task2)

    assert pid not in progress._queues


# ── emit() (sync variant) ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_emit_sync_delivers():
    pid = "test-sync-emit"

    task = asyncio.create_task(_consume_until_done(pid))
    await asyncio.sleep(0)

    progress.emit(pid, "stitch", 88)
    await asyncio.sleep(0)  # let call_soon_threadsafe deliver

    await progress.emit_async(pid, "done", 100)
    chunks = await task

    assert len(chunks) == 2
    data = json.loads(chunks[0].replace("data: ", "").strip())
    assert data["stage"] == "stitch"


# ── Cost-estimation helpers (unit tests, not asyncio) ─────────────────────────

def test_gemini_flash_cost_positive():
    from pipeline.costs import est_gemini_flash
    _, _, cost = est_gemini_flash("Hello world " * 100, '{"key": "value"}')
    assert cost > 0


def test_imagen4_cost():
    from pipeline.costs import est_imagen4
    assert abs(est_imagen4(1) - 0.04) < 0.001
    assert abs(est_imagen4(3) - 0.12) < 0.001


def test_veo31_cost():
    from pipeline.costs import est_veo31
    assert abs(est_veo31(8.0) - 2.80) < 0.001


def test_elevenlabs_cost():
    from pipeline.costs import est_elevenlabs
    script = "A" * 1000
    assert abs(est_elevenlabs(script) - 0.30) < 0.001
