"""Integration tests: video parse must stay responsive during summary work."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import httpx
from fastapi.testclient import TestClient

from main import app

PARSE_URL = "https://www.bilibili.com/video/BV1h5QaY5EaH"
SUMMARY_URL = "https://www.bilibili.com/video/BV1yyMM69Em2"


def test_parse_bilibili_responds_quickly():
    client = TestClient(app)
    t0 = time.time()
    resp = client.post("/api/info", json={"url": PARSE_URL})
    elapsed = time.time() - t0
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["title"]
    assert data["formats"]
    assert elapsed < 30, f"parse took too long: {elapsed:.1f}s"
    print(f"[OK] parse in {elapsed:.1f}s title={data['title'][:40]}")


def test_parse_while_summary_running():
    """Core parse must not hang when a summary task is in progress."""
    client = TestClient(app)
    sum_resp = client.post("/api/summary", json={"url": SUMMARY_URL})
    assert sum_resp.status_code == 200
    task_id = sum_resp.json()["task_id"]

    t0 = time.time()
    parse_resp = client.post("/api/info", json={"url": PARSE_URL})
    elapsed = time.time() - t0
    assert parse_resp.status_code == 200, parse_resp.text
    assert elapsed < 30, f"parse blocked by summary for {elapsed:.1f}s"
    print(f"[OK] parse while summary running: {elapsed:.1f}s")

    task = client.get(f"/api/summary/tasks/{task_id}").json()
    print(f"[INFO] summary status={task['status']} progress={task.get('progress')}")


if __name__ == "__main__":
    test_parse_bilibili_responds_quickly()
    test_parse_while_summary_running()
    print("\nIntegration tests passed!")
