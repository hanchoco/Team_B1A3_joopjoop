"""SQLAlchemy 2.x synchronous database foundation."""

from __future__ import annotations

from typing import Any

from sqlalchemy import MetaData, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool

from app.core.config import settings

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base class shared by every ORM model."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def _engine_options(database_url: str) -> dict[str, Any]:
    """Return backend-specific options without changing model semantics."""

    options: dict[str, Any] = {
        "pool_pre_ping": True,
    }
    if database_url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
        if database_url in {"sqlite://", "sqlite:///:memory:"}:
            options["poolclass"] = StaticPool
    return options


engine = create_engine(settings.database_url, **_engine_options(settings.database_url))


if engine.dialect.name == "sqlite":

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(
        dbapi_connection: Any,
        _connection_record: Any,
    ) -> None:
        """Make SQLite enforce the same foreign-key intent as MySQL."""

        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()


__all__ = ["Base", "Engine", "engine"]
