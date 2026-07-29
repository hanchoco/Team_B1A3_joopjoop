"""Request and response DTOs for the policy benefit simulator.

The request models intentionally contain only transient calculation inputs.  They
are not ORM models and must never be persisted as user profile data.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

Money = Annotated[
    Decimal,
    Field(ge=Decimal("0"), max_digits=15, decimal_places=2),
]
Percentage = Annotated[
    Decimal,
    Field(ge=Decimal("0"), le=Decimal("100"), max_digits=7, decimal_places=4),
]
DurationMonths = Annotated[int, Field(ge=1, le=120)]


class SimulatorCategory(str, Enum):
    """Categories that have independent simulator calculation rules."""

    HOUSING = "HOUSING"
    TRANSPORT = "TRANSPORT"
    FINANCE = "FINANCE"
    TAX = "TAX"
    EMPLOYMENT = "EMPLOYMENT"
    WELFARE = "WELFARE"


class SimulatorRequest(BaseModel):
    """Shared validation configuration for transient simulator inputs."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )


class HousingSimulatorRequest(SimulatorRequest):
    """Monthly housing cost and rent-support inputs."""

    monthly_rent_amount: Money
    monthly_management_fee_amount: Money = Decimal("0")
    deposit_amount: Money = Decimal("0")
    monthly_support_amount: Money
    support_months: DurationMonths = 12


class TransportSimulatorRequest(SimulatorRequest):
    """Monthly transport cost and reimbursement inputs."""

    monthly_transport_cost_amount: Money
    reimbursement_rate_percent: Percentage
    monthly_support_cap_amount: Money | None = None
    support_months: DurationMonths = 12


class FinanceSimulatorRequest(SimulatorRequest):
    """Principal and interest-rate reduction inputs.

    The MVP calculation compares interest-only monthly costs.  Repayment of
    principal is deliberately excluded because amortisation schedules differ by
    product.
    """

    principal_amount: Money
    annual_interest_rate_percent: Percentage
    interest_reduction_rate_percent: Percentage
    support_months: DurationMonths = 12


class TaxSimulatorRequest(SimulatorRequest):
    """Annual tax and reduction inputs."""

    annual_tax_amount: Money
    tax_reduction_rate_percent: Percentage
    max_reduction_amount: Money | None = None
    support_months: DurationMonths = 12


class EmploymentSimulatorRequest(SimulatorRequest):
    """Current monthly income and employment subsidy inputs."""

    monthly_income_amount: Money
    monthly_subsidy_amount: Money
    support_months: DurationMonths = 12


class WelfareSimulatorRequest(SimulatorRequest):
    """Monthly essential-living cost and welfare benefit inputs."""

    monthly_living_cost_amount: Money
    monthly_benefit_amount: Money
    support_months: DurationMonths = 12


class SimulatorResult(BaseModel):
    """Normalised monthly, annual, and full-period simulator result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    category: SimulatorCategory
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
