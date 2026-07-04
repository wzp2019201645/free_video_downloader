"""Backend unit tests — no network required."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.schemas import TaskStatus
from services.task_manager import Task, TaskManager


def test_task_manager_response():
    mgr = TaskManager()
    task = Task(
        task_id="test123",
        url="https://example.com/video",
        format_id="best",
        status=TaskStatus.COMPLETED,
        progress=100.0,
        filename="test.mp4",
        filepath="/tmp/test.mp4",
    )
    mgr.tasks["test123"] = task
    resp = mgr.to_response(task)
    assert resp.task_id == "test123"
    assert resp.status == TaskStatus.COMPLETED
    assert resp.file_url == "/api/files/test123"
    print("[OK] task_manager response test passed")


def test_build_quality_formats():
    from services.ytdlp_service import _build_quality_formats

    info = {
        "formats": [
            {"height": 1080, "vcodec": "avc1", "acodec": "none", "ext": "mp4"},
            {"height": 720, "vcodec": "avc1", "acodec": "none", "ext": "mp4"},
            {"height": 480, "vcodec": "avc1", "acodec": "none", "ext": "mp4"},
            {"abr": 128, "vcodec": "none", "acodec": "mp4a", "ext": "m4a"},
        ]
    }
    formats = _build_quality_formats(info)
    assert len(formats) >= 4
    assert formats[0].quality == "最佳质量"
    assert any(f.quality == "1080p" for f in formats)
    assert any("音频" in f.quality for f in formats)
    print("[OK] quality formats test passed")


def test_health_import():
    from main import app
    assert app.title == "万能视频下载 API"
    print("[OK] main app import test passed")


if __name__ == "__main__":
    test_task_manager_response()
    test_build_quality_formats()
    test_health_import()
    print("\nAll unit tests passed!")
