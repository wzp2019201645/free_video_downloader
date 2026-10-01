"""Email + password accounts. The session cookie is HttpOnly."""

from __future__ import annotations

import threading
import time

from fastapi import APIRouter, HTTPException, Request, Response

import billing_config
from models.billing_schemas import Credentials
from services.access import current_user
from services.billing_service import public_user
from services.membership_db import get_db
from services.passwords import DUMMY_PASSWORD_HASH, hash_password, verify_password
from services.session_token import sign_session

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])

_LOCK = threading.Lock()
_HITS: dict[str, list[float]] = {}


def _client_key(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _allow(bucket: str, limit: int, window_seconds: int) -> bool:
    now = time.time()
    with _LOCK:
        recent = [stamp for stamp in _HITS.get(bucket, []) if now - stamp < window_seconds]
        if len(recent) >= limit:
            _HITS[bucket] = recent
            return False
        recent.append(now)
        _HITS[bucket] = recent
        return True


def _set_session_cookie(response: Response, user_id: str) -> None:
    response.set_cookie(
        key=billing_config.SESSION_COOKIE,
        value=sign_session(user_id),
        httponly=True,
        secure=billing_config.PUBLIC_APP_URL.startswith("https://"),
        samesite="lax",
        max_age=billing_config.SESSION_DAYS * 86400,
        path="/",
    )


@auth_router.post("/register")
def register(body: Credentials, request: Request, response: Response):
    if not _allow(f"register:{_client_key(request)}", limit=5, window_seconds=600):
        raise HTTPException(status_code=429, detail="注册太频繁，请稍后再试")
    try:
        user = get_db().create_user(body.email, hash_password(body.password))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _set_session_cookie(response, user["id"])
    return {"user": public_user(user)}


@auth_router.post("/login")
def login(body: Credentials, request: Request, response: Response):
    if not _allow(f"login:{_client_key(request)}", limit=10, window_seconds=600):
        raise HTTPException(status_code=429, detail="登录太频繁，请稍后再试")
    user = get_db().get_user_by_email(body.email)
    stored = user["password_hash"] if user else DUMMY_PASSWORD_HASH
    if not user or not verify_password(body.password, stored):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    _set_session_cookie(response, user["id"])
    return {"user": public_user(user)}


@auth_router.post("/logout")
def logout(response: Response):
    response.delete_cookie(billing_config.SESSION_COOKIE, path="/")
    return {"ok": True}


@auth_router.get("/me")
def me(request: Request):
    user = current_user(request)
    if not user:
        return {"user": None}
    return {"user": public_user(user)}
