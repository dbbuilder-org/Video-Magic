"""Stripe Checkout — create session and handle webhook."""
import json
import os

import stripe
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from pydantic import BaseModel

from models import create_project, get_project, update_project
from api.generate import run_pipeline

router = APIRouter(prefix="/stripe", tags=["stripe"])

PRICE_MAP = {
    10: "STRIPE_PRICE_10S",
    30: "STRIPE_PRICE_30S",
    60: "STRIPE_PRICE_60S",
}


class CheckoutRequest(BaseModel):
    duration: int          # 10, 30, or 60
    brand_name: str
    brand_color: str = "#1A56DB"
    document_text: str


@router.post("/checkout")
async def create_checkout(body: CheckoutRequest):
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
    app_url = os.environ.get("APP_URL", "http://localhost:3000")

    price_env = PRICE_MAP.get(body.duration)
    if not price_env:
        raise HTTPException(400, f"Unsupported duration: {body.duration}")

    price_id = os.environ.get(price_env)
    if not price_id:
        raise HTTPException(500, f"Stripe price not configured: {price_env}")

    # Create project record (status=pending until payment confirmed)
    spec = {
        "duration": body.duration,
        "brand_name": body.brand_name,
        "brand_color": body.brand_color,
        "document_text": body.document_text,
    }
    project = create_project(spec)
    project_id = project["id"]

    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{"price": price_id, "quantity": 1}],
        metadata={"project_id": project_id},
        success_url=f"{app_url}/project/{project_id}?session={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{app_url}/create?cancelled=1",
    )

    return {"checkout_url": session.url, "project_id": project_id}


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    bg: BackgroundTasks,
    stripe_signature: str = Header(None, alias="stripe-signature"),
):
    payload = await request.body()
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature, webhook_secret)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(400, "Invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        project_id = session.get("metadata", {}).get("project_id")
        if project_id:
            p = get_project(project_id)
            if p:
                bg.add_task(run_pipeline, project_id, p["spec"])

    return {"received": True}


@router.get("/prices")
async def get_prices():
    return {
        "10s": {"price": 9.99, "label": "10-Second Promo"},
        "30s": {"price": 14.99, "label": "30-Second Overview"},
        "60s": {"price": 19.99, "label": "60-Second Deep Dive"},
    }
