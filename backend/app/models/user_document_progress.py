"""Persisted user progress for policy application documents."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import BIGINT_UNSIGNED, DATETIME_FSP6, varchar_enum

if TYPE_CHECKING:
    from app.models.policy_document import PolicyDocument
    from app.models.user_policy import UserPolicyState


class DocumentPreparationStatus(str, Enum):
    """Preparation state for one required document."""

    NOT_STARTED = "NOT_STARTED"
    PREPARING = "PREPARING"
    READY = "READY"
    SUBMITTED = "SUBMITTED"


class UserDocumentProgress(Base):
    """One user's checklist state for one policy document."""

    __tablename__ = "user_document_checks"
    __table_args__ = (
        UniqueConstraint(
            "user_policy_state_id",
            "document_id",
            name="uk_state_document",
        ),
    )

    id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        primary_key=True,
        autoincrement=True,
    )
    user_policy_state_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("user_policy_states.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("policy_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    preparation_status: Mapped[DocumentPreparationStatus] = mapped_column(
        varchar_enum(
            DocumentPreparationStatus,
            name="document_preparation_status_enum",
            length=30,
        ),
        nullable=False,
        default=DocumentPreparationStatus.NOT_STARTED,
        server_default=DocumentPreparationStatus.NOT_STARTED.value,
    )
    is_checked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )
    checked_at: Mapped[datetime | None] = mapped_column(
        DATETIME_FSP6,
        nullable=True,
    )
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DATETIME_FSP6,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user_policy_state: Mapped[UserPolicyState] = relationship(back_populates="document_progress")
    document: Mapped[PolicyDocument] = relationship(back_populates="user_progress")


UserDocumentCheck = UserDocumentProgress


__all__ = [
    "DocumentPreparationStatus",
    "UserDocumentCheck",
    "UserDocumentProgress",
]
