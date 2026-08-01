"""Category-specific, Decimal-safe policy benefit calculations.

The calculator uses only the request DTO passed by the caller.  It neither reads
nor writes a user profile, which keeps concrete simulator amounts transient as
required by the product specification.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Literal

from app.models.policy import Policy, PolicyBenefit
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
from app.services.policy_engine.calc_type import CalcType, resolve_calc_type

MONEY_QUANTUM = Decimal("0.01")
RATE_QUANTUM = Decimal("0.0001")
MONTHS_PER_YEAR = Decimal("12")
PERCENT_DIVISOR = Decimal("100")

# calculation_rule_json에 실데이터를 채우는 방법은 docs/simulator_calc_rules.md 계약을 따른다.
CALC_TYPE_DISCLAIMER = (
    "본 계산 결과는 정책 공고 기준을 적용한 예상 시뮬레이션 금액이며, 실제 지급액은 "
    "개인의 세부 소득 심사, 금융기관 약정 조건 및 자격 검증 결과에 따라 달라질 수 있습니다."
)


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


# ---------------------------------------------------------------------------
# CalcType 기반 계산기 (docs/simulator_calc_rules.md 계약을 소비)
#
# 위의 calculate_housing()/calculate_transport() 등은 카테고리별로 사용자가 직접
# 입력한 비용을 비교하는 "카테고리 시뮬레이터"이고, 아래 6개 함수는 이미 저장된
# PolicyBenefit.calculation_rule_json(정책이 확정한 조건) + 사용자가 그때그때 입력하는
# user_input을 조합해 계산하는 별도 경로다. calculation_rule_json은 아직 이 스키마를
# 강제하는 Pydantic 모델이 없으므로(문서 상단 참고), 각 함수가 직접 필수 필드를 검증한다.
# ---------------------------------------------------------------------------

_CALC_TYPE_SIMULATOR_CATEGORY: dict[CalcType, SimulatorCategory] = {
    CalcType.LOAN_INTEREST: SimulatorCategory.FINANCE,
    CalcType.SAVINGS_ASSET: SimulatorCategory.FINANCE,
    CalcType.CASH_VOUCHER: SimulatorCategory.WELFARE,
    CalcType.HOUSING_RENT: SimulatorCategory.HOUSING,
    CalcType.EMPLOYMENT_EDUCATION: SimulatorCategory.EMPLOYMENT,
    CalcType.TAX_DEDUCTION: SimulatorCategory.TAX,
}


class UnsupportedCalcTypeError(ValueError):
    """Raised when no CalcType can be resolved for a benefit/policy pair."""


def calculate_loan_interest(
    calculation_rule_json: Mapping[str, Any],
    user_input: Mapping[str, Any],
) -> SimulatorResult:
    """Compare interest-only cost between the policy rate and a baseline rate."""

    policy_rate = _decimal_field(
        calculation_rule_json, "policy_interest_rate_percent", source="calculation_rule_json"
    )
    reduction_rate = _decimal_field(
        calculation_rule_json,
        "interest_reduction_rate_percent",
        source="calculation_rule_json",
        required=False,
    )
    max_loan_amount = _decimal_field(
        calculation_rule_json, "max_loan_amount", source="calculation_rule_json"
    )
    max_support_months = _int_field(
        calculation_rule_json, "max_support_months", source="calculation_rule_json"
    )
    # repayment_type은 문서상 자유 확장 가능한 값("등")이라 값 자체를 검증하지 않고
    # 존재 여부만 확인한다. Decimal 전용인 breakdown에는 문자열이라 넣지 않는다.
    _str_field(calculation_rule_json, "repayment_type", source="calculation_rule_json")

    requested_loan_amount = _decimal_field(user_input, "loan_amount", source="user_input")
    loan_amount = min(requested_loan_amount, max_loan_amount)

    general_rate = _decimal_field(
        user_input,
        "general_interest_rate_percent",
        source="user_input",
        required=False,
    )
    if general_rate is None:
        if reduction_rate is None:
            raise ValueError(
                "일반 대출 금리를 알 수 없어 절감액을 계산할 수 없습니다. "
                "user_input.general_interest_rate_percent 또는 "
                "calculation_rule_json.interest_reduction_rate_percent 중 하나가 필요합니다."
            )
        general_rate = policy_rate + reduction_rate

    requested_support_months = _int_field(
        user_input, "support_months", source="user_input", required=False
    )
    support_months = (
        min(requested_support_months, max_support_months)
        if requested_support_months is not None
        else max_support_months
    )

    monthly_before = loan_amount * general_rate / PERCENT_DIVISOR / MONTHS_PER_YEAR
    monthly_after = loan_amount * policy_rate / PERCENT_DIVISOR / MONTHS_PER_YEAR
    monthly_effect = max(monthly_before - monthly_after, Decimal("0"))

    return _build_calc_type_result(
        calc_type=CalcType.LOAN_INTEREST,
        monthly_before=monthly_before,
        monthly_effect=monthly_effect,
        support_months=support_months,
        direction="reduce",
        breakdown={
            "loan_amount": _money(loan_amount),
            "policy_interest_rate_percent": _rate(policy_rate),
            "general_interest_rate_percent": _rate(general_rate),
        },
    )


def calculate_savings_asset(
    calculation_rule_json: Mapping[str, Any],
    user_input: Mapping[str, Any],
) -> SimulatorResult:
    """Compare a self-only deposit against the government-matched deposit."""

    match_rate = _decimal_field(
        calculation_rule_json, "government_match_rate_percent", source="calculation_rule_json"
    )
    monthly_max_support = _decimal_field(
        calculation_rule_json, "monthly_max_support_amount", source="calculation_rule_json"
    )
    maturity_months = _int_field(
        calculation_rule_json, "maturity_months", source="calculation_rule_json"
    )
    base_rate = _decimal_field(
        calculation_rule_json, "base_interest_rate_percent", source="calculation_rule_json"
    )
    bonus_rate = _decimal_field(
        calculation_rule_json,
        "bonus_interest_rate_percent",
        source="calculation_rule_json",
        required=False,
        default=Decimal("0"),
    )

    monthly_deposit = _decimal_field(user_input, "monthly_deposit_amount", source="user_input")

    matched_base = min(monthly_deposit, monthly_max_support)
    monthly_match_amount = matched_base * match_rate / PERCENT_DIVISOR
    # 만기 시 적용되는 이자(base+bonus)는 월/연 현금흐름 비교에는 반영하지 않고
    # breakdown에 참고용으로만 노출한다 - 이자는 만기 시점에만 발생하므로 매월 적립액
    # 비교와 성격이 다르다(calculate_finance의 원금 상환 단순화와 동일한 접근).
    applied_interest_rate = base_rate + bonus_rate

    return _build_calc_type_result(
        calc_type=CalcType.SAVINGS_ASSET,
        monthly_before=monthly_deposit,
        monthly_effect=monthly_match_amount,
        support_months=maturity_months,
        direction="increase",
        breakdown={
            "monthly_deposit_amount": _money(monthly_deposit),
            "monthly_matched_amount": _money(monthly_match_amount),
            "government_match_rate_percent": _rate(match_rate),
            "applied_interest_rate_percent": _rate(applied_interest_rate),
        },
    )


def calculate_cash_voucher(
    calculation_rule_json: Mapping[str, Any],
    user_input: Mapping[str, Any],
) -> SimulatorResult:
    """Calculate a direct cash/voucher benefit, branching on amount_type."""

    amount_type = _str_field(calculation_rule_json, "amount_type", source="calculation_rule_json")
    payment_cycle = _str_field(
        calculation_rule_json, "payment_cycle", source="calculation_rule_json"
    )

    if amount_type == "FIXED":
        amount = _decimal_field(calculation_rule_json, "amount", source="calculation_rule_json")
        max_count = _int_field(calculation_rule_json, "max_count", source="calculation_rule_json")
        requested_count = _int_field(
            user_input, "count", source="user_input", required=False, default=max_count
        )
        count = max(min(requested_count, max_count), 1)
        total_amount = amount * Decimal(count)
        breakdown = {
            "amount": _money(amount),
            "applied_count": Decimal(count),
        }
    elif amount_type == "PERCENTAGE":
        rate_percent = _decimal_field(
            calculation_rule_json, "rate_percent", source="calculation_rule_json"
        )
        cap_amount = _decimal_field(
            calculation_rule_json, "cap_amount", source="calculation_rule_json"
        )
        base_amount = _decimal_field(user_input, "base_amount", source="user_input")
        count = max(
            _int_field(user_input, "count", source="user_input", required=False, default=1),
            1,
        )
        applied_benefit_per_payment = min(
            base_amount * rate_percent / PERCENT_DIVISOR,
            cap_amount,
        )
        total_amount = applied_benefit_per_payment * Decimal(count)
        breakdown = {
            "base_amount": _money(base_amount),
            "rate_percent": _rate(rate_percent),
            "cap_amount": _money(cap_amount),
            "applied_benefit_per_payment": _money(applied_benefit_per_payment),
        }
    else:
        raise ValueError(
            f"calculation_rule_json.amount_type은 FIXED 또는 PERCENTAGE여야 합니다: {amount_type}"
        )

    support_months = count if payment_cycle == "MONTHLY" else 1
    monthly_effect = total_amount / Decimal(support_months)

    return _build_calc_type_result(
        calc_type=CalcType.CASH_VOUCHER,
        monthly_before=Decimal("0"),
        monthly_effect=monthly_effect,
        support_months=support_months,
        direction="increase",
        breakdown=breakdown,
    )


def calculate_housing_rent(
    calculation_rule_json: Mapping[str, Any],
    user_input: Mapping[str, Any],
) -> SimulatorResult:
    """Compare rent cost against a policy-capped monthly rent support."""

    support_cap = _decimal_field(
        calculation_rule_json, "monthly_support_cap_amount", source="calculation_rule_json"
    )
    rule_support_months = _int_field(
        calculation_rule_json, "support_months", source="calculation_rule_json"
    )
    rent_limit = _decimal_field(
        calculation_rule_json,
        "rent_limit_amount",
        source="calculation_rule_json",
        required=False,
    )
    deposit_limit = _decimal_field(
        calculation_rule_json,
        "deposit_limit_amount",
        source="calculation_rule_json",
        required=False,
    )

    # 관리비는 문서(docs/simulator_calc_rules.md HOUSING_RENT)상 지원 대상이 아닐 수 있어
    # 월세 비용/지원액 계산에서 제외하고, 참고용으로만 breakdown에 남긴다.
    monthly_rent = _decimal_field(user_input, "monthly_rent_amount", source="user_input")
    monthly_management_fee = _decimal_field(
        user_input,
        "monthly_management_fee_amount",
        source="user_input",
        required=False,
        default=Decimal("0"),
    )
    deposit_amount = _decimal_field(
        user_input, "deposit_amount", source="user_input", required=False
    )

    rent_eligible_for_support = (
        min(monthly_rent, rent_limit) if rent_limit is not None else monthly_rent
    )
    monthly_support = min(support_cap, rent_eligible_for_support)

    requested_support_months = _int_field(
        user_input, "support_months", source="user_input", required=False
    )
    support_months = (
        min(requested_support_months, rule_support_months)
        if requested_support_months is not None
        else rule_support_months
    )

    breakdown = {
        "monthly_rent_amount": _money(monthly_rent),
        "monthly_management_fee_amount": _money(monthly_management_fee),
        "monthly_support_cap_amount": _money(support_cap),
        "applied_monthly_support_amount": _money(monthly_support),
    }
    if rent_limit is not None:
        breakdown["rent_limit_amount"] = _money(rent_limit)
    if deposit_limit is not None:
        breakdown["deposit_limit_amount"] = _money(deposit_limit)
    if deposit_amount is not None:
        breakdown["deposit_amount"] = _money(deposit_amount)

    return _build_calc_type_result(
        calc_type=CalcType.HOUSING_RENT,
        monthly_before=monthly_rent,
        monthly_effect=monthly_support,
        support_months=support_months,
        direction="reduce",
        breakdown=breakdown,
    )


def calculate_employment_education(
    calculation_rule_json: Mapping[str, Any],
    user_input: Mapping[str, Any],
) -> SimulatorResult:
    """Add recurring training/education support to income; bonus is one-time."""

    training_allowance = _decimal_field(
        calculation_rule_json,
        "training_allowance_amount",
        source="calculation_rule_json",
        required=False,
        default=Decimal("0"),
    )
    education_subsidy = _decimal_field(
        calculation_rule_json,
        "education_subsidy_amount",
        source="calculation_rule_json",
        required=False,
        default=Decimal("0"),
    )
    success_bonus = _decimal_field(
        calculation_rule_json,
        "employment_success_bonus_amount",
        source="calculation_rule_json",
        required=False,
        default=Decimal("0"),
    )
    support_months = _int_field(
        calculation_rule_json, "support_months", source="calculation_rule_json"
    )

    current_income = _decimal_field(
        user_input,
        "current_monthly_income_amount",
        source="user_input",
        required=False,
        default=Decimal("0"),
    )

    monthly_effect = training_allowance + education_subsidy

    result = _build_calc_type_result(
        calc_type=CalcType.EMPLOYMENT_EDUCATION,
        monthly_before=current_income,
        monthly_effect=monthly_effect,
        support_months=support_months,
        direction="increase",
        breakdown={
            "training_allowance_amount": _money(training_allowance),
            "education_subsidy_amount": _money(education_subsidy),
            "employment_success_bonus_amount": _money(success_bonus),
        },
    )
    if success_bonus == 0:
        return result
    # 취업성공수당은 1회성이라 월/연 환산에는 넣지 않고 총 예상 혜택에만 더한다.
    return result.model_copy(
        update={"total_benefit_amount": _money(result.total_benefit_amount + success_bonus)}
    )


def calculate_tax_deduction(
    calculation_rule_json: Mapping[str, Any],
    user_input: Mapping[str, Any],
) -> SimulatorResult:
    """Calculate a proportional annual tax reduction with an optional cap."""

    deduction_rate = _decimal_field(
        calculation_rule_json, "deduction_rate_percent", source="calculation_rule_json"
    )
    max_deduction = _decimal_field(
        calculation_rule_json,
        "max_deduction_amount",
        source="calculation_rule_json",
        required=False,
    )
    deduction_type = _str_field(
        calculation_rule_json, "deduction_type", source="calculation_rule_json"
    )
    if deduction_type not in {"TAX_CREDIT", "INCOME_DEDUCTION"}:
        raise ValueError(
            "calculation_rule_json.deduction_type은 TAX_CREDIT 또는 INCOME_DEDUCTION이어야 "
            f"합니다: {deduction_type}"
        )

    annual_tax_amount = _decimal_field(user_input, "annual_tax_amount", source="user_input")
    support_months = _int_field(
        user_input, "support_months", source="user_input", required=False, default=12
    )

    annual_reduction = annual_tax_amount * deduction_rate / PERCENT_DIVISOR
    if max_deduction is not None:
        annual_reduction = min(annual_reduction, max_deduction)
    annual_reduction = min(annual_reduction, annual_tax_amount)

    monthly_before = annual_tax_amount / MONTHS_PER_YEAR
    monthly_reduction = annual_reduction / MONTHS_PER_YEAR

    breakdown = {
        "annual_tax_amount": _money(annual_tax_amount),
        "deduction_rate_percent": _rate(deduction_rate),
        "applied_annual_reduction_amount": _money(annual_reduction),
    }
    if max_deduction is not None:
        breakdown["max_deduction_amount"] = _money(max_deduction)

    return _build_calc_type_result(
        calc_type=CalcType.TAX_DEDUCTION,
        monthly_before=monthly_before,
        monthly_effect=monthly_reduction,
        support_months=support_months,
        direction="reduce",
        breakdown=breakdown,
    )


CALCULATORS: dict[CalcType, Callable[[Mapping[str, Any], Mapping[str, Any]], SimulatorResult]] = {
    CalcType.LOAN_INTEREST: calculate_loan_interest,
    CalcType.SAVINGS_ASSET: calculate_savings_asset,
    CalcType.CASH_VOUCHER: calculate_cash_voucher,
    CalcType.HOUSING_RENT: calculate_housing_rent,
    CalcType.EMPLOYMENT_EDUCATION: calculate_employment_education,
    CalcType.TAX_DEDUCTION: calculate_tax_deduction,
}


def simulate(
    benefit: PolicyBenefit,
    policy: Policy,
    user_input: Mapping[str, Any],
) -> SimulatorResult:
    """Resolve benefit's CalcType via resolve_calc_type() and dispatch to it.

    Callers must always go through this function (or CALCULATORS via a
    resolve_calc_type() lookup) instead of branching on benefit_type directly,
    so the dispatch stays centralised in one place.
    """

    calc_type = resolve_calc_type(benefit, policy)
    if calc_type is None:
        raise UnsupportedCalcTypeError(
            f"benefit_type={benefit.benefit_type}에 대해서는 계산 로직을 지원하지 않습니다."
        )
    calculation_rule_json = benefit.calculation_rule_json or {}
    return CALCULATORS[calc_type](calculation_rule_json, user_input)


def _build_calc_type_result(
    *,
    calc_type: CalcType,
    monthly_before: Decimal,
    monthly_effect: Decimal,
    support_months: int,
    direction: Literal["reduce", "increase"],
    breakdown: dict[str, Decimal],
) -> SimulatorResult:
    return _build_result(
        category=_CALC_TYPE_SIMULATOR_CATEGORY[calc_type],
        monthly_before=monthly_before,
        monthly_effect=monthly_effect,
        support_months=support_months,
        direction=direction,
        breakdown=breakdown,
        disclaimer=CALC_TYPE_DISCLAIMER,
    )


def _field(
    mapping: Mapping[str, Any],
    key: str,
    *,
    source: str,
    required: bool = True,
    default: Any = None,
) -> Any:
    value = mapping.get(key) if hasattr(mapping, "get") else None
    if value is None:
        if required:
            raise ValueError(f"{source}에 필수 필드 '{key}'가 없습니다.")
        return default
    return value


def _decimal_field(
    mapping: Mapping[str, Any],
    key: str,
    *,
    source: str,
    required: bool = True,
    default: Decimal | None = None,
) -> Decimal | None:
    value = _field(mapping, key, source=source, required=required, default=default)
    return _decimal(value) if value is not None else None


def _int_field(
    mapping: Mapping[str, Any],
    key: str,
    *,
    source: str,
    required: bool = True,
    default: int | None = None,
) -> int | None:
    value = _field(mapping, key, source=source, required=required, default=default)
    return int(value) if value is not None else None


def _str_field(
    mapping: Mapping[str, Any],
    key: str,
    *,
    source: str,
    required: bool = True,
    default: str | None = None,
) -> str | None:
    value = _field(mapping, key, source=source, required=required, default=default)
    if value is not None and not isinstance(value, str):
        raise ValueError(f"{source} 필드 '{key}'는 문자열이어야 합니다.")
    return value
