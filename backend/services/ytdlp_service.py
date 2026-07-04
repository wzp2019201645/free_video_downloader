import asyncio
import os
from pathlib import Path
from typing import Callable, Optional

from config import resolve_ffmpeg_dir, resolve_proxy, YTDLP_COOKIES_BROWSER

import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget

from models.schemas import FormatInfo, VideoInfoResponse
from services.bilibili_helper import (
    DEFAULT_UA,
    apply_bilibili_patch,
    is_bilibili_url,
    warmup_bilibili_cookies,
)
from services.douyin_helper import is_douyin_url, normalize_douyin_url
from services.douyin_parser import DouyinParser
from services.thumbnail_proxy import normalize_thumbnail_url
from services.youtube_helper import (
    apply_youtube_opts,
    is_youtube_url,
    normalize_youtube_url,
)


def _build_quality_formats(info: dict) -> list[FormatInfo]:
    """Build user-friendly quality options using yt-dlp format selectors."""
    formats = info.get("formats") or []
    heights = sorted(
        {f["height"] for f in formats if f.get("height") and f.get("vcodec", "none") != "none"},
        reverse=True,
    )

    result: list[FormatInfo] = []

    result.append(
        FormatInfo(
            format_id="bestvideo+bestaudio/best",
            quality="最佳质量",
            ext="mp4",
        )
    )

    for h in heights[:8]:
        result.append(
            FormatInfo(
                format_id=f"bestvideo[height<={h}]+bestaudio/best",
                quality=f"{h}p",
                ext="mp4",
            )
        )

    audio_formats = [
        f for f in formats
        if f.get("acodec", "none") != "none" and f.get("vcodec", "none") == "none"
    ]
    if audio_formats:
        best_audio = max(audio_formats, key=lambda f: f.get("abr") or 0)
        result.append(
            FormatInfo(
                format_id="bestaudio/best",
                quality=f"仅音频 {int(best_audio.get('abr') or 128)}kbps",
                ext=best_audio.get("ext", "m4a"),
            )
        )

    return result


class YtdlpService:
    def __init__(self):
        apply_bilibili_patch()
        self._douyin = DouyinParser()
        self._base_opts = {
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "merge_output_format": "mp4",
        }
        self._temp_cookies: list[str] = []

    def _build_opts(self, url: str, **extra) -> dict:
        opts = {**self._base_opts, **extra}
        headers = dict(opts.get("http_headers") or {})
        headers.setdefault("User-Agent", DEFAULT_UA)
        if is_bilibili_url(url):
            headers.setdefault("Referer", url.split("?")[0])
            cookiefile = warmup_bilibili_cookies(url)
            if cookiefile:
                opts["cookiefile"] = cookiefile
                self._temp_cookies.append(cookiefile)
            opts["impersonate"] = ImpersonateTarget(
                client="edge", version="101", os="windows", os_version="10"
            )
        if is_youtube_url(url):
            url = normalize_youtube_url(url)
            apply_youtube_opts(opts, url)
            cookies_browser = YTDLP_COOKIES_BROWSER
            if cookies_browser:
                opts["cookiesfrombrowser"] = (cookies_browser,)
        opts["http_headers"] = headers
        proxy = resolve_proxy()
        if proxy:
            opts["proxy"] = proxy
        ffmpeg_dir = resolve_ffmpeg_dir()
        if ffmpeg_dir:
            opts["ffmpeg_location"] = ffmpeg_dir
        return opts

    def _prepare_url(self, url: str) -> str:
        if is_youtube_url(url):
            return normalize_youtube_url(url)
        if is_douyin_url(url):
            return normalize_douyin_url(url)
        return url.strip()

    def _cleanup_temp_cookies(self):
        for path in self._temp_cookies:
            try:
                os.unlink(path)
            except OSError:
                pass
        self._temp_cookies.clear()

    def _needs_ffmpeg(self, format_id: str) -> bool:
        lowered = format_id.lower()
        if "bestaudio" in lowered and "bestvideo" not in lowered and "+" not in format_id:
            return False
        return "+" in format_id or "bestvideo" in lowered or lowered in ("best",)

    def _ensure_ffmpeg(self) -> str:
        ffmpeg_dir = resolve_ffmpeg_dir()
        if not ffmpeg_dir:
            raise RuntimeError(
                "未检测到 ffmpeg/ffprobe，B站等平台的音视频合并需要完整 ffmpeg 安装。"
                "请将 tools/ffmpeg 解压到项目目录，或执行 winget install Gyan.FFmpeg"
            )
        ffmpeg = Path(ffmpeg_dir) / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        if not ffmpeg.exists():
            raise RuntimeError(f"ffmpeg 未找到: {ffmpeg}")
        if ffmpeg_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
        return str(ffmpeg)

    async def extract_info(self, url: str) -> VideoInfoResponse:
        return await asyncio.to_thread(self._extract_info_sync, url)

    def _extract_info_sync(self, url: str) -> VideoInfoResponse:
        url = self._prepare_url(url)
        if is_douyin_url(url):
            return self._douyin.parse_url(url)
        self._cleanup_temp_cookies()
        opts = self._build_opts(url, skip_download=True)
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
        finally:
            self._cleanup_temp_cookies()

        if info.get("_type") == "playlist":
            entries = info.get("entries") or []
            if entries:
                first = entries[0]
                if not isinstance(first, dict):
                    first = next(iter(entries), None)
                if isinstance(first, dict):
                    info = first

        formats = _build_quality_formats(info)
        thumbnail = normalize_thumbnail_url(info.get("thumbnail"))

        return VideoInfoResponse(
            title=info.get("title", "Unknown"),
            thumbnail=thumbnail,
            duration=int(info["duration"]) if info.get("duration") else None,
            uploader=info.get("uploader") or info.get("channel"),
            webpage_url=info.get("webpage_url") or url,
            formats=formats,
        )

    async def download(
        self,
        url: str,
        format_id: str,
        output_dir: Path,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> tuple[str, str]:
        return await asyncio.to_thread(
            self._download_sync, url, format_id, output_dir, progress_callback
        )

    def _download_sync(
        self,
        url: str,
        format_id: str,
        output_dir: Path,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> tuple[str, str]:
        url = self._prepare_url(url)
        if is_douyin_url(url):
            return self._douyin.download_to(url, output_dir, progress_callback)

        if self._needs_ffmpeg(format_id):
            self._ensure_ffmpeg()
        output_template = str(output_dir / "%(title)s.%(ext)s")

        last_pct = [0.0]

        def hook(d: dict):
            if not progress_callback:
                return
            status = d.get("status")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes", 0)
                if total > 0:
                    pct = min(downloaded / total * 100, 99.0)
                elif downloaded > 0:
                    pct = min(last_pct[0] + 1.0, 85.0)
                else:
                    pct = last_pct[0]
                last_pct[0] = max(last_pct[0], pct)
                progress_callback(last_pct[0])
            elif status == "finished":
                last_pct[0] = min(max(last_pct[0], 90.0), 99.0)
                progress_callback(last_pct[0])

        self._cleanup_temp_cookies()
        opts = self._build_opts(
            url,
            format=format_id,
            outtmpl=output_template,
            progress_hooks=[hook],
        )
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                filepath = Path(filename)
                if not filepath.exists() and filepath.with_suffix(".mp4").exists():
                    filepath = filepath.with_suffix(".mp4")
                    filename = filepath.name
        finally:
            self._cleanup_temp_cookies()

        if progress_callback:
            progress_callback(100.0)

        return Path(filename).name, str(filepath.resolve())
