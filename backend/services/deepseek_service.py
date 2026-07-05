"""DeepSeek Chat API for structured video summarization."""

from __future__ import annotations

import json
import logging
import re

import httpx

from models.summary_schemas import (
    SummaryChapter,
    SummaryResult,
    TranscriptSegment,
)
from summary_config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    SUMMARY_MAX_TRANSCRIPT_CHARS,
)

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """你是一位专业的视频内容分析助手。用户会提供视频标题和带时间戳的字幕/转录文本。
请用中文输出 JSON，结构如下：
{
  "overview": "200字以内的整体摘要",
  "key_points": ["核心要点1", "核心要点2"],
  "chapters": [
    {"title": "章节标题", "start_seconds": 0, "summary": "该章节内容摘要"}
  ],
  "tags": ["#标签1", "#标签2"]
}
要求：
1. key_points 3-8 条，简洁有力
2. chapters 按时间顺序，覆盖主要段落，start_seconds 为整数秒
3. tags 2-5 个
4. 只输出 JSON，不要 markdown 代码块"""


def _format_timestamp(seconds: float) -> str:
    total = int(seconds)
    m, s = divmod(total, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _build_transcript_text(segments: list[TranscriptSegment]) -> str:
    lines = [
        f"[{_format_timestamp(seg.start)}] {seg.text}"
        for seg in segments
    ]
    text = "\n".join(lines)
    if len(text) > SUMMARY_MAX_TRANSCRIPT_CHARS:
        text = text[:SUMMARY_MAX_TRANSCRIPT_CHARS] + "\n...(内容过长，已截断)"
    return text


def _parse_json_content(raw: str) -> dict:
    content = raw.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    return json.loads(content)


class DeepSeekService:
    def __init__(self):
        if not DEEPSEEK_API_KEY:
            raise RuntimeError("未配置 DEEPSEEK_API_KEY，请在 backend/.env 中设置")

    async def summarize(
        self,
        title: str,
        duration: int | None,
        subtitle_source: str,
        segments: list[TranscriptSegment],
    ) -> SummaryResult:
        transcript_text = _build_transcript_text(segments)
        user_content = (
            f"视频标题：{title}\n"
            f"视频时长：{duration or '未知'} 秒\n\n"
            f"字幕/转录内容：\n{transcript_text}"
        )

        payload = {
            "model": DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.3,
            "max_tokens": 4096,
        }
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        }
        url = f"{DEEPSEEK_BASE_URL}/v1/chat/completions"

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code >= 400:
                logger.error("DeepSeek API error %s: %s", resp.status_code, resp.text[:500])
                resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"]
        parsed = _parse_json_content(content)

        chapters = [
            SummaryChapter(
                title=c.get("title", ""),
                start_seconds=int(c.get("start_seconds", 0)),
                summary=c.get("summary", ""),
            )
            for c in parsed.get("chapters") or []
        ]

        return SummaryResult(
            title=title,
            duration=duration,
            subtitle_source=subtitle_source,
            overview=parsed.get("overview", ""),
            key_points=list(parsed.get("key_points") or []),
            chapters=chapters,
            tags=list(parsed.get("tags") or []),
            transcript=segments,
        )
