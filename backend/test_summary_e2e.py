"""End-to-end test for AI summary with a real Bilibili URL (requires network + DEEPSEEK_API_KEY)."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient

from main import app

TEST_URL = "https://www.bilibili.com/video/BV1yyMM69Em2"
POLL_INTERVAL = 2
MAX_WAIT = 600


def test_summary_e2e_bilibili():
    client = TestClient(app)
    resp = client.post("/api/summary", json={"url": TEST_URL})
    assert resp.status_code == 200, resp.text
    task_id = resp.json()["task_id"]
    print(f"[INFO] task_id={task_id}")

    deadline = time.time() + MAX_WAIT
    last_progress = -1
    while time.time() < deadline:
        task = client.get(f"/api/summary/tasks/{task_id}").json()
        status = task["status"]
        progress = task.get("progress", 0)
        detail = task.get("status_detail") or ""
        if progress != last_progress or detail:
            print(f"[INFO] status={status} progress={progress:.0f}% detail={detail}")
            last_progress = progress
        if status == "completed":
            result = task["result"]
            assert result["overview"]
            assert result["key_points"]
            assert result["transcript"]
            print(f"[OK] summary completed: {result['title'][:40]}")
            print(f"[OK] source={result['subtitle_source']} segments={len(result['transcript'])}")
            return
        if status == "failed":
            raise AssertionError(f"Summary failed: {task.get('error')}")
        time.sleep(POLL_INTERVAL)

    raise AssertionError(f"Summary timed out after {MAX_WAIT}s")


if __name__ == "__main__":
    test_summary_e2e_bilibili()
    print("\nE2E summary test passed!")
