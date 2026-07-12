"""Unit tests for summary extended features."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from models.summary_extended_schemas import MindMapNode
from services.mindmap_service import _parse_json_content, _to_node


def test_parse_mindmap_json():
    raw = '```json\n{"root": {"label": "主题", "children": [{"label": "分支"}]}}\n```'
    parsed = _parse_json_content(raw)
    node = _to_node(parsed["root"])
    assert node.label == "主题"
    assert node.children[0].label == "分支"
    print("[OK] mindmap json parse test passed")


def test_extended_routes_registered():
    from main import app

    paths = app.openapi().get("paths", {})
    assert "/api/summary/mindmap" in paths
    assert "/api/summary/chat" in paths
    print("[OK] extended summary routes registered test passed")


if __name__ == "__main__":
    test_parse_mindmap_json()
    test_extended_routes_registered()
    print("\nAll summary extended unit tests passed!")
