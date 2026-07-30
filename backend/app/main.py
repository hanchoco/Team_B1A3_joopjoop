"""joopjoop FastAPI application."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import app.models  # noqa: F401 - registers all ORM tables on Base.metadata.
from app.api.v1 import chatbot, checklist, notification, policies, simulator, users
from app.core.config import settings
from app.core.database import Base, engine
from app.crud.categories import ensure_default_categories
from app.db.session import SessionLocal
from app.services.errors import ServiceError


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Optionally bootstrap tables for local/hackathon deployments."""

    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            ensure_default_categories(db)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.auth_router, prefix=settings.api_v1_prefix)
app.include_router(users.router, prefix=settings.api_v1_prefix)
app.include_router(policies.router, prefix=settings.api_v1_prefix)
app.include_router(simulator.router, prefix=settings.api_v1_prefix)
app.include_router(chatbot.router, prefix=settings.api_v1_prefix)
app.include_router(checklist.router, prefix=settings.api_v1_prefix)
app.include_router(notification.router, prefix=settings.api_v1_prefix)


@app.exception_handler(ServiceError)
async def handle_service_error(
    _request: Request,
    exc: ServiceError,
) -> JSONResponse:
    """Translate expected domain errors into one stable JSON envelope."""

    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "detail": exc.detail},
    )


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Container health endpoint."""

    return {"status": "ok"}
