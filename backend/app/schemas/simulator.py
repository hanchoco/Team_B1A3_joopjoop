"""Request and response DTOs for the CalcType-based policy benefit simulator.

``user_input`` is intentionally untyped (see SimulateBenefitRequest) because
each CalcType expects a different shape - the same reason
``PolicyBenefit.calculation_rule_json`` has no enforcing Pydantic model yet
(see docs/simulator_calc_rules.md). Values are transient calculation inputs
and must never be persisted as user profile data.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from app.models.policy import CalcType

Money = Annotated[
    Decimal,
    Field(ge=Decimal("0"), max_digits=15, decimal_places=2),
]
DurationMonths = Annotated[int, Field(ge=1, le=120)]


class SimulateBenefitRequest(BaseModel):
    """Transient, per-request user input for one benefit's calculation."""

    model_config = ConfigDict(extra="forbid")

    user_input: dict[str, JsonValue] = Field(default_factory=dict)


class SimulatorResult(BaseModel):
    """Normalised monthly, annual, and full-period simulator result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    category: CalcType
    monthly_before_amount: Money
    monthly_after_amount: Money
    monthly_savings_amount: Money
    annual_before_amount: Money
    annual_after_amount: Money
    annual_savings_amount: Money
    total_benefit_amount: Money
    support_months: DurationMonths
    breakdown: dict[str, Decimal] = Field(default_factory=dict)
    disclaimer: str = Field(min_length=1)
