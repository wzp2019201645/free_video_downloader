"""Proxy external video thumbnails (Bilibili CDN requires Referer)."""

import asyncio
import urllib.request
from urllib.parse import urlparse

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def normalize_thumbnail_url(url: str | None) -> str | None:
    if not url:
        return None
    if url.startswith("http://"):
        url = "https://" + url[7:]
    return url


def _referer_for(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if "hdslb.com" in host or "bilibili.com" in host:
        return "https://www.bilibili.com/"
    if "ytimg.com" in host or "youtube.com" in host:
        return "https://www.youtube.com/"
    return url


def _fetch_thumbnail_sync(url: str) -> tuple[bytes, str]:
    url = normalize_thumbnail_url(url) or url
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": DEFAULT_UA,
            "Referer": _referer_for(url),
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read()
        content_type = resp.headers.get("Content-Type", "image/jpeg")
        if not content_type.startswith("image/"):
            content_type = "image/jpeg"
        return data, content_type


async def fetch_thumbnail(url: str) -> tuple[bytes, str]:
    return await asyncio.to_thread(_fetch_thumbnail_sync, url)
