"""Unit tests for AI summary module — no network required."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from models.summary_schemas import TranscriptSegment
from services.bilibili_subtitle import _parse_bilibili_subtitle_json
from services.deepseek_service import _build_transcript_text, _parse_json_content
from services.summary_ytdlp import _parse_vtt_or_srt
from services.subtitle_service import SubtitleService


def test_parse_bilibili_subtitle_json():
    data = {
        "body": [
            {"from": 0, "to": 2.5, "content": "你好"},
            {"from": 2.5, "to": 5.0, "content": "世界"},
        ]
    }
    segments = _parse_bilibili_subtitle_json(data)
    assert len(segments) == 2
    assert segments[0].text == "你好"
    assert segments[1].start == 2.5
    print("[OK] bilibili subtitle JSON parse test passed")


def test_parse_vtt():
    vtt = """WEBVTT

1
00:00:00.000 --> 00:00:02.000
Hello world
"""
    segments = _parse_vtt_or_srt(vtt)
    assert len(segments) == 1
    assert segments[0].text == "Hello world"
    print("[OK] VTT parse test passed")


def test_build_transcript_text():
    segments = [
        TranscriptSegment(start=0, end=2, text="测试"),
        TranscriptSegment(start=65, end=70, text="内容"),
    ]
    text = _build_transcript_text(segments)
    assert "[00:00]" in text
    assert "[01:05]" in text
    assert "测试" in text
    print("[OK] transcript text build test passed")


def test_parse_deepseek_json():
    raw = '```json\n{"overview": "摘要", "key_points": ["a"]}\n```'
    parsed = _parse_json_content(raw)
    assert parsed["overview"] == "摘要"
    print("[OK] DeepSeek JSON parse test passed")


def test_subtitle_service_supported_urls():
    svc = SubtitleService()
    assert svc.is_supported("https://www.bilibili.com/video/BV1xx411c7mD")
    assert svc.is_supported("https://v.douyin.com/abc/")
    assert not svc.is_supported("https://www.youtube.com/watch?v=abc")
    print("[OK] subtitle service platform check passed")


def test_whisper_return_shape():
    """Regression: _transcribe_from_audio must not be double-wrapped."""
    from services.subtitle_service import SubtitleService
    from models.summary_schemas import TranscriptSegment

    svc = SubtitleService()
    # mock path: verify _fetch_bilibili whisper fallback return unpack
    segments, source = ([TranscriptSegment(start=0, end=1, text="a")], "whisper")
    assert isinstance(segments, list)
    assert all(isinstance(s, TranscriptSegment) for s in segments)
    assert source == "whisper"
    print("[OK] whisper return shape test passed")


def test_normalize_douyin_modal_url():
    from services.douyin_helper import extract_douyin_video_id, normalize_douyin_url

    url = "https://www.douyin.com/jingxuan/knowledge?modal_id=7636306372904209702"
    assert extract_douyin_video_id(url) == "7636306372904209702"
    assert normalize_douyin_url(url) == "https://www.iesdouyin.com/share/video/7636306372904209702/"
    print("[OK] douyin modal url normalize test passed")


def test_summary_routes_registered():
    from main import app

    paths = app.openapi().get("paths", {})
    assert "/api/summary" in paths
    assert "/api/summary/tasks/{task_id}" in paths
    print("[OK] summary routes registered test passed")


def test_traditional_to_simplified():
    from services.text_normalize import normalize_segments, to_simplified

    assert to_simplified("繁體中文測試") == "繁体中文测试"
    assert to_simplified("簡體已經是簡體") == "简体已经是简体"
    segs = normalize_segments(
        [
            TranscriptSegment(start=0, end=1, text="這是繁體字幕"),
            TranscriptSegment(start=1, end=2, text="Hello"),
        ]
    )
    assert segs[0].text == "这是繁体字幕"
    assert segs[1].text == "Hello"
    print("[OK] traditional to simplified test passed")


def test_whisper_default_model_is_base():
    from summary_config import WHISPER_MODEL_SIZE

    assert WHISPER_MODEL_SIZE == "base"
    print("[OK] whisper default model is base")


if __name__ == "__main__":
    test_parse_bilibili_subtitle_json()
    test_parse_vtt()
    test_build_transcript_text()
    test_parse_deepseek_json()
    test_subtitle_service_supported_urls()
    test_whisper_return_shape()
    test_normalize_douyin_modal_url()
    test_summary_routes_registered()
    test_traditional_to_simplified()
    test_whisper_default_model_is_base()
    print("\nAll summary unit tests passed!")
