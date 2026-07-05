"""Progress callback type for summary pipeline."""

from __future__ import annotations

from typing import Callable, Optional

ProgressCallback = Optional[Callable[[float, str], None]]


def report_progress(callback: ProgressCallback, progress: float, detail: str) -> None:
    if callback:
        callback(progress, detail)
