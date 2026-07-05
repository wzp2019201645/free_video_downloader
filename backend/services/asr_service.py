"""Local ASR via faster-whisper (fallback when no subtitles available)."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from models.summary_schemas import TranscriptSegment
from services.summary_progress import ProgressCallback, report_progress
from summary_config import WHISPER_COMPUTE_TYPE, WHISPER_DEVICE, WHISPER_MODEL_SIZE

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def _get_model():
    from faster_whisper import WhisperModel

    logger.info(
        "Loading Whisper model size=%s device=%s compute=%s",
        WHISPER_MODEL_SIZE,
        WHISPER_DEVICE,
        WHISPER_COMPUTE_TYPE,
    )
    return WhisperModel(
        WHISPER_MODEL_SIZE,
        device=WHISPER_DEVICE,
        compute_type=WHISPER_COMPUTE_TYPE,
    )


def transcribe_audio(
    audio_path: Path,
    on_progress: ProgressCallback = None,
) -> list[TranscriptSegment]:
    report_progress(on_progress, 38.0, "正在加载语音识别模型…")
    model = _get_model()
    report_progress(on_progress, 42.0, "正在转写音频内容…")
    segments_iter, info = model.transcribe(
        str(audio_path),
        beam_size=5,
        language="zh",
        vad_filter=True,
    )
    logger.info(
        "Whisper detected language=%s prob=%.2f duration=%.1fs",
        info.language,
        info.language_probability,
        info.duration,
    )
    segments: list[TranscriptSegment] = []
    for seg in segments_iter:
        text = (seg.text or "").strip()
        if text:
            segments.append(
                TranscriptSegment(start=float(seg.start), end=float(seg.end), text=text)
            )
    if not segments:
        raise RuntimeError("语音识别未产生任何文本")
    return segments
