"""Douyin (抖音) helpers: URL normalization and cookie setup."""

from __future__ import annotations

import http.cookiejar
import os
import tempfile
import urllib.request
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

DOUYIN_HOSTS = ("douyin.com", "iesdouyin.com")


def is_douyin_url(url: str) -> bool:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    return any(host == h or host.endswith(f".{h}") for h in DOUYIN_HOSTS)


def normalize_douyin_url(url: str) -> str:
    """Return canonical URL; short links (v.douyin.com) are resolved by yt-dlp."""
    return url.strip()


def _cookies_search_paths() -> list[Path]:
    backend_dir = Path(__file__).resolve().parent.parent
    project_dir = backend_dir.parent
    return [
        backend_dir / "cookies" / "douyin.txt",
        project_dir / "cookies" / "douyin.txt",
    ]


def resolve_douyin_cookiefile() -> Optional[str]:
    from config import YTDLP_COOKIES_FILE

    if YTDLP_COOKIES_FILE and Path(YTDLP_COOKIES_FILE).exists():
        return YTDLP_COOKIES_FILE
    for path in _cookies_search_paths():
        if path.exists() and path.stat().st_size > 0:
            return str(path)
    return None


def warmup_douyin_cookies(url: str, user_agent: str = DEFAULT_UA) -> Optional[str]:
    """Best-effort cookie warmup; usually needs browser-exported cookies for s_v_web_id."""
    if not is_douyin_url(url):
        return None

    try:
        from curl_cffi import requests as cffi_requests

        session = cffi_requests.Session(impersonate="chrome131")
        session.get("https://www.douyin.com/", timeout=15)
        session.get(url, timeout=15, headers={"Referer": "https://www.douyin.com/"})

        cookiefile = tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        )
        cookiefile.write("# Netscape HTTP Cookie File\n")
        for name, value in session.cookies.items():
            cookiefile.write(f".douyin.com\tTRUE\t/\tFALSE\t0\t{name}\t{value}\n")
        cookiefile.close()
        return cookiefile.name if session.cookies else None
    except Exception:
        pass

    try:
        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        opener.addheaders = [("User-Agent", user_agent)]
        opener.open("https://www.douyin.com/", timeout=15)
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
        return cookiefile.name if jar else None
    except Exception:
        return None


def merge_cookie_files(base_file: str, extra_file: str) -> str:
    """Merge two Netscape cookie files into a temp file."""
    merged = tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    )
    merged.write("# Netscape HTTP Cookie File\n")
    seen: set[tuple[str, str]] = set()
    for path in (base_file, extra_file):
        with open(path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                parts = line.rstrip("\n").split("\t")
                if len(parts) >= 7:
                    key = (parts[0], parts[5])
                    if key in seen:
                        continue
                    seen.add(key)
                merged.write(line if line.endswith("\n") else line + "\n")
    merged.close()
    return merged.name


def apply_douyin_opts(
    opts: dict,
    url: str,
    temp_cookies: list[str],
) -> None:
    if not is_douyin_url(url):
        return

    opts.setdefault("http_headers", {})
    opts["http_headers"].setdefault("Referer", "https://www.douyin.com/")

    cookiefile = resolve_douyin_cookiefile()
    warmup = warmup_douyin_cookies(url)

    if cookiefile and warmup:
        merged = merge_cookie_files(cookiefile, warmup)
        opts["cookiefile"] = merged
        temp_cookies.append(warmup)
        temp_cookies.append(merged)
    elif cookiefile:
        opts["cookiefile"] = cookiefile
    elif warmup:
        opts["cookiefile"] = warmup
        temp_cookies.append(warmup)

    from config import YTDLP_COOKIES_BROWSER

    if YTDLP_COOKIES_BROWSER and "cookiefile" not in opts:
        opts["cookiesfrombrowser"] = (YTDLP_COOKIES_BROWSER,)


def friendly_douyin_error(exc: Exception) -> str | None:
    msg = str(exc)
    lowered = msg.lower()
    if not any(k in lowered for k in ("douyin", "iesdouyin", "抖音", "aweme")):
        if "分享页" not in msg and "视频" not in msg and "链接" not in msg:
            return None
    if "status_self_see" in lowered or "不可访问" in msg or "已删除" in msg or "私密" in msg:
        return msg
    if "未找到有效的抖音链接" in msg or "无法从链接中提取视频ID" in msg:
        return msg
    if "fresh cookies" in lowered or "cookie" in lowered:
        return (
            "抖音解析失败，请确认链接有效且视频为公开状态。"
            "若链接来自分享短链，请粘贴完整链接后重试。"
        )
    return msg if msg else None
