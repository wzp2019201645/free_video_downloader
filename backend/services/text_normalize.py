"""Normalize transcript text (Traditional → Simplified Chinese)."""

from __future__ import annotations

from functools import lru_cache

from models.summary_schemas import TranscriptSegment


@lru_cache(maxsize=1)
def _t2s_converter():
    from opencc import OpenCC

    return OpenCC("t2s")


def to_simplified(text: str) -> str:
    if not text:
        return text
    return _t2s_converter().convert(text)


def normalize_segments(segments: list[TranscriptSegment]) -> list[TranscriptSegment]:
    return [
        TranscriptSegment(
            start=seg.start,
            end=seg.end,
            text=to_simplified(seg.text),
        )
        for seg in segments
    ]
