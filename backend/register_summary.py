"""Register AI summary routes on the main FastAPI app (additive wiring only)."""

from __future__ import annotations

from fastapi import FastAPI

from routes.summary_router import summary_router


def register_summary_routes(app: FastAPI) -> None:
    app.include_router(summary_router)
