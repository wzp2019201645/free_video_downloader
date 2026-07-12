"""AI Q&A over completed summary task context via DeepSeek."""

from __future__ import annotations

import logging

import httpx

from models.summary_extended_schemas import ChatMessage, SummaryChatResponse
from models.summary_schemas import SummaryResult
from services.deepseek_service import _build_transcript_text
from summary_config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """你是一位专业的视频内容问答助手。
用户已完成某视频的 AI 总结，你会收到视频标题、摘要、要点、章节和字幕/转录文本。
请基于这些内容用中文准确回答用户问题。
要求：
1. 只依据提供的视频内容回答，不要编造
2. 若内容中没有相关信息，明确说明「视频中未提及」
3. 回答简洁清晰，必要时引用时间点
4. 保持对话连贯，可参考历史消息"""


def _build_context_block(result: SummaryResult) -> str:
    lines = [
        f"视频标题：{result.title}",
        f"视频时长：{result.duration or '未知'} 秒",
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
        lines.append("")
    if result.transcript:
        transcript = _build_transcript_text(result.transcript)
        lines.append("字幕/转录：")
        lines.append(transcript)
    return "\n".join(lines)


class SummaryChatService:
    def __init__(self):
        if not DEEPSEEK_API_KEY:
            raise RuntimeError("未配置 DEEPSEEK_API_KEY，请在 backend/.env 中设置")

    async def chat(
        self,
        result: SummaryResult,
        message: str,
        history: list[ChatMessage],
    ) -> SummaryChatResponse:
        context = _build_context_block(result)
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"以下是视频内容上下文：\n\n{context}"},
            {"role": "assistant", "content": "我已理解视频内容，请提问。"},
        ]
        for item in history[-10:]:
            if item.role in ("user", "assistant") and item.content.strip():
                messages.append({"role": item.role, "content": item.content})
        messages.append({"role": "user", "content": message.strip()})

        payload = {
            "model": DEEPSEEK_MODEL,
            "messages": messages,
            "temperature": 0.4,
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
                logger.error("Summary chat API error %s: %s", resp.status_code, resp.text[:500])
                resp.raise_for_status()
            data = resp.json()

        reply = data["choices"][0]["message"]["content"].strip()
        return SummaryChatResponse(reply=reply)
