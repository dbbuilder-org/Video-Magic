"""SSE progress bus — asyncio.Queue per project_id."""
import asyncio
import json
from collections import defaultdict
from typing import AsyncGenerator

# project_id -> list of subscriber queues
_queues: dict[str, list[asyncio.Queue]] = defaultdict(list)


def emit(project_id: str, stage: str, pct: int, detail: str = "") -> None:
    """Publish a progress event. Called from background thread via asyncio.run_coroutine_threadsafe."""
    payload = json.dumps({"stage": stage, "pct": pct, "detail": detail})
    loop = asyncio.get_event_loop()
    for q in list(_queues.get(project_id, [])):
        loop.call_soon_threadsafe(q.put_nowait, payload)


async def emit_async(project_id: str, stage: str, pct: int, detail: str = "") -> None:
    """Async variant — call from async context."""
    payload = json.dumps({"stage": stage, "pct": pct, "detail": detail})
    for q in list(_queues.get(project_id, [])):
        await q.put(payload)


async def subscribe(project_id: str) -> AsyncGenerator[str, None]:
    """Yield SSE data strings for the given project."""
    q: asyncio.Queue = asyncio.Queue(maxsize=256)
    _queues[project_id].append(q)
    try:
        while True:
            payload = await asyncio.wait_for(q.get(), timeout=30)
            yield f"data: {payload}\n\n"
            parsed = json.loads(payload)
            if parsed.get("pct") == 100 or parsed.get("stage") == "error":
                break
    except asyncio.TimeoutError:
        # Keep-alive ping
        yield ": ping\n\n"
    finally:
        _queues[project_id].remove(q)
