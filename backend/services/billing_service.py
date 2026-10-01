"""Stripe Checkout subscription, webhook fulfillment, and customer portal.

Card numbers stay on Stripe's hosted page. Membership is granted only after the
server verifies a paid Checkout Session or a signed subscription webhook, and
the price id matches the configured monthly CNY plan.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Any

import billing_config
from services.entitlements import is_entitled
from services.membership_db import MembershipDB, get_db

logger = logging.getLogger("billing")

_MEMBER_BLOCKING = {"active", "trialing"}
_PORTAL_STATUSES = {"past_due", "unpaid"}
_PAID_CHECKOUT = {"paid", "no_payment_required"}


class BillingError(Exception):
    pass


class BillingNotConfigured(BillingError):
    pass


class AlreadyMember(BillingError):
    pass


class NeedsPortal(BillingError):
    pass


class NoCustomer(BillingError):
    pass


class PriceMisconfigured(BillingError):
    pass


class InvalidSignature(BillingError):
    pass


class LivemodeMismatch(BillingError):
    pass


class NotYourSession(BillingError):
    pass


def _as_dict(obj: Any) -> dict:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    to_dict = getattr(obj, "to_dict", None)
    if callable(to_dict):
        converted = to_dict()
        if isinstance(converted, dict):
            return converted
    return dict(obj)


def _id(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        nested = value.get("id")
        return nested if isinstance(nested, str) else None
    nested = getattr(value, "id", None)
    return nested if isinstance(nested, str) else None


def _price_ids(subscription: dict) -> set[str]:
    items = ((subscription.get("items") or {}).get("data")) or []
    found: set[str] = set()
    for item in items:
        price_id = _id(item.get("price"))
        if price_id:
            found.add(price_id)
    return found


def _period_end(subscription: dict) -> int | None:
    direct = subscription.get("current_period_end")
    if direct:
        return int(direct)
    items = ((subscription.get("items") or {}).get("data")) or []
    ends = [int(item["current_period_end"]) for item in items if item.get("current_period_end")]
    return max(ends) if ends else None


def _safe_stripe_message(exc: Exception) -> str:
    text = getattr(exc, "user_message", None) or str(exc)
    if "sk_" in text or "whsec_" in text:
        return "请求被拒绝"
    return text[:300]


def assert_expected_price(price: dict) -> None:
    currency = (price.get("currency") or "").lower()
    amount = price.get("unit_amount")
    recurring = price.get("recurring") or {}
    interval = recurring.get("interval")
    interval_count = recurring.get("interval_count") or 1
    if (
        currency == billing_config.EXPECTED_CURRENCY
        and amount == billing_config.EXPECTED_UNIT_AMOUNT
        and interval == billing_config.EXPECTED_INTERVAL
        and interval_count == 1
    ):
        return
    shown = "未知"
    if isinstance(amount, int):
        shown = f"{amount / 100:.2f} {currency or '?'} / {interval or '?'}"
    raise PriceMisconfigured(
        "Stripe 价格必须是每月 19.00 人民币（CNY）。"
        f"当前 Price 是 {shown}。"
        "请在 Stripe 测试模式新建「每月 ¥19.00 CNY」价格，并把 Price ID 写入 STRIPE_PRICE_ID 后重启后端。"
    )


class StripeGateway:
    """Thin wrapper around stripe-python 15 StripeClient. No card data here."""

    def __init__(self):
        self._client = None
        self._price_ok = False

    def configured(self) -> bool:
        return billing_config.stripe_configured()

    def client(self):
        if not billing_config.STRIPE_SECRET_KEY:
            raise BillingNotConfigured("支付功能尚未配置")
        if self._client is None:
            import stripe

            kwargs: dict[str, Any] = {"max_network_retries": 2}
            proxy = billing_config.stripe_proxy()
            if proxy:
                kwargs["proxy"] = proxy
            self._client = stripe.StripeClient(billing_config.STRIPE_SECRET_KEY, **kwargs)
        return self._client

    def construct_event(self, payload: bytes, signature: str) -> dict:
        if not billing_config.STRIPE_WEBHOOK_SECRET:
            raise BillingNotConfigured("支付功能尚未配置")
        try:
            event = self.client().construct_event(
                payload,
                signature,
                billing_config.STRIPE_WEBHOOK_SECRET,
            )
        except Exception as exc:
            if exc.__class__.__name__ == "SignatureVerificationError":
                raise InvalidSignature("Webhook 签名无效") from exc
            raise
        return _as_dict(event)

    def retrieve_price(self, price_id: str) -> dict:
        return _as_dict(self.client().v1.prices.retrieve(price_id))

    def create_customer(self, email: str, user_id: str) -> dict:
        customer = self.client().v1.customers.create(
            params={"email": email, "metadata": {"user_id": user_id}},
            options={"idempotency_key": f"customer-{user_id}"},
        )
        return _as_dict(customer)

    def list_subscriptions(self, customer_id: str) -> list[dict]:
        result = self.client().v1.subscriptions.list(
            params={"customer": customer_id, "status": "all", "limit": 20}
        )
        data = _as_dict(result).get("data") or []
        return [_as_dict(item) for item in data]

    def retrieve_subscription(self, subscription_id: str) -> dict:
        return _as_dict(self.client().v1.subscriptions.retrieve(subscription_id))

    def retrieve_session(self, session_id: str) -> dict:
        session = self.client().v1.checkout.sessions.retrieve(
            session_id,
            params={"expand": ["line_items"]},
        )
        return _as_dict(session)

    def create_checkout_session(
        self,
        *,
        customer_id: str,
        user_id: str,
        idempotency_key: str,
    ) -> dict:
        success_url = (
            billing_config.PUBLIC_APP_URL
            + "/?billing=success&session_id={CHECKOUT_SESSION_ID}"
        )
        cancel_url = billing_config.PUBLIC_APP_URL + "/?billing=cancel"
        session = self.client().v1.checkout.sessions.create(
            params={
                "mode": "subscription",
                "customer": customer_id,
                "client_reference_id": user_id,
                "success_url": success_url,
                "cancel_url": cancel_url,
                "locale": "zh",
                "line_items": [{"price": billing_config.STRIPE_PRICE_ID, "quantity": 1}],
                "metadata": {"user_id": user_id},
                "subscription_data": {"metadata": {"user_id": user_id}},
            },
            options={"idempotency_key": idempotency_key},
        )
        return _as_dict(session)

    def create_portal(self, customer_id: str) -> dict:
        session = self.client().v1.billing_portal.sessions.create(
            params={
                "customer": customer_id,
                "return_url": billing_config.PUBLIC_APP_URL + "/",
            }
        )
        return _as_dict(session)


class BillingService:
    def __init__(self, db: MembershipDB | None = None, gateway: StripeGateway | None = None):
        self.db = db or get_db()
        self.gateway = gateway or StripeGateway()
        self._locks_guard = threading.Lock()
        self._user_locks: dict[str, threading.Lock] = {}

    def _user_lock(self, user_id: str) -> threading.Lock:
        with self._locks_guard:
            lock = self._user_locks.get(user_id)
            if lock is None:
                lock = threading.Lock()
                self._user_locks[user_id] = lock
            return lock

    def ensure_price(self) -> None:
        if not self.gateway.configured():
            raise BillingNotConfigured("支付功能尚未配置")
        if self.gateway._price_ok:
            return
        price = self.gateway.retrieve_price(billing_config.STRIPE_PRICE_ID)
        assert_expected_price(price)
        self.gateway._price_ok = True

    def refresh_if_period_ended(self, user_id: str) -> None:
        if not self.gateway.configured():
            return
        row = self.db.get_membership(user_id)
        if not row or not row.get("stripe_subscription_id"):
            return
        period_end = row.get("current_period_end") or 0
        if row.get("status") not in _MEMBER_BLOCKING or not period_end or period_end >= time.time():
            return
        try:
            subscription = self.gateway.retrieve_subscription(row["stripe_subscription_id"])
        except Exception as exc:
            logger.warning("refresh membership skipped: %s", exc.__class__.__name__)
            return
        mutation = self._mutation_from_subscription(subscription)
        if mutation:
            self.db.apply_now(mutation)

    def create_checkout(self, user: dict) -> str:
        with self._user_lock(user["id"]):
            if is_entitled(self.db.get_membership(user["id"])):
                raise AlreadyMember("你已经是 Pro 会员，无需重复付款")
            self.ensure_price()
            customer_id = self._ensure_customer(user)
            self._reject_duplicate_subscription(user["id"], customer_id)
            return self._reuse_or_create_session(user["id"], customer_id)

    def create_portal(self, user: dict) -> str:
        self.ensure_price()
        row = self.db.get_membership(user["id"])
        customer_id = row.get("stripe_customer_id") if row else None
        if not customer_id:
            raise NoCustomer("还没有支付记录，无法打开订阅管理")
        portal = self.gateway.create_portal(customer_id)
        url = portal.get("url") or ""
        if not url.startswith("https://billing.stripe.com/"):
            raise BillingError("订阅管理链接异常")
        return url

    def confirm_session(self, user: dict, session_id: str) -> None:
        if not session_id.startswith("cs_"):
            raise BillingError("订单号不正确")
        self.ensure_price()
        session = self.gateway.retrieve_session(session_id)
        owner = session.get("client_reference_id") or (session.get("metadata") or {}).get("user_id")
        if owner != user["id"]:
            raise NotYourSession("这不是当前账号的订单")
        if session.get("payment_status") not in _PAID_CHECKOUT:
            return
        mutation = self._mutation_from_checkout(session)
        if mutation:
            self.db.apply_now(mutation)

    def handle_event(self, event: dict) -> str:
        event = _as_dict(event)
        self._check_livemode(event)
        event_id = event.get("id")
        if not event_id:
            raise BillingError("事件缺少 id")
        mutation = self._mutation_for_event(event)
        applied = self.db.process_once(event_id, event.get("type") or "", mutation)
        if applied:
            logger.info("stripe event %s %s", event.get("type"), event_id)
        return "ok" if applied else "duplicate"

    def _check_livemode(self, event: dict) -> None:
        live_event = bool(event.get("livemode"))
        live_key = billing_config.STRIPE_SECRET_KEY.startswith("sk_live_")
        if live_event != live_key:
            raise LivemodeMismatch("测试环境和正式环境的支付事件不能混用")

    def _ensure_customer(self, user: dict) -> str:
        row = self.db.get_membership(user["id"])
        if row and row.get("stripe_customer_id"):
            return row["stripe_customer_id"]
        customer = self.gateway.create_customer(user["email"], user["id"])
        customer_id = _id(customer)
        if not customer_id:
            raise BillingError("创建 Stripe 客户失败")
        self.db.set_customer_id(user["id"], customer_id)
        return customer_id

    def _reject_duplicate_subscription(self, user_id: str, customer_id: str) -> None:
        for subscription in self.gateway.list_subscriptions(customer_id):
            if billing_config.STRIPE_PRICE_ID not in _price_ids(subscription):
                continue
            status = subscription.get("status")
            mutation = self._mutation_from_subscription(subscription, user_id=user_id)
            if mutation:
                self.db.apply_now(mutation)
            if status in _MEMBER_BLOCKING:
                raise AlreadyMember("你已经是 Pro 会员，无需重复付款")
            if status in _PORTAL_STATUSES:
                raise NeedsPortal("当前订阅扣款未成功。请先更新付款方式，不要再次开通，以免重复扣款。")

    def _reuse_or_create_session(self, user_id: str, customer_id: str) -> str:
        row = self.db.get_checkout(user_id)
        if row and row.get("session_id"):
            existing = self.gateway.retrieve_session(row["session_id"])
            if existing.get("status") == "open":
                return self._checkout_url(existing)
            idempotency_key = f"checkout-{user_id}-{uuid.uuid4().hex}"
        elif row and row.get("idempotency_key"):
            # Previous create may have reached Stripe without us saving the session id.
            idempotency_key = row["idempotency_key"]
        else:
            idempotency_key = f"checkout-{user_id}-{uuid.uuid4().hex}"
        self.db.save_checkout(user_id, idempotency_key, None)
        created = self.gateway.create_checkout_session(
            customer_id=customer_id,
            user_id=user_id,
            idempotency_key=idempotency_key,
        )
        session_id = _id(created)
        self.db.save_checkout(user_id, idempotency_key, session_id)
        return self._checkout_url(created)

    def _checkout_url(self, session: dict) -> str:
        url = session.get("url") or ""
        if not url.startswith("https://checkout.stripe.com/"):
            raise BillingError("支付链接异常")
        return url

    def _mutation_for_event(self, event: dict):
        event_type = event.get("type")
        obj = _as_dict((event.get("data") or {}).get("object"))
        if event_type in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
            return self._mutation_from_checkout(obj)
        if event_type in (
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        ):
            return self._mutation_from_subscription(obj)
        return None

    def _mutation_from_checkout(self, session: dict):
        session = _as_dict(session)
        if session.get("mode") != "subscription":
            return None
        if session.get("payment_status") not in _PAID_CHECKOUT:
            return None
        if "line_items" not in session and session.get("id"):
            session = self.gateway.retrieve_session(session["id"])
        user_id = session.get("client_reference_id") or (session.get("metadata") or {}).get("user_id")
        meta_user = (session.get("metadata") or {}).get("user_id")
        if meta_user and user_id and meta_user != user_id:
            logger.warning("checkout user mismatch for %s", session.get("id"))
            return None
        if not user_id or not self.db.get_user_by_id(user_id):
            logger.warning("checkout has no local user for %s", session.get("id"))
            return None
        if not self._session_has_expected_price(session):
            logger.warning("checkout price mismatch for %s", session.get("id"))
            return None
        subscription_id = _id(session.get("subscription"))
        if not subscription_id:
            return None
        subscription = self.gateway.retrieve_subscription(subscription_id)
        return self._mutation_from_subscription(
            subscription,
            user_id=user_id,
            customer_id=_id(session.get("customer")),
        )

    def _session_has_expected_price(self, session: dict) -> bool:
        items = ((session.get("line_items") or {}).get("data")) or []
        for item in items:
            if _id(item.get("price")) == billing_config.STRIPE_PRICE_ID:
                return True
        return False

    def _mutation_from_subscription(
        self,
        subscription: dict,
        user_id: str | None = None,
        customer_id: str | None = None,
    ):
        subscription = _as_dict(subscription)
        subscription_id = _id(subscription)
        if not subscription_id:
            return None
        resolved_user = user_id or (subscription.get("metadata") or {}).get("user_id")
        if resolved_user and not self.db.get_user_by_id(resolved_user):
            resolved_user = None
        if not resolved_user:
            row = self.db.get_membership_by_subscription(subscription_id)
            if row is None:
                row = self.db.get_membership_by_customer(_id(subscription.get("customer")))
            resolved_user = row["user_id"] if row else None
        if not resolved_user:
            logger.warning("subscription %s is not linked to a user", subscription_id)
            return None
        meta_user = (subscription.get("metadata") or {}).get("user_id")
        if meta_user and meta_user != resolved_user:
            logger.warning("subscription user mismatch %s", subscription_id)
            return None
        prices = _price_ids(subscription)
        if prices:
            if billing_config.STRIPE_PRICE_ID in prices:
                price_id = billing_config.STRIPE_PRICE_ID
            else:
                price_id = next(iter(prices))
        else:
            existing = self.db.get_membership(resolved_user)
            price_id = existing.get("price_id") if existing else ""
        resolved_customer = customer_id or _id(subscription.get("customer"))
        status = subscription.get("status") or "canceled"
        period_end = _period_end(subscription)
        cancel_at_period_end = bool(subscription.get("cancel_at_period_end"))

        def apply(conn) -> None:
            self.db.upsert_membership(
                resolved_user,
                customer_id=resolved_customer,
                subscription_id=subscription_id,
                status=status,
                price_id=price_id or "",
                period_end=period_end,
                cancel_at_period_end=cancel_at_period_end,
                conn=conn,
            )

        return apply


billing = BillingService()


def public_user(user: dict) -> dict:
    billing.refresh_if_period_ended(user["id"])
    row = billing.db.get_membership(user["id"])
    period_end = row.get("current_period_end") if row else None
    return {
        "email": user["email"],
        "is_member": is_entitled(row),
        "membership_status": row.get("status") if row else None,
        "current_period_end": period_end,
        "cancel_at_period_end": bool(row.get("cancel_at_period_end")) if row else False,
        "has_billing_customer": bool(row and row.get("stripe_customer_id")),
    }
