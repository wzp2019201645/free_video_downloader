"""Bilibili anti-bot helpers: cookie warmup and yt-dlp extractor patch."""

from __future__ import annotations

import http.cookiejar
import tempfile
import urllib.request
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

BILIBILI_HOSTS = ("bilibili.com", "b23.tv")
DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def is_bilibili_url(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(host == h or host.endswith(f".{h}") for h in BILIBILI_HOSTS)


def warmup_bilibili_cookies(url: str, user_agent: str = DEFAULT_UA) -> Optional[str]:
    """
    Visit Bilibili homepage and target page to obtain buvid3 cookies.
    Returns path to a Netscape cookie file, or None on failure.
    """
    if not is_bilibili_url(url):
        return None

    try:
        from curl_cffi import requests as cffi_requests

        session = cffi_requests.Session(impersonate="edge101")
        session.get("https://www.bilibili.com/", timeout=15)
        session.get(url, timeout=15, headers={"Referer": "https://www.bilibili.com/"})

        cookiefile = tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        )
        cookiefile.write("# Netscape HTTP Cookie File\n")
        for name, value in session.cookies.items():
            cookiefile.write(
                f".bilibili.com\tTRUE\t/\tFALSE\t0\t{name}\t{value}\n"
            )
        cookiefile.close()
        return cookiefile.name
    except Exception:
        pass

    try:
        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        opener.addheaders = [("User-Agent", user_agent)]
        opener.open("https://www.bilibili.com/", timeout=15)
        opener.open(url, timeout=15)

        cookiefile = tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        )
        cookiefile.write("# Netscape HTTP Cookie File\n")
        for cookie in jar:
            cookiefile.write(
                f"{cookie.domain}\tTRUE\t{cookie.path}\tFALSE\t"
                f"{int(cookie.expires or 0)}\t{cookie.name}\t{cookie.value}\n"
            )
        cookiefile.close()
        return cookiefile.name
    except Exception:
        return None


_patch_applied = False


def apply_bilibili_patch() -> None:
    """
    Bilibili embeds playinfo in the webpage for all users, but yt-dlp only
    reads it when SESSDATA exists. Treat buvid3 as sufficient to use embedded data.
    """
    global _patch_applied
    if _patch_applied:
        return

    from yt_dlp.extractor.bilibili import BiliBiliIE

    def _patched_is_logged_in(self):
        cookies = self._get_cookies("https://api.bilibili.com")
        return bool(cookies.get("SESSDATA") or cookies.get("buvid3"))

    BiliBiliIE.is_logged_in = property(_patched_is_logged_in)
    _patch_applied = True
