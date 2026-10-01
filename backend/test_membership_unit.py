"""Membership, gating, and Stripe webhook tests. No network and no real charges."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import tempfile
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))

_TMP = Path(tempfile.mkdtemp(prefix="fvd-member-"))
os.environ["MEMBERSHIP_DATA_DIR"] = str(_TMP)
os.environ["MEMBERSHIP_DB_PATH"] = str(_TMP / "membership.db")
os.environ["SESSION_SECRET"] = "unit-test-session-secret"
os.environ["STRIPE_SECRET_KEY"] = "sk_test_unit_dummy"
os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_unit_test_secret"
os.environ["STRIPE_PRICE_ID"] = "price_unit_pro"
os.environ["PUBLIC_APP_URL"] = "http://localhost:3000"

import billing_config
from fastapi.testclient import TestClient
from main import app, task_manager
from routes import summary_router
from services.billing_service import (
    AlreadyMember,
    BillingService,
    PriceMisconfigured,
)
from services.entitlements import format_requires_membership, is_entitled
from services.membership_db import MembershipDB, get_db
from services.passwords import hash_password, verify_password
from services.session_token import sign_session, verify_session

PRICE = "price_unit_pro"
PERIOD_END = int(time.time()) + 30 * 86400


class FakeGateway:
    def __init__(self):
        self.created = 0
        self.customers = 0
        self._price_ok = False
        self.by_key = {}
        self.sessions = {}
        self.price = {
            "id": PRICE,
            "currency": "cny",
            "unit_amount": 1900,
            "recurring": {"interval": "month", "interval_count": 1},
        }
        self.subscription = {
            "id": "sub_fake",
            "status": "active",
            "customer": "cus_fake",
            "cancel_at_period_end": False,
            "current_period_end": PERIOD_END,
            "metadata": {},
            "items": {
                "data": [
                    {"price": {"id": PRICE}, "current_period_end": PERIOD_END},
                ]
            },
        }

    def configured(self):
        return True

    def retrieve_price(self, price_id):
        return dict(self.price)

    def create_customer(self, email, user_id):
        self.customers += 1
        return {"id": "cus_fake", "email": email, "metadata": {"user_id": user_id}}

    def list_subscriptions(self, customer_id):
        return []

    def retrieve_subscription(self, subscription_id):
        sub = dict(self.subscription)
        sub["id"] = subscription_id
        return sub

    def retrieve_session(self, session_id):
        return self.sessions[session_id]

    def create_checkout_session(self, *, customer_id, user_id, idempotency_key):
        self.created += 1
        cached = self.by_key.get(idempotency_key)
        if cached:
            return cached
        session = {
            "id": f"cs_test_{self.created}",
            "url": f"https://checkout.stripe.com/c/pay/cs_test_{self.created}",
            "status": "open",
        }
        self.by_key[idempotency_key] = session
        self.sessions[session["id"]] = session
        return session


def _subscription(user_id, status, price_id, event_id):
    return {
        "id": event_id,
        "object": "event",
        "type": "customer.subscription.updated",
        "livemode": False,
        "data": {
            "object": {
                "id": "sub_unit_1",
                "object": "subscription",
                "status": status,
                "customer": "cus_unit_1",
                "cancel_at_period_end": False,
                "current_period_end": PERIOD_END,
                "metadata": {"user_id": user_id},
                "items": {
                    "data": [
                        {
                            "price": {"id": price_id},
                            "current_period_end": PERIOD_END,
                        }
                    ]
                },
            }
        },
    }


def _sign(payload: bytes) -> str:
    timestamp = int(time.time())
    signed = f"{timestamp}.".encode() + payload
    digest = hmac.new(
        billing_config.STRIPE_WEBHOOK_SECRET.encode("utf-8"),
        signed,
        hashlib.sha256,
    ).hexdigest()
    return f"t={timestamp},v1={digest}"


def test_format_gate():
    assert format_requires_membership("bestaudio/best") is False
    assert format_requires_membership("bestvideo[height<=720]+bestaudio/best") is False
    assert format_requires_membership("bestvideo[height<=480]+bestaudio/best") is False
    assert format_requires_membership("bestvideo[height<=1080]+bestaudio/best") is True
    assert format_requires_membership("bestvideo+bestaudio/best") is True
    assert format_requires_membership("bestvideo[height<=720]+bestaudio/best,extra") is True
    assert format_requires_membership("137") is True
    print("[OK] format gate")


def test_password_and_session():
    stored = hash_password("correct-horse")
    assert verify_password("correct-horse", stored)
    assert not verify_password("wrong-password", stored)
    token = sign_session("user123", now=1_700_000_000)
    assert verify_session(token, now=1_700_000_000) == "user123"
    assert verify_session(token, now=1_700_000_000 + 15 * 86400) is None
    assert verify_session(token[:-1] + ("a" if token[-1] != "a" else "b"), now=1_700_000_000) is None
    print("[OK] password and session")


def test_checkout_is_idempotent_and_blocks_second_payment():
    db = MembershipDB(_TMP / "checkout.db")
    user = db.create_user("buyer@example.com", hash_password("password12"))
    gateway = FakeGateway()
    gateway.subscription["metadata"] = {"user_id": user["id"]}
    service = BillingService(db, gateway)

    first = service.create_checkout(user)
    second = service.create_checkout(user)
    assert first == second
    assert gateway.created == 1
    assert gateway.customers == 1

    db.upsert_membership(
        user["id"],
        customer_id="cus_fake",
        subscription_id="sub_fake",
        status="active",
        price_id=PRICE,
        period_end=PERIOD_END,
        cancel_at_period_end=False,
    )
    try:
        service.create_checkout(user)
        raise AssertionError("second purchase should be blocked")
    except AlreadyMember:
        pass
    assert gateway.created == 1
    print("[OK] checkout idempotency")


def test_webhook_grants_once_and_ignores_replay():
    db = MembershipDB(_TMP / "events.db")
    user = db.create_user("member@example.com", hash_password("password12"))
    gateway = FakeGateway()
    service = BillingService(db, gateway)

    active = _subscription(user["id"], "active", PRICE, "evt_same")
    assert service.handle_event(active) == "ok"
    assert is_entitled(db.get_membership(user["id"]))

    replay = _subscription(user["id"], "canceled", PRICE, "evt_same")
    assert service.handle_event(replay) == "duplicate"
    assert is_entitled(db.get_membership(user["id"]))

    canceled = _subscription(user["id"], "canceled", PRICE, "evt_cancel")
    assert service.handle_event(canceled) == "ok"
    assert not is_entitled(db.get_membership(user["id"]))

    wrong = _subscription(user["id"], "active", "price_other", "evt_wrong_price")
    assert service.handle_event(wrong) == "ok"
    assert not is_entitled(db.get_membership(user["id"]))
    print("[OK] webhook grant once")


def test_failed_event_can_retry():
    db = MembershipDB(_TMP / "retry.db")

    def boom(_conn):
        raise RuntimeError("disk")

    try:
        db.process_once("evt_boom", "customer.subscription.updated", boom)
        raise AssertionError("expected failure")
    except RuntimeError:
        pass
    assert db.process_once("evt_boom", "customer.subscription.updated", None) is True
    assert db.process_once("evt_boom", "customer.subscription.updated", None) is False
    print("[OK] webhook retry after failure")


def test_paid_checkout_grants_and_wrong_price_does_not():
    db = MembershipDB(_TMP / "paid.db")
    user = db.create_user("paid@example.com", hash_password("password12"))
    gateway = FakeGateway()
    gateway.subscription["metadata"] = {"user_id": user["id"]}
    service = BillingService(db, gateway)
    event = {
        "id": "evt_paid",
        "type": "checkout.session.completed",
        "livemode": False,
        "data": {
            "object": {
                "id": "cs_test_paid",
                "mode": "subscription",
                "payment_status": "paid",
                "client_reference_id": user["id"],
                "metadata": {"user_id": user["id"]},
                "customer": "cus_fake",
                "subscription": "sub_paid",
                "line_items": {"data": [{"price": {"id": PRICE}}]},
            }
        },
    }
    assert service.handle_event(event) == "ok"
    assert is_entitled(db.get_membership(user["id"]))
    assert service.handle_event(event) == "duplicate"
    assert db.get_membership(user["id"])["stripe_subscription_id"] == "sub_paid"

    other = db.create_user("other@example.com", hash_password("password12"))
    gateway.subscription["metadata"] = {"user_id": other["id"]}
    mismatch = {
        "id": "evt_mismatch",
        "type": "checkout.session.completed",
        "livemode": False,
        "data": {
            "object": {
                "id": "cs_test_mismatch",
                "mode": "subscription",
                "payment_status": "paid",
                "client_reference_id": other["id"],
                "metadata": {"user_id": other["id"]},
                "customer": "cus_other",
                "subscription": "sub_other",
                "line_items": {"data": [{"price": {"id": "price_other"}}]},
            }
        },
    }
    assert service.handle_event(mismatch) == "ok"
    assert not is_entitled(db.get_membership(other["id"]))
    print("[OK] paid checkout fulfillment")


def test_price_must_be_monthly_cny():
    db = MembershipDB(_TMP / "price.db")
    user = db.create_user("price@example.com", hash_password("password12"))
    gateway = FakeGateway()
    gateway.price = {
        "currency": "usd",
        "unit_amount": 999,
        "recurring": {"interval": "month", "interval_count": 1},
    }
    service = BillingService(db, gateway)
    try:
        service.create_checkout(user)
        raise AssertionError("usd price should be rejected")
    except PriceMisconfigured:
        pass
    assert gateway.created == 0
    print("[OK] price currency check")


def test_http_auth_and_feature_gates():
    async def fake_download(_url, _format_id):
        return "task-ok"

    class FakeSummary:
        def __init__(self):
            self.calls = 0

        async def create_task(self, _url):
            self.calls += 1
            return "sum-ok"

    task_manager.create_task = fake_download
    summary = FakeSummary()
    summary_router._manager = summary
    client = TestClient(app)

    free = {
        "url": "https://example.com/video",
        "format_id": "bestvideo[height<=720]+bestaudio/best",
    }
    hd = {
        "url": "https://example.com/video",
        "format_id": "bestvideo[height<=1080]+bestaudio/best",
    }
    best = {
        "url": "https://example.com/video",
        "format_id": "bestvideo+bestaudio/best",
    }
    audio = {
        "url": "https://example.com/video",
        "format_id": "bestaudio/best",
    }
    bypass = {
        "url": "https://example.com/video",
        "format_id": "bestvideo[height<=720]+bestaudio/best,bestvideo",
    }

    assert client.post("/api/download", json=free).status_code == 200
    assert client.post("/api/download", json=audio).status_code == 200
    assert client.post("/api/download", json=hd).status_code == 401
    assert client.post("/api/download", json=best).status_code == 401
    assert client.post("/api/download", json=bypass).status_code == 401
    assert client.post("/api/summary", json={"url": "https://example.com/video"}).status_code == 401

    created = client.post(
        "/api/auth/register",
        json={"email": "User@Example.com", "password": "password12"},
    )
    assert created.status_code == 200
    body = created.text
    assert "password_hash" not in body
    assert "scrypt" not in body
    assert created.json()["user"]["email"] == "user@example.com"
    assert created.json()["user"]["is_member"] is False

    assert client.post("/api/download", json=hd).status_code == 403
    assert client.post("/api/summary", json={"url": "https://example.com/video"}).status_code == 403
    assert client.post("/api/summary/mindmap", json={"task_id": "x"}).status_code == 403
    assert summary.calls == 0

    duplicate = client.post(
        "/api/auth/register",
        json={"email": "user@example.com", "password": "password12"},
    )
    assert duplicate.status_code == 409

    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").json()["user"] is None
    bad_login = client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "nope-nope"},
    )
    assert bad_login.status_code == 401
    good_login = client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "password12"},
    )
    assert good_login.status_code == 200

    user = get_db().get_user_by_email("user@example.com")
    get_db().upsert_membership(
        user["id"],
        customer_id="cus_http",
        subscription_id="sub_http",
        status="active",
        price_id=PRICE,
        period_end=PERIOD_END,
        cancel_at_period_end=False,
    )
    assert client.post("/api/download", json=hd).status_code == 200
    assert client.post("/api/summary", json={"url": "https://example.com/video"}).status_code == 200
    assert summary.calls == 1
    me = client.get("/api/auth/me").json()["user"]
    assert me["is_member"] is True

    blocked = client.post("/api/billing/checkout")
    assert blocked.status_code == 409

    secret = billing_config.STRIPE_SECRET_KEY
    try:
        billing_config.STRIPE_SECRET_KEY = ""
        client.post("/api/auth/logout")
        client.post(
            "/api/auth/login",
            json={"email": "fresh@example.com", "password": "password12"},
        )
        # fresh user does not exist yet
        registered = client.post(
            "/api/auth/register",
            json={"email": "fresh@example.com", "password": "password12"},
        )
        assert registered.status_code == 200
        missing = client.post("/api/billing/checkout")
        assert missing.status_code == 503
        assert "sk_" not in missing.text
    finally:
        billing_config.STRIPE_SECRET_KEY = secret
    print("[OK] http auth and gates")


def test_signed_webhook_and_bad_signature():
    client = TestClient(app)
    user = get_db().create_user("hook@example.com", hash_password("password12"))
    event = _subscription(user["id"], "active", PRICE, "evt_http_1")
    payload = json.dumps(event).encode()
    ok = client.post(
        "/api/billing/webhook",
        content=payload,
        headers={"stripe-signature": _sign(payload)},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["duplicate"] is False
    assert is_entitled(get_db().get_membership(user["id"]))

    again = client.post(
        "/api/billing/webhook",
        content=payload,
        headers={"stripe-signature": _sign(payload)},
    )
    assert again.status_code == 200
    assert again.json()["duplicate"] is True

    bad = client.post(
        "/api/billing/webhook",
        content=payload,
        headers={"stripe-signature": "t=1,v1=deadbeef"},
    )
    assert bad.status_code == 400

    live = json.loads(payload)
    live["id"] = "evt_live"
    live["livemode"] = True
    live["data"]["object"]["status"] = "canceled"
    live_payload = json.dumps(live).encode()
    rejected = client.post(
        "/api/billing/webhook",
        content=live_payload,
        headers={"stripe-signature": _sign(live_payload)},
    )
    assert rejected.status_code == 400
    assert is_entitled(get_db().get_membership(user["id"]))
    print("[OK] signed webhook")


if __name__ == "__main__":
    test_format_gate()
    test_password_and_session()
    test_checkout_is_idempotent_and_blocks_second_payment()
    test_webhook_grants_once_and_ignores_replay()
    test_failed_event_can_retry()
    test_paid_checkout_grants_and_wrong_price_does_not()
    test_price_must_be_monthly_cny()
    test_http_auth_and_feature_gates()
    test_signed_webhook_and_bad_signature()
    print("ALL MEMBERSHIP TESTS PASSED")
