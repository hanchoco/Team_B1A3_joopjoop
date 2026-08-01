"""Resolves the logical simulator calculation type for a policy benefit.

``CalcType`` is not a database column.  It is a logical classification derived
at runtime from ``PolicyBenefit.benefit_type`` plus the policy's
``PolicyCategory`` links (see ``docs/simulator_calc_rules.md``).  If a
``calc_category`` column is ever added to the schema, only the body of
:func:`resolve_calc_type` needs to change to read that field instead --
callers must always go through :func:`resolve_calc_type`/:func:`can_simulate`
rather than branching on ``benefit_type`` themselves, so that migration stays
a one-function change.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from enum import Enum
from typing import Any, Protocol

from app.models.policy import BenefitType, CalcType
from app.models.user_category_profile import CategoryCode


class _CategoryLike(Protocol):
    code: CategoryCode | str


class _CategoryLinkLike(Protocol):
    category: _CategoryLike


class BenefitLike(Protocol):
    """Minimal structural contract accepted from a model or DTO."""

    benefit_type: BenefitType | str
    calculation_rule_json: Mapping[str, Any] | None


class PolicyLike(Protocol):
    """Minimal structural contract accepted from a model or DTO."""

    category_links: Iterable[_CategoryLinkLike]


_DIRECT_CALC_TYPE_BY_BENEFIT_TYPE: dict[BenefitType, CalcType] = {
    BenefitType.LOAN: CalcType.LOAN_INTEREST,
    BenefitType.SAVINGS: CalcType.SAVINGS_ASSET,
    BenefitType.TAX_REDUCTION: CalcType.TAX_DEDUCTION,
}

_CASH_LIKE_BENEFIT_TYPES = frozenset({BenefitType.CASH, BenefitType.DISCOUNT})

# calculation_rule_json에서 각 CalcType의 calculate_*()가 필수(required=True)로
# 읽는 필드. docs/simulator_calc_rules.md 계약 및
# services/policy_engine/simulator.py의 _decimal_field()/_int_field()/_str_field()
# 호출과 반드시 함께 갱신한다.
_REQUIRED_RULE_FIELDS_BY_CALC_TYPE: dict[CalcType, tuple[str, ...]] = {
    CalcType.LOAN_INTEREST: (
        "policy_interest_rate_percent",
        "max_loan_amount",
        "max_support_months",
        "repayment_type",
    ),
    CalcType.SAVINGS_ASSET: (
        "government_match_rate_percent",
        "monthly_max_support_amount",
        "maturity_months",
        "base_interest_rate_percent",
    ),
    CalcType.HOUSING_RENT: (
        "monthly_support_cap_amount",
        "support_months",
    ),
    CalcType.EMPLOYMENT_EDUCATION: ("support_months",),
    CalcType.TAX_DEDUCTION: (
        "deduction_rate_percent",
        "deduction_type",
    ),
}

# CASH_VOUCHER는 calculation_rule_json.amount_type("FIXED"/"PERCENTAGE")에 따라
# 필수 필드가 갈린다 (calculate_cash_voucher() 참고).
_REQUIRED_CASH_VOUCHER_RULE_FIELDS_BY_AMOUNT_TYPE: dict[str, tuple[str, ...]] = {
    "FIXED": ("amount", "payment_cycle", "max_count"),
    "PERCENTAGE": ("rate_percent", "cap_amount", "payment_cycle"),
}


def resolve_calc_type(benefit: BenefitLike, policy: PolicyLike) -> CalcType | None:
    """Derive the logical simulator calc type for one benefit.

    Mapping rules (see ``docs/simulator_calc_rules.md``):

    - ``LOAN`` -> ``LOAN_INTEREST``
    - ``SAVINGS`` -> ``SAVINGS_ASSET``
    - ``TAX_REDUCTION`` -> ``TAX_DEDUCTION``
    - ``CASH``/``DISCOUNT`` -> ``HOUSING_RENT`` if the policy has a HOUSING
      category, else ``EMPLOYMENT_EDUCATION`` if it has an EMPLOYMENT
      category, else ``CASH_VOUCHER``
    - ``SERVICE``/``OTHER`` -> ``None`` (not simulatable yet)
    """

    benefit_type = _normalise_benefit_type(benefit.benefit_type)

    direct_calc_type = _DIRECT_CALC_TYPE_BY_BENEFIT_TYPE.get(benefit_type)
    if direct_calc_type is not None:
        return direct_calc_type

    if benefit_type in _CASH_LIKE_BENEFIT_TYPES:
        category_codes = _policy_category_codes(policy)
        if CategoryCode.HOUSING in category_codes:
            return CalcType.HOUSING_RENT
        if CategoryCode.EMPLOYMENT in category_codes:
            return CalcType.EMPLOYMENT_EDUCATION
        return CalcType.CASH_VOUCHER

    return None


def can_simulate(benefit: BenefitLike, policy: PolicyLike) -> bool:
    """Return whether a simulator calculation can actually be run for this benefit.

    A ``CalcType`` resolving is necessary but not sufficient: the calculator
    for that type also needs its required fields present in
    ``benefit.calculation_rule_json`` (see docs/simulator_calc_rules.md), or
    ``simulator.simulate()`` would raise ``ValueError`` when called.
    """

    calc_type = resolve_calc_type(benefit, policy)
    if calc_type is None:
        return False
    return _has_required_rule_fields(calc_type, benefit.calculation_rule_json)


def _has_required_rule_fields(
    calc_type: CalcType,
    calculation_rule_json: Mapping[str, Any] | None,
) -> bool:
    if not calculation_rule_json:
        return False

    if calc_type is CalcType.CASH_VOUCHER:
        amount_type = calculation_rule_json.get("amount_type")
        required_fields = _REQUIRED_CASH_VOUCHER_RULE_FIELDS_BY_AMOUNT_TYPE.get(amount_type)
        if required_fields is None:
            return False
        return all(calculation_rule_json.get(field) is not None for field in required_fields)

    required_fields = _REQUIRED_RULE_FIELDS_BY_CALC_TYPE[calc_type]
    return all(calculation_rule_json.get(field) is not None for field in required_fields)


def _normalise_benefit_type(value: BenefitType | str) -> BenefitType:
    raw_value = value.value if isinstance(value, Enum) else value
    return BenefitType(raw_value)


def _normalise_category_code(value: CategoryCode | str) -> CategoryCode:
    raw_value = value.value if isinstance(value, Enum) else value
    return CategoryCode(raw_value)


def _policy_category_codes(policy: PolicyLike) -> set[CategoryCode]:
    return {_normalise_category_code(link.category.code) for link in policy.category_links}


__all__ = [
    "BenefitLike",
    "CalcType",
    "PolicyLike",
    "can_simulate",
    "resolve_calc_type",
]
