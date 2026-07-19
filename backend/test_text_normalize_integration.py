"""Integration-style tests for subtitle simplification path."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from models.summary_schemas import TranscriptSegment
from services.subtitle_service import SubtitleService


def test_fetch_converts_traditional_chinese():
    svc = SubtitleService()
    traditional_segments = [
        TranscriptSegment(start=0.0, end=1.0, text="這是繁體字幕內容"),
        TranscriptSegment(start=1.0, end=2.0, text="視頻下載測試"),
    ]

    with (
        patch.object(svc, "is_supported", return_value=True),
        patch.object(
            svc._ytdlp,
            "extract_basic_info",
            return_value={"title": "測試視頻", "duration": 10},
        ),
        patch(
            "services.subtitle_service.is_bilibili_url",
            return_value=True,
        ),
        patch(
            "services.subtitle_service.fetch_bilibili_subtitles",
            return_value=traditional_segments,
        ),
    ):
        result = svc.fetch("https://www.bilibili.com/video/BV1xx411c7mD")

    assert result.segments[0].text == "这是繁体字幕内容"
    assert result.segments[1].text == "视频下载测试"
    assert result.source == "bilibili_api"
    print("[OK] fetch converts traditional Chinese")


if __name__ == "__main__":
    test_fetch_converts_traditional_chinese()
    print("\nAll text normalize integration tests passed!")
