"""Project CRUD routes."""
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from models import get_project, get_jobs, list_projects_by_user, patch_project_spec, update_project
from progress import subscribe
from api.generate import run_pipeline

router = APIRouter(prefix="/projects", tags=["projects"])


def _check_ownership(p: dict, x_user_id: str | None) -> None:
    """Project is accessible if it has no owner or the caller owns it."""
    owner = p.get("user_id")
    if owner and owner != x_user_id:
        raise HTTPException(403, "Forbidden")


class RerunRequest(BaseModel):
    spec: dict


@router.get("")
async def list_projects(user_id: str | None = None, x_user_id: str | None = Header(None)):
    uid = user_id or x_user_id
    if not uid:
        raise HTTPException(401, "Unauthorized")
    return list_projects_by_user(uid)


@router.get("/{project_id}")
async def get_project_route(project_id: str, x_user_id: str | None = Header(None)):
    p = get_project(project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    _check_ownership(p, x_user_id)
    return p


@router.get("/{project_id}/jobs")
async def list_jobs(project_id: str, x_user_id: str | None = Header(None)):
    p = get_project(project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    _check_ownership(p, x_user_id)
    return get_jobs(project_id)


@router.patch("/{project_id}/spec")
async def update_spec(
    project_id: str,
    body: RerunRequest,
    bg: BackgroundTasks,
    x_user_id: str | None = Header(None),
):
    p = get_project(project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    _check_ownership(p, x_user_id)

    merged_spec = {**p["spec"], **body.spec}
    merged_spec.pop("doc_spec", None)
    patch_project_spec(project_id, merged_spec)
    update_project(project_id, status="running", error=None)

    bg.add_task(run_pipeline, project_id, merged_spec)
    return {"project_id": project_id, "status": "rerunning"}


@router.get("/{project_id}/progress")
async def progress_stream(project_id: str):
    """Server-Sent Events stream for pipeline progress. Public — auth checked upstream."""
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
