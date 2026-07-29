"""Required application document definitions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import BIGINT_UNSIGNED, TimestampMixin

if TYPE_CHECKING:
    from app.models.policy import Policy
    from app.models.user_document_progress import UserDocumentProgress


class PolicyDocument(TimestampMixin, Base):
    """One confirmed document item displayed in the preparation checklist."""

    __tablename__ = "policy_documents"
    __table_args__ = (
        UniqueConstraint(
            "policy_id",
            "document_code",
            name="uk_policy_document_code",
        ),
        CheckConstraint("display_order >= 0", name="display_order_nonnegative"),
    )

    id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        primary_key=True,
        autoincrement=True,
    )
    policy_id: Mapped[int] = mapped_column(
        BIGINT_UNSIGNED,
        ForeignKey("policies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_code: Mapped[str] = mapped_column(String(50), nullable=False)
    document_name: Mapped[str] = mapped_column(String(255), nullable=False)
    required_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    issuing_organization: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    issuing_method: Mapped[str | None] = mapped_column(String(500), nullable=True)
    issuing_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    submission_format: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    is_required: Mapped[bool] = mapped_column(
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

    policy: Mapped[Policy] = relationship(back_populates="documents")
    user_progress: Mapped[list[UserDocumentProgress]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )


__all__ = ["PolicyDocument"]
