"""Who may use HD download and AI. Keep frontend/src/utils/membership.js in sync."""

from __future__ import annotations

import re

import billing_config

_CAPPED_VIDEO = re.compile(r"bestvideo\[height<=(\d+)\]\+bestaudio/best\Z")
_MEMBER_STATUSES = {"active", "trialing"}


def format_requires_membership(format_id: str) -> bool:
    """720p and below, plus audio-only, stay free. Anything else is Pro.

    Unknown format ids are rejected for free users so a client cannot bypass
    the selector by sending a raw high-resolution yt-dlp format.
    """
    if format_id == "bestaudio/best":
        return False
    match = _CAPPED_VIDEO.fullmatch(format_id or "")
    if match:
        return int(match.group(1)) > billing_config.FREE_MAX_HEIGHT
    return True


def is_entitled(row: dict | None) -> bool:
    if not row:
        return False
    if row.get("status") not in _MEMBER_STATUSES:
        return False
    price_id = billing_config.STRIPE_PRICE_ID
    return bool(price_id) and row.get("price_id") == price_id
