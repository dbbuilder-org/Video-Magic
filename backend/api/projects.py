"""Project CRUD routes."""
import json
from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from models import create_project, get_project, get_jobs, patch_project_spec, update_project
from progress import subscribe
from api.generate import run_pipeline

router = APIRouter(prefix="/projects", tags=["projects"])


class RerunRequest(BaseModel):
    spec: dict


@router.get("/{project_id}")
async def get_project_route(project_id: str):
    p = get_project(project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    return p


@router.get("/{project_id}/jobs")
async def list_jobs(project_id: str):
    return get_jobs(project_id)


@router.patch("/{project_id}/spec")
async def update_spec(project_id: str, body: RerunRequest, bg: BackgroundTasks):
    p = get_project(project_id)
    if not p:
        raise HTTPException(404, "Project not found")

    merged_spec = {**p["spec"], **body.spec}
    # Clear doc_spec so pipeline re-runs parser with new spec
    merged_spec.pop("doc_spec", None)
    patch_project_spec(project_id, merged_spec)
    update_project(project_id, status="running", error=None)

    bg.add_task(run_pipeline, project_id, merged_spec)
    return {"project_id": project_id, "status": "rerunning"}


@router.get("/{project_id}/progress")
async def progress_stream(project_id: str):
    """Server-Sent Events stream for pipeline progress."""
    async def event_generator():
        async for chunk in subscribe(project_id):
            yield chunk

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
