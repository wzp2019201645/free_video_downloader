"""Bilibili WBI request signing (standalone, no changes to bilibili_helper)."""

from __future__ import annotations

import hashlib
import time
import urllib.parse
from functools import reduce
from typing import Any

import requests

from services.bilibili_helper import DEFAULT_UA

_MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52,
]

_NAV_URL = "https://api.bilibili.com/x/web-interface/nav"


def _mixin_key(orig: str) -> str:
    return reduce(lambda s, i: s + orig[i], _MIXIN_KEY_ENC_TAB, "")[:32]


def get_wbi_keys(session: requests.Session | None = None) -> tuple[str, str]:
    sess = session or requests.Session()
    resp = sess.get(
        _NAV_URL,
        headers={"User-Agent": DEFAULT_UA, "Referer": "https://www.bilibili.com/"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()["data"]["wbi_img"]
    img_key = data["img_url"].rsplit("/", 1)[1].split(".")[0]
    sub_key = data["sub_url"].rsplit("/", 1)[1].split(".")[0]
    return img_key, sub_key


def sign_wbi_params(params: dict[str, Any], img_key: str, sub_key: str) -> dict[str, Any]:
    mixin = _mixin_key(img_key + sub_key)
    signed = dict(params)
    signed["wts"] = int(time.time())
    signed = dict(sorted(signed.items()))
    filtered = {
        k: "".join(ch for ch in str(v) if ch not in "!'()*")
        for k, v in signed.items()
    }
    query = urllib.parse.urlencode(filtered)
    signed["w_rid"] = hashlib.md5((query + mixin).encode()).hexdigest()
    return signed
