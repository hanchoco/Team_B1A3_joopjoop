"""Category definitions and flexible category-specific user answers."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import (
    BIGINT_UNSIGNED,
    DATETIME_FSP6,
    SMALLINT_UNSIGNED,
    TimestampMixin,
    varchar_enum,
)

if TYPE_CHECKING:
    from app.models.policy import PolicyCategory
    from app.models.user import User


class CategoryCode(str, Enum):
    """Initial policy category registry."""

    HOUSING = "HOUSING"
    TRANSPORT = "TRANSPORT"
    FINANCE = "FINANCE"
    TAX = "TAX"
    EMPLOYMENT = "EMPLOYMENT"
    WELFARE = "WELFARE"
    PARTICIPATION = "PARTICIPATION"
    ETC = "ETC"


class AnswerType(str, Enum):
    """Storage/rendering type for a category question."""

    SINGLE_SELECT = "SINGLE_SELECT"
    MULTI_SELECT = "MULTI_SELECT"
    NUMBER = "NUMBER"
    BOOLEAN = "BOOLEAN"
    TEXT = "TEXT"
    DATE = "DATE"


class Category(TimestampMixin, Base):
    """Top-level policy category shown on the dashboard."""

    __tablename__ = "categories"
    __table_args__ = (CheckConstraint("display_order >= 0", name="display_order_nonnegative"),)

    id: Mapped[int] = mapped_column(
        SMALLINT_UNSIGNED,
        primary_key=True,
        autoincrement=True,
    )
    code: Mapped[CategoryCode] = mapped_column(
        varchar_enum(
            CategoryCode,
            name="category_code_enum",
            length=30,
        ),
        nullable=False,
        unique=True,
    )
    name: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_order: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default="0",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        index=True,
    )

    questions: Mapped[list[CategoryQuestion]] = relationship(
        back_populates="category",
        cascade="all, delete-orphan",
        order_by="CategoryQuestion.display_order",
    )
    policy_links: Mapped[list[PolicyCategory]] = relationship(
        back_populates="category",
        cascade="all, delete-orphan",
    )


class CategoryQuestion(TimestampMixin, Base):
    """A configurable question used for one policy category."""

    __tablename__ = "category_questions"
    __table_args__ = (
        UniqueConstraint(
            "category_id",
            "question_key",
            name="uk_category_question_key",
        ),
        CheckConstraint("display_order >= 0", name="display_order_nonnegative"),
    )

    id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        primary_key=True,
        autoincrement=True,
    )
    category_id: Mapped[int] = mapped_column(
        SMALLINT_UNSIGNED,
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_key: Mapped[str] = mapped_column(String(100), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    answer_type: Mapped[AnswerType] = mapped_column(
        varchar_enum(
            AnswerType,
            name="answer_type_enum",
            length=20,
        ),
        nullable=False,
    )
    options_json: Mapped[list[Any] | dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )
    is_used_for_matching: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )
    display_order: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default="0",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        index=True,
    )

    category: Mapped[Category] = relationship(back_populates="questions")
    user_answers: Mapped[list[UserCategoryAnswer]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
    )


class UserCategoryAnswer(Base):
    """One user's persisted answer to one category question."""

    __tablename__ = "user_category_answers"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "question_id",
            name="uk_user_question",
        ),
    )

    id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("category_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    answer_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    answered_at: Mapped[datetime] = mapped_column(
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

    user: Mapped[User] = relationship(back_populates="category_answers")
    question: Mapped[CategoryQuestion] = relationship(back_populates="user_answers")


__all__ = [
    "AnswerType",
    "Category",
    "CategoryCode",
    "CategoryQuestion",
    "UserCategoryAnswer",
]
