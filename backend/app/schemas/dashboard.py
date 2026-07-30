"""Pydantic v2 DTOs for the home dashboard summary."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class SchemaModel(BaseModel):
    """Strict ORM-compatible DTO base."""

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


class DashboardUpcomingPolicy(SchemaModel):
    """The single most imminent bookmarked/in-progress policy deadline."""

    policy_id: int
    title: str
    summary: str | None = None
    application_end_date: date
    days_until_deadline: int


class DashboardSummaryResponse(SchemaModel):
    """Home dashboard aggregate: nearest deadline and missed ELIGIBLE benefits."""

    upcoming_deadline_policy: DashboardUpcomingPolicy | None = None
    upcoming_deadline_count: int
    missed_benefit_total_amount: Decimal
    missed_benefit_policy_count: int
