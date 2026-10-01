"""HttpOnly session cookie payload. The browser cannot read or edit the user id."""

from __future__ import annotations

import hashlib
import hmac
import time

import billing_config


def sign_session(user_id: str, now: int | None = None) -> str:
    issued_at = int(time.time() if now is None else now)
    expires_at = issued_at + billing_config.SESSION_DAYS * 86400
    body = f"{user_id}.{expires_at}"
    signature = hmac.new(
        billing_config.SESSION_SECRET.encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{body}.{signature}"


def verify_session(token: str, now: int | None = None) -> str | None:
    try:
        user_id, expires_at, signature = token.rsplit(".", 2)
        if not user_id or "." in user_id:
            return None
        body = f"{user_id}.{expires_at}"
        expected = hmac.new(
            billing_config.SESSION_SECRET.encode("utf-8"),
            body.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            return None
        if int(expires_at) < int(time.time() if now is None else now):
            return None
        return user_id
    except (ValueError, TypeError):
        return None
