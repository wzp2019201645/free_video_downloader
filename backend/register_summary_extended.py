"""Register extended summary routes (mind map + AI Q&A)."""

from __future__ import annotations

from fastapi import FastAPI

from routes.summary_extended_router import summary_extended_router


def register_summary_extended_routes(app: FastAPI) -> None:
    app.include_router(summary_extended_router)
