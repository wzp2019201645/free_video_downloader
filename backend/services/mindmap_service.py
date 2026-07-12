"""Generate structured mind maps from completed summary tasks via DeepSeek."""

from __future__ import annotations

import json
import logging
import re

import httpx

from models.summary_extended_schemas import MindMapNode, MindMapResponse
from models.summary_schemas import SummaryResult
from summary_config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
)

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """你是一位专业的知识结构化助手。根据视频总结内容，生成思维导图 JSON。
输出格式：
{
  "root": {
    "label": "中心主题（视频核心主题，简短）",
    "children": [
      {
        "label": "一级分支",
        "children": [
          {"label": "二级要点", "children": []}
        ]
      }
    ]
  }
}
要求：
1. 一级分支 3-6 个，覆盖主要议题
2. 每个一级分支下 2-5 个二级要点
3. label 简洁，每条不超过 20 字
4. 只输出 JSON，不要 markdown 代码块"""


def _parse_json_content(raw: str) -> dict:
    content = raw.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    return json.loads(content)


def _to_node(data: dict) -> MindMapNode:
    return MindMapNode(
        label=str(data.get("label") or "未命名"),
        children=[_to_node(child) for child in data.get("children") or []],
    )


def _build_user_content(result: SummaryResult) -> str:
    lines = [
        f"视频标题：{result.title}",
        "",
        "整体摘要：",
        result.overview or "",
        "",
    ]
    if result.key_points:
        lines.append("核心要点：")
        lines.extend(f"- {point}" for point in result.key_points)
        lines.append("")
    if result.chapters:
        lines.append("章节大纲：")
        for chapter in result.chapters:
            lines.append(
                f"- [{chapter.start_seconds}s] {chapter.title}：{chapter.summary}"
            )
    return "\n".join(lines)


class MindMapService:
    def __init__(self):
        if not DEEPSEEK_API_KEY:
            raise RuntimeError("未配置 DEEPSEEK_API_KEY，请在 backend/.env 中设置")
        self._cache: dict[str, MindMapResponse] = {}

    def get_cached(self, task_id: str) -> MindMapResponse | None:
        return self._cache.get(task_id)

    async def generate(self, task_id: str, result: SummaryResult) -> MindMapResponse:
        cached = self._cache.get(task_id)
        if cached:
            return cached

        payload = {
            "model": DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_content(result)},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
            "max_tokens": 2048,
        }
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        }
        url = f"{DEEPSEEK_BASE_URL}/v1/chat/completions"

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code >= 400:
                logger.error("Mind map API error %s: %s", resp.status_code, resp.text[:500])
                resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"]
        parsed = _parse_json_content(content)
        root_data = parsed.get("root") or parsed
        response = MindMapResponse(root=_to_node(root_data))
        self._cache[task_id] = response
        return response
