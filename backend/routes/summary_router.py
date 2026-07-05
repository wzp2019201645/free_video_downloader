"""FastAPI routes for AI video summary."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from models.summary_schemas import (
    SummaryCreateResponse,
    SummaryRequest,
    SummaryTaskResponse,
)
from services.summary_manager import SummaryManager

summary_router = APIRouter(prefix="/api/summary", tags=["summary"])

_manager: SummaryManager | None = None


def _get_manager() -> SummaryManager:
    global _manager
    if _manager is None:
        _manager = SummaryManager()
    return _manager


@summary_router.post("", response_model=SummaryCreateResponse)
async def create_summary(req: SummaryRequest):
    try:
        task_id = await _get_manager().create_task(req.url.strip())
        return SummaryCreateResponse(task_id=task_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@summary_router.get("/tasks/{task_id}", response_model=SummaryTaskResponse)
async def get_summary_task(task_id: str):
    task = _get_manager().get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="总结任务不存在")
    return _get_manager().to_response(task)
