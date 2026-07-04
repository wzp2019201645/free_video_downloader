import asyncio
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from config import DOWNLOAD_DIR, FILE_TTL_SECONDS, MAX_CONCURRENT
from models.schemas import TaskResponse, TaskStatus
from services.ytdlp_service import YtdlpService


@dataclass
class Task:
    task_id: str
    url: str
    format_id: str
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    filename: Optional[str] = None
    filepath: Optional[str] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None


class TaskManager:
    def __init__(self):
        self.tasks: dict[str, Task] = {}
        self._active_count = 0
        self._lock = asyncio.Lock()
        self.ytdlp = YtdlpService()
        self._cleanup_task: Optional[asyncio.Task] = None

    def start_cleanup_loop(self):
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def _cleanup_loop(self):
        while True:
            await asyncio.sleep(600)
            await self.cleanup_expired()

    async def cleanup_expired(self):
        now = time.time()
        expired = [
            tid
            for tid, task in self.tasks.items()
            if task.completed_at and (now - task.completed_at) > FILE_TTL_SECONDS
        ]
        for tid in expired:
            task = self.tasks.pop(tid, None)
            if task and task.filepath:
                try:
                    Path(task.filepath).unlink(missing_ok=True)
                except OSError:
                    pass

    async def create_task(self, url: str, format_id: str) -> str:
        async with self._lock:
            if self._active_count >= MAX_CONCURRENT:
                raise RuntimeError(
                    f"当前下载任务已满（最多 {MAX_CONCURRENT} 个），请稍后再试"
                )

        task_id = uuid.uuid4().hex[:12]
        task = Task(task_id=task_id, url=url, format_id=format_id)
        self.tasks[task_id] = task
        asyncio.create_task(self._run_download(task))
        return task_id

    async def _run_download(self, task: Task):
        async with self._lock:
            self._active_count += 1
        task.status = TaskStatus.DOWNLOADING

        def on_progress(pct: float):
            task.progress = round(pct, 1)

        try:
            task_dir = DOWNLOAD_DIR / task.task_id
            task_dir.mkdir(parents=True, exist_ok=True)

            filename, filepath = await self.ytdlp.download(
                task.url, task.format_id, task_dir, on_progress
            )
            task.filename = filename
            task.filepath = filepath
            task.status = TaskStatus.COMPLETED
            task.progress = 100.0
            task.completed_at = time.time()
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = time.time()
        finally:
            async with self._lock:
                self._active_count -= 1

    def get_task(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)

    def to_response(self, task: Task) -> TaskResponse:
        file_url = None
        if task.status == TaskStatus.COMPLETED and task.filepath:
            file_url = f"/api/files/{task.task_id}"

        return TaskResponse(
            task_id=task.task_id,
            status=task.status,
            progress=task.progress,
            filename=task.filename,
            file_url=file_url,
            error=task.error,
        )

    @property
    def active_count(self) -> int:
        return self._active_count
