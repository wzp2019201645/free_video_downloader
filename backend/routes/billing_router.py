"""Stripe billing routes. Amounts and price ids are never taken from the browser."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException, Request

import billing_config
from models.billing_schemas import ConfirmCheckoutRequest
from services.access import current_user
from services.billing_service import (
    AlreadyMember,
    BillingError,
    BillingNotConfigured,
    InvalidSignature,
    LivemodeMismatch,
    NeedsPortal,
    NoCustomer,
    NotYourSession,
    PriceMisconfigured,
    _safe_stripe_message,
    billing,
    public_user,
)

logger = logging.getLogger("billing")

billing_router = APIRouter(prefix="/api/billing", tags=["billing"])

_NOT_CONFIGURED = "支付功能尚未配置。请在 backend/.env 填入 Stripe 测试密钥后重启后端。"


def _require_login(request: Request) -> dict:
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")
    return user


def _stripe_http_error(exc: Exception) -> HTTPException:
    name = exc.__class__.__name__
    text = _safe_stripe_message(exc)
    if name in {"APIConnectionError", "APIError"}:
        return HTTPException(
            status_code=502,
            detail="连不上 Stripe。如果这台电脑访问不了 checkout.stripe.com，请在 backend/.env 设置 STRIPE_PROXY 后重启后端。",
        )
    lowered = text.lower()
    if "portal" in lowered or "configuration" in lowered:
        return HTTPException(
            status_code=400,
            detail="请先在 Stripe 测试模式打开客户门户：设置 → Billing → Customer portal，打开后保存。",
        )
    return HTTPException(status_code=502, detail=f"Stripe 请求失败：{text}")


@billing_router.get("/plan")
def plan():
    payload = {
        "configured": billing_config.stripe_configured(),
        "currency": billing_config.EXPECTED_CURRENCY,
        "unit_amount": billing_config.EXPECTED_UNIT_AMOUNT,
        "interval": billing_config.EXPECTED_INTERVAL,
        "label": "每月 ¥19",
    }
    if not payload["configured"]:
        return payload
    try:
        billing.ensure_price()
    except BillingNotConfigured:
        payload["configured"] = False
        return payload
    except PriceMisconfigured as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.warning("price lookup failed: %s", exc.__class__.__name__)
        raise _stripe_http_error(exc) from exc
    return payload


@billing_router.post("/checkout")
def checkout(request: Request):
    user = _require_login(request)
    try:
        url = billing.create_checkout(user)
    except AlreadyMember as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except NeedsPortal as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except BillingNotConfigured as exc:
        raise HTTPException(status_code=503, detail=_NOT_CONFIGURED) from exc
    except PriceMisconfigured as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except BillingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.warning("checkout failed: %s", exc.__class__.__name__)
        raise _stripe_http_error(exc) from exc
    return {"url": url}


@billing_router.post("/portal")
def portal(request: Request):
    user = _require_login(request)
    try:
        url = billing.create_portal(user)
    except NoCustomer as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except BillingNotConfigured as exc:
        raise HTTPException(status_code=503, detail=_NOT_CONFIGURED) from exc
    except BillingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.warning("portal failed: %s", exc.__class__.__name__)
        raise _stripe_http_error(exc) from exc
    return {"url": url}


@billing_router.post("/confirm")
def confirm(body: ConfirmCheckoutRequest, request: Request):
    user = _require_login(request)
    try:
        billing.confirm_session(user, body.session_id)
    except NotYourSession as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except BillingNotConfigured as exc:
        raise HTTPException(status_code=503, detail=_NOT_CONFIGURED) from exc
    except BillingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.warning("confirm failed: %s", exc.__class__.__name__)
        raise _stripe_http_error(exc) from exc
    return {"user": public_user(user)}


@billing_router.post("/webhook")
async def webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    try:
        event = await asyncio.to_thread(billing.gateway.construct_event, payload, signature)
        result = await asyncio.to_thread(billing.handle_event, event)
    except BillingNotConfigured as exc:
        raise HTTPException(status_code=503, detail=_NOT_CONFIGURED) from exc
    except InvalidSignature as exc:
        raise HTTPException(status_code=400, detail="Webhook 签名无效") from exc
    except LivemodeMismatch as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.warning("webhook failed: %s", exc.__class__.__name__)
        raise HTTPException(status_code=500, detail="处理支付通知失败") from exc
    return {"received": True, "duplicate": result == "duplicate"}
