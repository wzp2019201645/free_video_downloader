from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SummaryStatus(str, Enum):
    PENDING = "pending"
    EXTRACTING_SUBTITLE = "extracting_subtitle"
    SUMMARIZING = "summarizing"
    COMPLETED = "completed"
    FAILED = "failed"


class SummaryRequest(BaseModel):
    url: str


class SummaryCreateResponse(BaseModel):
    task_id: str


class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str


class SummaryChapter(BaseModel):
    title: str
    start_seconds: int
    summary: str


class SummaryResult(BaseModel):
    title: str
    duration: Optional[int] = None
    subtitle_source: str
    overview: str
    key_points: list[str] = Field(default_factory=list)
    chapters: list[SummaryChapter] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    transcript: list[TranscriptSegment] = Field(default_factory=list)


class SummaryTaskResponse(BaseModel):
    task_id: str
    status: SummaryStatus
    progress: float = 0.0
    status_detail: Optional[str] = None
    error: Optional[str] = None
    result: Optional[SummaryResult] = None
