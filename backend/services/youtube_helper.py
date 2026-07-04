"""YouTube URL normalization and yt-dlp options."""

from __future__ import annotations

import re
import socket
from urllib.parse import parse_qs, urlparse

YOUTUBE_HOSTS = (
    "youtube.com",
    "youtu.be",
    "youtube-nocookie.com",
    "m.youtube.com",
    "music.youtube.com",
)

# Common local proxy ports (Clash / V2RayN / etc.)
_COMMON_PROXY_PORTS = (7890, 7897, 10809, 10808, 20171, 33210)


def is_youtube_url(url: str) -> bool:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    return any(host == h or host.endswith(f".{h}") for h in YOUTUBE_HOSTS)


def normalize_youtube_url(url: str) -> str:
    """
    Strip playlist/radio params and return a single-video watch URL.
    Supports watch, youtu.be, shorts, and music.youtube.com links.
    """
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower()

    if "youtu.be" in host:
        video_id = parsed.path.lstrip("/").split("/")[0]
    elif "/shorts/" in parsed.path:
        video_id = parsed.path.split("/shorts/", 1)[1].split("/")[0]
    else:
        video_id = parse_qs(parsed.query).get("v", [None])[0]

    if not video_id:
        match = re.search(r"(?:v=|/shorts/|youtu\.be/)([A-Za-z0-9_-]{11})", url)
        video_id = match.group(1) if match else None

    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"
    return url.strip()


def detect_local_proxy() -> str | None:
    for port in _COMMON_PROXY_PORTS:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                return f"http://127.0.0.1:{port}"
        except OSError:
            continue
    return None


def apply_youtube_opts(opts: dict, url: str) -> dict:
    if not is_youtube_url(url):
        return opts

    opts["noplaylist"] = True
    extractor_args = dict(opts.get("extractor_args") or {})
    extractor_args["youtube"] = {
        "player_client": ["android", "web", "tv_embedded"],
    }
    opts["extractor_args"] = extractor_args
    return opts


def friendly_youtube_error(exc: Exception) -> str | None:
    if not isinstance(exc, Exception):
        return None
    msg = str(exc).lower()
    if "youtube" not in msg and "youtu.be" not in msg:
        return None
    if any(k in msg for k in ("timed out", "timeout", "connection", "unable to download", "network")):
        return (
            "无法连接 YouTube。国内网络需开启代理，并设置环境变量 "
            "YTDLP_PROXY=http://127.0.0.1:7890（端口按你的代理软件调整）。"
            "若已开 Clash/V2Ray，程序也会自动尝试检测本地代理端口。"
        )
    if "sign in" in msg or "bot" in msg or "cookies" in msg:
        return "YouTube 要求验证，请尝试在浏览器登录 YouTube 后重试，或配置代理。"
    return None
