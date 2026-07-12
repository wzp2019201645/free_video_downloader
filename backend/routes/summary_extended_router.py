"""FastAPI routes for mind map and AI Q&A extensions."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from models.summary_extended_schemas import (
    MindMapRequest,
    MindMapResponse,
    SummaryChatRequest,
    SummaryChatResponse,
)
from models.summary_schemas import SummaryStatus
from routes.summary_router import _get_manager
from services.mindmap_service import MindMapService
from services.summary_chat_service import SummaryChatService

summary_extended_router = APIRouter(prefix="/api/summary", tags=["summary-extended"])

_mindmap: MindMapService | None = None
_chat: SummaryChatService | None = None


def _get_mindmap_service() -> MindMapService:
    global _mindmap
    if _mindmap is None:
        _mindmap = MindMapService()
    return _mindmap


def _get_chat_service() -> SummaryChatService:
    global _chat
    if _chat is None:
        _chat = SummaryChatService()
    return _chat


def _require_completed_task(task_id: str):
    task = _get_manager().get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="总结任务不存在")
    if task.status != SummaryStatus.COMPLETED or not task.result:
        raise HTTPException(status_code=400, detail="请等待视频总结完成后再使用此功能")
    return task


@summary_extended_router.post("/mindmap", response_model=MindMapResponse)
async def create_mindmap(req: MindMapRequest):
    task = _require_completed_task(req.task_id.strip())
    try:
        return await _get_mindmap_service().generate(req.task_id, task.result)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"思维导图生成失败: {e}")


@summary_extended_router.post("/chat", response_model=SummaryChatResponse)
async def summary_chat(req: SummaryChatRequest):
    message = req.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="请输入问题")
    task = _require_completed_task(req.task_id.strip())
    try:
        return await _get_chat_service().chat(task.result, message, req.history)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 问答失败: {e}")
