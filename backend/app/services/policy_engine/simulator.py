"""Category-specific, Decimal-safe policy benefit calculations.

The calculator uses only the request DTO passed by the caller.  It neither reads
nor writes a user profile, which keeps concrete simulator amounts transient as
required by the product specification.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from app.schemas.simulator import (
    EmploymentSimulatorRequest,
    FinanceSimulatorRequest,
    HousingSimulatorRequest,
    SimulatorCategory,
    SimulatorResult,
    TaxSimulatorRequest,
    TransportSimulatorRequest,
    WelfareSimulatorRequest,
)

MONEY_QUANTUM = Decimal("0.01")
RATE_QUANTUM = Decimal("0.0001")
MONTHS_PER_YEAR = Decimal("12")
PERCENT_DIVISOR = Decimal("100")


def calculate_housing(request: HousingSimulatorRequest) -> SimulatorResult:
    """Calculate rent support without treating the refundable deposit as cost."""

    monthly_before = _decimal(request.monthly_rent_amount) + _decimal(
        request.monthly_management_fee_amount
    )
    monthly_support = min(
        _decimal(request.monthly_support_amount),
        _decimal(request.monthly_rent_amount),
    )
    return _build_result(
        category=SimulatorCategory.HOUSING,
        monthly_before=monthly_before,
        monthly_effect=monthly_support,
        support_months=request.support_months,
        direction="reduce",
        breakdown={
            "monthly_rent_amount": _money(request.monthly_rent_amount),
            "monthly_management_fee_amount": _money(request.monthly_management_fee_amount),
            "deposit_amount": _money(request.deposit_amount),
            "applied_monthly_support_amount": _money(monthly_support),
        },
        disclaimer=(
            "예상치는 월세 지원이 월세액을 넘지 않는다고 가정합니다. "
            "반환 가능한 보증금은 비용 합계에서 제외했으며 실제 지급액은 "
            "정책 심사와 지급 기간에 따라 달라질 수 있습니다."
        ),
    )


def calculate_transport(request: TransportSimulatorRequest) -> SimulatorResult:
    """Calculate a percentage reimbursement with an optional monthly cap."""

    monthly_before = _decimal(request.monthly_transport_cost_amount)
    reimbursement = monthly_before * _decimal(request.reimbursement_rate_percent) / PERCENT_DIVISOR
    if request.monthly_support_cap_amount is not None:
        reimbursement = min(
            reimbursement,
            _decimal(request.monthly_support_cap_amount),
        )
    reimbursement = min(reimbursement, monthly_before)

    breakdown = {
        "monthly_transport_cost_amount": _money(monthly_before),
        "reimbursement_rate_percent": _rate(request.reimbursement_rate_percent),
        "applied_monthly_support_amount": _money(reimbursement),
    }
    if request.monthly_support_cap_amount is not None:
        breakdown["monthly_support_cap_amount"] = _money(request.monthly_support_cap_amount)

    return _build_result(
        category=SimulatorCategory.TRANSPORT,
        monthly_before=monthly_before,
        monthly_effect=reimbursement,
        support_months=request.support_months,
        direction="reduce",
        breakdown=breakdown,
        disclaimer=(
            "교통비 환급률과 한도를 단순 적용한 예상치입니다. 인정 교통수단, "
            "이용 실적 및 월별 한도 산정 방식에 따라 실제 환급액이 달라질 수 있습니다."
        ),
    )


def calculate_finance(request: FinanceSimulatorRequest) -> SimulatorResult:
    """Compare interest-only cost before and after a rate reduction."""

    principal = _decimal(request.principal_amount)
    annual_rate = _decimal(request.annual_interest_rate_percent)
    reduction_rate = min(
        _decimal(request.interest_reduction_rate_percent),
        annual_rate,
    )
    supported_rate = annual_rate - reduction_rate
    monthly_before = principal * annual_rate / PERCENT_DIVISOR / MONTHS_PER_YEAR
    monthly_after = principal * supported_rate / PERCENT_DIVISOR / MONTHS_PER_YEAR
    monthly_savings = monthly_before - monthly_after

    return _build_result(
        category=SimulatorCategory.FINANCE,
        monthly_before=monthly_before,
        monthly_effect=monthly_savings,
        support_months=request.support_months,
        direction="reduce",
        breakdown={
            "principal_amount": _money(principal),
            "annual_interest_rate_percent": _rate(annual_rate),
            "applied_interest_reduction_rate_percent": _rate(reduction_rate),
            "supported_annual_interest_rate_percent": _rate(supported_rate),
        },
        disclaimer=(
            "원금이 유지되는 단순 이자 계산이며 원금 상환, 복리, 중도상환수수료와 "
            "상품별 상환 방식은 반영하지 않았습니다. 금융기관의 실제 약정 조건을 "
            "반드시 확인하세요."
        ),
    )


def calculate_tax(request: TaxSimulatorRequest) -> SimulatorResult:
    """Calculate a proportional annual tax reduction with an optional cap."""

    annual_tax = _decimal(request.annual_tax_amount)
    annual_reduction = annual_tax * _decimal(request.tax_reduction_rate_percent) / PERCENT_DIVISOR
    if request.max_reduction_amount is not None:
        annual_reduction = min(
            annual_reduction,
            _decimal(request.max_reduction_amount),
        )
    annual_reduction = min(annual_reduction, annual_tax)

    monthly_before = annual_tax / MONTHS_PER_YEAR
    monthly_reduction = annual_reduction / MONTHS_PER_YEAR
    breakdown = {
        "annual_tax_amount": _money(annual_tax),
        "tax_reduction_rate_percent": _rate(request.tax_reduction_rate_percent),
        "applied_annual_reduction_amount": _money(annual_reduction),
    }
    if request.max_reduction_amount is not None:
        breakdown["max_reduction_amount"] = _money(request.max_reduction_amount)

    return _build_result(
        category=SimulatorCategory.TAX,
        monthly_before=monthly_before,
        monthly_effect=monthly_reduction,
        support_months=request.support_months,
        direction="reduce",
        breakdown=breakdown,
        disclaimer=(
            "입력한 연간 세액에 감면율과 한도만 적용한 단순 예상치입니다. "
            "과세표준, 공제 순서, 지방세 및 개인별 신고 결과에 따라 실제 세액은 "
            "달라질 수 있습니다."
        ),
    )


def calculate_employment(
    request: EmploymentSimulatorRequest,
) -> SimulatorResult:
    """Calculate the cash-flow increase from a monthly employment subsidy."""

    monthly_income = _decimal(request.monthly_income_amount)
    monthly_subsidy = _decimal(request.monthly_subsidy_amount)
    return _build_result(
        category=SimulatorCategory.EMPLOYMENT,
        monthly_before=monthly_income,
        monthly_effect=monthly_subsidy,
        support_months=request.support_months,
        direction="increase",
        breakdown={
            "monthly_income_amount": _money(monthly_income),
            "monthly_subsidy_amount": _money(monthly_subsidy),
        },
        disclaimer=(
            "고용 지원금을 월 소득에 더한 현금흐름 예상치입니다. 세금·사회보험료, "
            "근속 요건, 사업주 지급분 및 중도 종료 조건은 반영하지 않았습니다."
        ),
    )


def calculate_welfare(request: WelfareSimulatorRequest) -> SimulatorResult:
    """Calculate how a welfare benefit offsets essential monthly costs."""

    monthly_before = _decimal(request.monthly_living_cost_amount)
    applied_benefit = min(
        _decimal(request.monthly_benefit_amount),
        monthly_before,
    )
    return _build_result(
        category=SimulatorCategory.WELFARE,
        monthly_before=monthly_before,
        monthly_effect=applied_benefit,
        support_months=request.support_months,
        direction="reduce",
        breakdown={
            "monthly_living_cost_amount": _money(monthly_before),
            "requested_monthly_benefit_amount": _money(request.monthly_benefit_amount),
            "applied_monthly_benefit_amount": _money(applied_benefit),
        },
        disclaimer=(
            "복지 급여가 입력한 생활비를 우선 보전한다고 가정한 예상치입니다. "
            "소득인정액, 가구원 수, 중복 수급 제한과 현물 급여는 별도 심사가 필요합니다."
        ),
    )


def _build_result(
    *,
    category: SimulatorCategory,
    monthly_before: Decimal,
    monthly_effect: Decimal,
    support_months: int,
    direction: Literal["reduce", "increase"],
    breakdown: dict[str, Decimal],
    disclaimer: str,
) -> SimulatorResult:
    active_months_in_year = min(support_months, 12)
    annual_before = monthly_before * MONTHS_PER_YEAR
    annual_effect = monthly_effect * Decimal(active_months_in_year)
    total_benefit = monthly_effect * Decimal(support_months)

    if direction == "reduce":
        monthly_after = max(monthly_before - monthly_effect, Decimal("0"))
        annual_after = max(annual_before - annual_effect, Decimal("0"))
    else:
        monthly_after = monthly_before + monthly_effect
        annual_after = annual_before + annual_effect

    return SimulatorResult(
        category=category,
        monthly_before_amount=_money(monthly_before),
        monthly_after_amount=_money(monthly_after),
        monthly_savings_amount=_money(monthly_effect),
        annual_before_amount=_money(annual_before),
        annual_after_amount=_money(annual_after),
        annual_savings_amount=_money(annual_effect),
        total_benefit_amount=_money(total_benefit),
        support_months=support_months,
        breakdown=breakdown,
        disclaimer=disclaimer,
    )


def _decimal(value: Decimal | int | str) -> Decimal:
    """Convert through text so a future caller cannot leak binary-float noise."""

    return value if isinstance(value, Decimal) else Decimal(str(value))


def _money(value: Decimal | int | str) -> Decimal:
    return _decimal(value).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def _rate(value: Decimal | int | str) -> Decimal:
    return _decimal(value).quantize(RATE_QUANTUM, rounding=ROUND_HALF_UP)
