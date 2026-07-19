"""Orchestrate subtitle acquisition: platform API → yt-dlp → ASR."""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from models.summary_schemas import TranscriptSegment
from services.asr_service import transcribe_audio
from services.bilibili_helper import is_bilibili_url
from services.bilibili_subtitle import fetch_bilibili_subtitles
from services.douyin_helper import is_douyin_url
from services.summary_progress import ProgressCallback, report_progress
from services.summary_ytdlp import SummaryYtdlpHelper
from services.text_normalize import normalize_segments
from summary_config import SUMMARY_DIR

logger = logging.getLogger(__name__)


@dataclass
class SubtitleFetchResult:
    segments: list[TranscriptSegment]
    source: str
    title: str
    duration: int | None


class SubtitleService:
    def __init__(self):
        self._ytdlp = SummaryYtdlpHelper()

    def is_supported(self, url: str) -> bool:
        return is_bilibili_url(url) or is_douyin_url(url)

    def fetch(
        self,
        url: str,
        work_dir: Path | None = None,
        on_progress: ProgressCallback = None,
    ) -> SubtitleFetchResult:
        if not self.is_supported(url):
            raise ValueError("仅支持 B 站和抖音链接")

        report_progress(on_progress, 8.0, "正在解析视频信息…")
        info = self._ytdlp.extract_basic_info(url)
        title = info.get("title") or "未知标题"
        duration = int(info["duration"]) if info.get("duration") else None

        work = work_dir or (SUMMARY_DIR / "work")
        work.mkdir(parents=True, exist_ok=True)

        if is_bilibili_url(url):
            segments, source = self._fetch_bilibili(url, work, on_progress)
        else:
            segments, source = self._fetch_douyin(url, work, on_progress)

        if not segments:
            raise RuntimeError("未能获取任何字幕或转录文本")
        segments = normalize_segments(segments)
        report_progress(on_progress, 50.0, "字幕/转录获取完成")
        return SubtitleFetchResult(
            segments=segments,
            source=source,
            title=title,
            duration=duration,
        )

    def _fetch_bilibili(
        self, url: str, work: Path, on_progress: ProgressCallback
    ) -> tuple[list[TranscriptSegment], str]:
        report_progress(on_progress, 12.0, "正在获取 B 站字幕…")
        try:
            return fetch_bilibili_subtitles(url), "bilibili_api"
        except Exception as exc:
            logger.warning("Bilibili API subtitle failed: %s", exc)
        report_progress(on_progress, 18.0, "正在通过 yt-dlp 获取字幕…")
        try:
            return self._ytdlp.fetch_subtitles_via_ytdlp(url), "ytdlp"
        except Exception as exc:
            logger.warning("yt-dlp subtitle failed: %s", exc)
        return self._transcribe_from_audio(url, work, on_progress)

    def _fetch_douyin(
        self, url: str, work: Path, on_progress: ProgressCallback
    ) -> tuple[list[TranscriptSegment], str]:
        # 抖音精选/分享页链接 yt-dlp 不支持，统一走 DouyinParser + Whisper
        return self._transcribe_from_audio(url, work, on_progress)

    def _transcribe_from_audio(
        self,
        url: str,
        work: Path | None = None,
        on_progress: ProgressCallback = None,
    ) -> tuple[list[TranscriptSegment], str]:
        work = work or (SUMMARY_DIR / "work")
        audio_dir = work / "audio"
        if audio_dir.exists():
            shutil.rmtree(audio_dir, ignore_errors=True)
        audio_dir.mkdir(parents=True, exist_ok=True)
        report_progress(on_progress, 22.0, "视频无字幕，正在下载音频…")
        audio_path = self._ytdlp.download_audio(url, audio_dir)
        report_progress(on_progress, 35.0, "正在加载语音识别模型…")
        segments = transcribe_audio(audio_path, on_progress=on_progress)
        report_progress(on_progress, 48.0, "语音识别完成")
        return segments, "whisper"
