from enum import Enum
from typing import Optional

from pydantic import BaseModel, HttpUrl


class TaskStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"


class InfoRequest(BaseModel):
    url: str


class FormatInfo(BaseModel):
    format_id: str
    quality: str
    ext: str
    filesize: Optional[int] = None
    vcodec: Optional[str] = None
    acodec: Optional[str] = None
    fps: Optional[float] = None
    tbr: Optional[float] = None


class VideoInfoResponse(BaseModel):
    title: str
    thumbnail: Optional[str] = None
    duration: Optional[int] = None
    uploader: Optional[str] = None
    webpage_url: Optional[str] = None
    formats: list[FormatInfo]


class DownloadRequest(BaseModel):
    url: str
    format_id: str


class DownloadResponse(BaseModel):
    task_id: str


class TaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    progress: float = 0.0
    filename: Optional[str] = None
    file_url: Optional[str] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    active_tasks: int
    max_concurrent: int
