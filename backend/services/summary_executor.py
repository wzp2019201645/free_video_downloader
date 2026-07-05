"""Dedicated thread pool for AI summary — avoids blocking core download/info parsing."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, TypeVar

from summary_config import SUMMARY_MAX_CONCURRENT

T = TypeVar("T")

# 与 SUMMARY_MAX_CONCURRENT 对齐，独立于 asyncio 默认线程池
SUMMARY_EXECUTOR = ThreadPoolExecutor(
    max_workers=max(SUMMARY_MAX_CONCURRENT, 1),
    thread_name_prefix="summary-worker",
)


async def run_in_summary_executor(func: Callable[[], T]) -> T:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(SUMMARY_EXECUTOR, func)
