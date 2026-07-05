"""yt-dlp helpers dedicated to subtitle/audio extraction for AI summary."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Callable, Optional

import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget

from config import resolve_ffmpeg_dir, resolve_proxy
from models.summary_schemas import TranscriptSegment
from services.bilibili_helper import DEFAULT_UA, apply_bilibili_patch, is_bilibili_url, warmup_bilibili_cookies
from services.douyin_helper import apply_douyin_opts, is_douyin_url, normalize_douyin_url
from services.youtube_helper import apply_youtube_opts, is_youtube_url, normalize_youtube_url

# 非文本字幕轨道，不能用于 AI 总结
_SKIP_SUBTITLE_LANGS = frozenset({"danmaku", "live_chat", "comments", "comment"})


def _parse_vtt_or_srt(content: str) -> list[TranscriptSegment]:
    segments: list[TranscriptSegment] = []
    blocks = re.split(r"\n\s*\n", content.strip())
    time_re = re.compile(
        r"(?P<start>\d{1,2}:\d{2}:\d{2}[.,]\d{3}|\d{1,2}:\d{2}[.,]\d{3})\s*-->\s*"
        r"(?P<end>\d{1,2}:\d{2}:\d{2}[.,]\d{3}|\d{1,2}:\d{2}[.,]\d{3})"
    )

    def _to_seconds(ts: str) -> float:
        ts = ts.replace(",", ".")
        parts = ts.split(":")
        if len(parts) == 3:
            h, m, s = parts
            return int(h) * 3600 + int(m) * 60 + float(s)
        m, s = parts
        return int(m) * 60 + float(s)

    for block in blocks:
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if len(lines) < 2:
            continue
        time_line = lines[1] if re.match(r"^\d+$", lines[0]) else lines[0]
        text_lines = lines[2:] if re.match(r"^\d+$", lines[0]) else lines[1:]
        m = time_re.search(time_line)
        if not m:
            continue
        text = " ".join(text_lines).strip()
        text = re.sub(r"<[^>]+>", "", text)
        if text:
            segments.append(
                TranscriptSegment(
                    start=_to_seconds(m.group("start")),
                    end=_to_seconds(m.group("end")),
                    text=text,
                )
            )
    return segments


def _filter_text_subtitles(subs: dict) -> dict:
    return {
        lang: formats
        for lang, formats in subs.items()
        if lang not in _SKIP_SUBTITLE_LANGS
    }


class SummaryYtdlpHelper:
    def __init__(self):
        apply_bilibili_patch()
        self._temp_cookies: list[str] = []

    def _cleanup_temp_cookies(self):
        for path in self._temp_cookies:
            try:
                os.unlink(path)
            except OSError:
                pass
        self._temp_cookies.clear()

    def _build_opts(self, url: str, **extra) -> dict:
        opts = {
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            **extra,
        }
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
        if is_douyin_url(url):
            apply_douyin_opts(opts, url, self._temp_cookies)
        if is_youtube_url(url):
            apply_youtube_opts(opts, normalize_youtube_url(url))
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

    def extract_basic_info(self, url: str) -> dict:
        url = self._prepare_url(url)
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
                if isinstance(first, dict):
                    info = first
        return info

    def fetch_subtitles_via_ytdlp(self, url: str) -> list[TranscriptSegment]:
        url = self._prepare_url(url)
        self._cleanup_temp_cookies()
        opts = self._build_opts(
            url,
            skip_download=True,
            writesubtitles=True,
            writeautomaticsub=True,
            subtitleslangs=["zh-Hans", "zh-CN", "zh", "ai-zh", "en"],
            subformat="vtt/best",
        )
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                subs = _filter_text_subtitles(info.get("subtitles") or {})
                auto = _filter_text_subtitles(info.get("automatic_captions") or {})
                merged = {**auto, **subs}
                if not merged:
                    raise RuntimeError("yt-dlp 未找到文本字幕")

                lang_order = ["zh-Hans", "zh-CN", "zh", "ai-zh", "en"]
                chosen_lang = None
                for lang in lang_order:
                    if lang in merged:
                        chosen_lang = lang
                        break
                if not chosen_lang:
                    chosen_lang = next(iter(merged))

                formats = merged[chosen_lang]
                vtt_fmt = next(
                    (f for f in formats if f.get("ext") in ("vtt", "srt")),
                    formats[0],
                )
                with tempfile.TemporaryDirectory() as tmp:
                    dl_opts = self._build_opts(
                        url,
                        skip_download=True,
                        writesubtitles=True,
                        writeautomaticsub=True,
                        subtitleslangs=[chosen_lang],
                        subformat=vtt_fmt.get("ext", "vtt"),
                        outtmpl=str(Path(tmp) / "%(id)s.%(ext)s"),
                    )
                    with yt_dlp.YoutubeDL(dl_opts) as ydl2:
                        ydl2.extract_info(url, download=True)
                    sub_files = list(Path(tmp).glob("*.*"))
                    if not sub_files:
                        raise RuntimeError("yt-dlp 字幕下载失败")
                    content = sub_files[0].read_text(encoding="utf-8", errors="ignore")
                    segments = _parse_vtt_or_srt(content)
                    if segments:
                        return segments
                    raise RuntimeError("yt-dlp 字幕解析为空")
        finally:
            self._cleanup_temp_cookies()

    def download_audio(self, url: str, output_dir: Path) -> Path:
        url = self._prepare_url(url)
        output_dir.mkdir(parents=True, exist_ok=True)
        outtmpl = str(output_dir / "audio.%(ext)s")
        self._cleanup_temp_cookies()
        opts = self._build_opts(
            url,
            format="bestaudio/best",
            outtmpl=outtmpl,
            postprocessors=[
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "128",
                }
            ],
        )
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.extract_info(url, download=True)
        finally:
            self._cleanup_temp_cookies()

        mp3_files = list(output_dir.glob("audio*.mp3"))
        if mp3_files:
            return mp3_files[0]
        audio_files = [
            p for p in output_dir.iterdir()
            if p.is_file() and p.suffix.lower() in (".mp3", ".m4a", ".wav", ".opus", ".webm")
        ]
        if not audio_files:
            raise RuntimeError("音频提取失败")
        return audio_files[0]
