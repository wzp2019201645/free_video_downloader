"""Register account and Stripe routes without changing the download core."""

from __future__ import annotations

from fastapi import FastAPI

from routes.auth_router import auth_router
from routes.billing_router import billing_router


def register_billing_routes(app: FastAPI) -> None:
    app.include_router(auth_router)
    app.include_router(billing_router)
