"""Stripe Checkout — create session and handle webhook."""
import os

import stripe
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from pydantic import BaseModel

from models import (
    apply_referral_credit,
    create_project,
    deduct_user_credits,
    get_project,
    get_user_credits,
    update_project,
    upsert_user_profile,
)
from api.generate import run_pipeline

router = APIRouter(prefix="/stripe", tags=["stripe"])

PRICE_CENTS = {10: 999, 30: 1999, 60: 2999}
PRICE_MAP   = {10: "STRIPE_PRICE_10S", 30: "STRIPE_PRICE_30S", 60: "STRIPE_PRICE_60S"}
PRICE_LABEL = {10: "$9.99", 30: "$19.99", 60: "$29.99"}


class CheckoutRequest(BaseModel):
    duration: int          # 10, 30, or 60
    brand_name: str
    brand_color: str = "#1A56DB"
    document_text: str


@router.post("/checkout")
async def create_checkout(
    body: CheckoutRequest,
    x_user_id: str | None = Header(None),
):
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
    app_url = os.environ.get("APP_URL", "http://localhost:3000")

    price_env = PRICE_MAP.get(body.duration)
    if not price_env:
        raise HTTPException(400, f"Unsupported duration: {body.duration}")

    price_id = os.environ.get(price_env)
    if not price_id:
        raise HTTPException(500, f"Stripe price not configured: {price_env}")

    spec = {
        "duration": body.duration,
        "brand_name": body.brand_name,
        "brand_color": body.brand_color,
        "document_text": body.document_text,
    }
    project = create_project(spec, user_id=x_user_id)
    project_id = project["id"]

    # ── Save brand to user profile ───────────────────────────────────────────
    if x_user_id:
        upsert_user_profile(x_user_id, body.brand_name, body.brand_color)

    # ── Credit handling ──────────────────────────────────────────────────────
    credit_cents = get_user_credits(x_user_id) if x_user_id else 0
    price_cents = PRICE_CENTS[body.duration]
    discounts = []

    if credit_cents > 0 and x_user_id:
        apply_cents = min(credit_cents, price_cents)
        coupon = stripe.Coupon.create(
            amount_off=apply_cents,
            currency="usd",
            duration="once",
            name=f"${apply_cents/100:.2f} referral credit",
        )
        discounts = [{"coupon": coupon.id}]
        # Deduct only after payment confirmed (in webhook) — store pending deduction
        # We pass applied_credit_cents in metadata
        update_project(project_id, spec={**spec, "pending_credit_cents": apply_cents})

    session_kwargs = dict(
        mode="payment",
        line_items=[{"price": price_id, "quantity": 1}],
        metadata={
            "project_id": project_id,
            "user_id": x_user_id or "",
            "credit_cents": str(credit_cents),
        },
        success_url=f"{app_url}/project/{project_id}?session={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{app_url}/create?cancelled=1",
    )
    if discounts:
        session_kwargs["discounts"] = discounts

    session = stripe.checkout.Session.create(**session_kwargs)
    return {"checkout_url": session.url, "project_id": project_id, "credit_applied_cents": apply_cents if credit_cents > 0 else 0}


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
        meta = session.get("metadata", {})
        project_id = meta.get("project_id")
        user_id = meta.get("user_id") or None

        if project_id:
            p = get_project(project_id)
            if p:
                # Deduct credits that were applied
                pending_credit = p["spec"].get("pending_credit_cents", 0)
                if pending_credit and user_id:
                    try:
                        deduct_user_credits(user_id, pending_credit)
                    except ValueError:
                        pass  # already deducted or insufficient — don't block pipeline

                # Apply referral credit to the referrer (first paid video)
                if user_id:
                    apply_referral_credit(user_id)

                bg.add_task(run_pipeline, project_id, p["spec"])

    return {"received": True}


@router.get("/prices")
async def get_prices():
    return {
        "10s": {"price": 9.99, "label": "10-Second Promo"},
        "30s": {"price": 14.99, "label": "30-Second Overview"},
        "60s": {"price": 19.99, "label": "60-Second Deep Dive"},
    }
