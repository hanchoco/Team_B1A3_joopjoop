"""Shared SQLAlchemy column types and model mixins."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TypeVar

from sqlalchemy import (
    BigInteger,
    DateTime,
    Integer,
    SmallInteger,
    Text,
    func,
)
from sqlalchemy import (
    Enum as SqlEnum,
)
from sqlalchemy.dialects.mysql import (
    BIGINT as MYSQL_BIGINT,
)
from sqlalchemy.dialects.mysql import (
    DATETIME as MYSQL_DATETIME,
)
from sqlalchemy.dialects.mysql import (
    LONGTEXT as MYSQL_LONGTEXT,
)
from sqlalchemy.dialects.mysql import (
    SMALLINT as MYSQL_SMALLINT,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.type_api import TypeEngine

EnumT = TypeVar("EnumT", bound=Enum)

# SQLite only autoincrements a single-column primary key whose declared type is
# exactly INTEGER.  The variants keep MySQL's intended unsigned widths while
# preserving realistic SQLite integration tests.
BIGINT_UNSIGNED: TypeEngine[int] = (
    BigInteger()
    .with_variant(Integer(), "sqlite")
    .with_variant(MYSQL_BIGINT(unsigned=True), "mysql")
)
SMALLINT_UNSIGNED: TypeEngine[int] = (
    SmallInteger()
    .with_variant(Integer(), "sqlite")
    .with_variant(MYSQL_SMALLINT(unsigned=True), "mysql")
)
DATETIME_FSP6: TypeEngine[datetime] = DateTime().with_variant(
    MYSQL_DATETIME(fsp=6),
    "mysql",
)
LONGTEXT_TYPE: TypeEngine[str] = Text().with_variant(MYSQL_LONGTEXT(), "mysql")


def varchar_enum(
    enum_class: type[EnumT],
    *,
    name: str,
    length: int,
) -> SqlEnum:
    """Store a Python enum as portable VARCHAR rather than a MySQL ENUM."""

    return SqlEnum(
        enum_class,
        name=name,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        values_callable=lambda members: [member.value for member in members],
        length=length,
    )


class TimestampMixin:
    """Created/updated timestamps used by mutable aggregate roots."""

    created_at: Mapped[datetime] = mapped_column(
        DATETIME_FSP6,
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DATETIME_FSP6,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


__all__ = [
    "BIGINT_UNSIGNED",
    "DATETIME_FSP6",
    "LONGTEXT_TYPE",
    "SMALLINT_UNSIGNED",
    "TimestampMixin",
    "varchar_enum",
]
