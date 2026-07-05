"""In-memory task manager for AI video summary."""

from __future__ import annotations

import asyncio
import logging
import shutil
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from models.summary_schemas import (
    SummaryResult,
    SummaryStatus,
    SummaryTaskResponse,
)
from services.deepseek_service import DeepSeekService
from services.subtitle_service import SubtitleService
from services.summary_executor import run_in_summary_executor
from summary_config import (
    SUMMARY_DIR,
    SUMMARY_MAX_CONCURRENT,
    SUMMARY_MAX_DURATION_SECONDS,
)

logger = logging.getLogger(__name__)


@dataclass
class SummaryTask:
    task_id: str
    url: str
    status: SummaryStatus = SummaryStatus.PENDING
    progress: float = 0.0
    status_detail: str = ""
    error: str | None = None
    result: SummaryResult | None = None
    work_dir: Path | None = None


class SummaryManager:
    def __init__(self):
        self.tasks: dict[str, SummaryTask] = {}
        self._semaphore = asyncio.Semaphore(SUMMARY_MAX_CONCURRENT)
        self._subtitle = SubtitleService()
        self._deepseek: DeepSeekService | None = None

    def _get_deepseek(self) -> DeepSeekService:
        if self._deepseek is None:
            self._deepseek = DeepSeekService()
        return self._deepseek

    @property
    def active_count(self) -> int:
        return sum(
            1
            for t in self.tasks.values()
            if t.status not in (SummaryStatus.COMPLETED, SummaryStatus.FAILED)
        )

    async def create_task(self, url: str) -> str:
        if not self._subtitle.is_supported(url):
            raise ValueError("仅支持 B 站和抖音链接")

        task_id = f"sum_{uuid.uuid4().hex[:12]}"
        work_dir = SUMMARY_DIR / task_id
        work_dir.mkdir(parents=True, exist_ok=True)
        task = SummaryTask(task_id=task_id, url=url, work_dir=work_dir)
        self.tasks[task_id] = task
        asyncio.create_task(self._run_task(task_id))
        return task_id

    def get_task(self, task_id: str) -> SummaryTask | None:
        return self.tasks.get(task_id)

    def to_response(self, task: SummaryTask) -> SummaryTaskResponse:
        return SummaryTaskResponse(
            task_id=task.task_id,
            status=task.status,
            progress=task.progress,
            status_detail=task.status_detail or None,
            error=task.error,
            result=task.result,
        )

    async def _run_task(self, task_id: str) -> None:
        task = self.tasks.get(task_id)
        if not task:
            return

        async with self._semaphore:
            try:
                task.status = SummaryStatus.EXTRACTING_SUBTITLE
                task.progress = 5.0
                task.status_detail = "开始获取字幕…"

                def _on_progress(progress: float, detail: str) -> None:
                    task.progress = progress
                    task.status_detail = detail

                def _fetch_subtitles():
                    return self._subtitle.fetch(
                        task.url, task.work_dir, on_progress=_on_progress
                    )

                sub_result = await run_in_summary_executor(_fetch_subtitles)
                task.progress = 55.0
                task.status_detail = "字幕准备完成，即将开始 AI 总结…"

                if (
                    sub_result.duration
                    and sub_result.duration > SUMMARY_MAX_DURATION_SECONDS
                ):
                    raise RuntimeError(
                        f"视频时长超过 {SUMMARY_MAX_DURATION_SECONDS // 60} 分钟上限，暂不支持总结"
                    )

                task.status = SummaryStatus.SUMMARIZING
                task.progress = 65.0
                task.status_detail = "DeepSeek 正在分析视频内容…"

                result = await self._get_deepseek().summarize(
                    title=sub_result.title,
                    duration=sub_result.duration,
                    subtitle_source=sub_result.source,
                    segments=sub_result.segments,
                )
                task.result = result
                task.status = SummaryStatus.COMPLETED
                task.progress = 100.0
                task.status_detail = "总结完成"
            except Exception as exc:
                logger.exception("Summary task %s failed", task_id)
                task.status = SummaryStatus.FAILED
                task.error = str(exc) or "总结失败"
                task.status_detail = task.error
            finally:
                if task.work_dir and task.work_dir.exists():
                    shutil.rmtree(task.work_dir, ignore_errors=True)
                    task.work_dir = None
