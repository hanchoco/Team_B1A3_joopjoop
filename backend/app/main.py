"""joopjoop FastAPI application."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import app.models  # noqa: F401 - registers all ORM tables on Base.metadata.
from app.api.v1 import chatbot, checklist, notification, policies, simulator, users
from app.core.config import settings
from app.core.database import Base, engine
from app.crud.categories import ensure_default_categories, ensure_default_category_questions
from app.db.session import SessionLocal
from app.services.errors import ServiceError
from app.services.notification_service import run_scheduled_deadline_notification_job
from app.services.policy_seed_loader import ensure_seeded_policies

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Optionally bootstrap tables for local/hackathon deployments."""

    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            ensure_default_categories(db)
            ensure_default_category_questions(db)
            ensure_seeded_policies(db)
    scheduler.add_job(
        run_scheduled_deadline_notification_job,
        trigger="cron",
        minute=0,
        id="deadline_notifications",
        replace_existing=True,
    )
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
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
