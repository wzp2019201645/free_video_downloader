"""Membership and Stripe settings. Secrets stay in backend/.env."""

from __future__ import annotations

import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

_BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(_BACKEND_DIR / ".env")

DATA_DIR = Path(os.getenv("MEMBERSHIP_DATA_DIR", str(_BACKEND_DIR / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = Path(os.getenv("MEMBERSHIP_DB_PATH", str(DATA_DIR / "membership.db")))

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "").strip()
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID", "").strip()
STRIPE_PROXY = os.getenv("STRIPE_PROXY", "").strip()
PUBLIC_APP_URL = os.getenv("PUBLIC_APP_URL", "http://localhost:3000").rstrip("/")

SESSION_COOKIE = "fvd_session"
SESSION_DAYS = 14

# Agreed test plan: monthly Pro at 19.00 CNY. Stripe stores CNY in fen.
EXPECTED_CURRENCY = "cny"
EXPECTED_UNIT_AMOUNT = 1900
EXPECTED_INTERVAL = "month"
FREE_MAX_HEIGHT = 720


def _load_session_secret() -> str:
    configured = os.getenv("SESSION_SECRET", "").strip()
    if configured:
        return configured
    path = DATA_DIR / "session_secret"
    if path.is_file():
        existing = path.read_text(encoding="utf-8").strip()
        if existing:
            return existing
    secret = secrets.token_urlsafe(32)
    path.write_text(secret, encoding="utf-8")
    return secret


SESSION_SECRET = _load_session_secret()


def stripe_proxy() -> str | None:
    for key in ("STRIPE_PROXY", "HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"):
        value = os.getenv(key, "").strip()
        if value:
            return value
    return STRIPE_PROXY or None


def stripe_configured() -> bool:
    return bool(STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET and STRIPE_PRICE_ID)
