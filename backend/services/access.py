"""Cookie session lookup and Pro feature gates."""

from __future__ import annotations

from fastapi import HTTPException, Request

import billing_config
from services.entitlements import format_requires_membership, is_entitled
from services.membership_db import get_db
from services.session_token import verify_session

_HD_LOGIN = "1080p 及以上清晰度需要登录并开通 Pro 会员"
_HD_MEMBER = "1080p 及以上清晰度仅 Pro 会员可用。720p 及以下、仅音频可以免费下载。"
_AI_LOGIN = "AI 总结、字幕、导图和问答需要登录并开通 Pro 会员"
_AI_MEMBER = "AI 总结、字幕、导图和问答仅 Pro 会员可用"


def current_user(request: Request) -> dict | None:
    token = request.cookies.get(billing_config.SESSION_COOKIE, "")
    if not token:
        return None
    user_id = verify_session(token)
    if not user_id:
        return None
    return get_db().get_user_by_id(user_id)


def _refresh(user_id: str) -> None:
    from services.billing_service import billing

    billing.refresh_if_period_ended(user_id)


def member_user(request: Request) -> dict | None:
    user = current_user(request)
    if not user:
        return None
    _refresh(user["id"])
    if not is_entitled(get_db().get_membership(user["id"])):
        return None
    return user


def assert_can_download(request: Request, format_id: str) -> None:
    if not format_requires_membership(format_id):
        return
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail=_HD_LOGIN)
    _refresh(user["id"])
    if not is_entitled(get_db().get_membership(user["id"])):
        raise HTTPException(status_code=403, detail=_HD_MEMBER)


def assert_member(request: Request) -> dict:
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail=_AI_LOGIN)
    _refresh(user["id"])
    if not is_entitled(get_db().get_membership(user["id"])):
        raise HTTPException(status_code=403, detail=_AI_MEMBER)
    return user
