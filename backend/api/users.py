"""User profile + referral + credits routes."""
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from models import (
    get_or_create_referral_code,
    get_user_credits,
    get_user_profile,
    list_projects_by_user,
    register_referral,
    upsert_user_profile,
)

router = APIRouter(prefix="/users", tags=["users"])


class ProfileUpdate(BaseModel):
    brand_name: str
    brand_color: str = "#1A56DB"


class ReferralTrack(BaseModel):
    code: str


def _require_owner(user_id: str, x_user_id: str | None) -> None:
    if x_user_id != user_id:
        raise HTTPException(403, "Forbidden")


@router.get("/{user_id}/profile")
async def get_profile(user_id: str, x_user_id: str | None = Header(None)):
    _require_owner(user_id, x_user_id)
    return get_user_profile(user_id)


@router.put("/{user_id}/profile")
async def update_profile(user_id: str, body: ProfileUpdate, x_user_id: str | None = Header(None)):
    _require_owner(user_id, x_user_id)
    return upsert_user_profile(user_id, body.brand_name, body.brand_color)


@router.get("/{user_id}/referral-code")
async def get_referral_code(user_id: str, x_user_id: str | None = Header(None)):
    _require_owner(user_id, x_user_id)
    code = get_or_create_referral_code(user_id)
    app_url = __import__("os").environ.get("APP_URL", "http://localhost:3000")
    return {
        "code": code,
        "referral_url": f"{app_url}/sign-up?ref={code}",
        "credit_per_referral_cents": 500,
        "credit_per_referral_display": "$5.00",
    }


@router.get("/{user_id}/credits")
async def get_credits(user_id: str, x_user_id: str | None = Header(None)):
    _require_owner(user_id, x_user_id)
    balance = get_user_credits(user_id)
    return {"balance_cents": balance, "balance_display": f"${balance/100:.2f}"}


@router.get("/{user_id}/projects")
async def list_user_projects(user_id: str, x_user_id: str | None = Header(None)):
    _require_owner(user_id, x_user_id)
    return list_projects_by_user(user_id)


@router.post("/referral/track")
async def track_referral(body: ReferralTrack, x_user_id: str | None = Header(None)):
    """Call from frontend after Clerk sign-up when ?ref=CODE is in the URL."""
    if not x_user_id:
        raise HTTPException(401, "Unauthorized")
    ok = register_referral(x_user_id, body.code)
    return {"registered": ok}
