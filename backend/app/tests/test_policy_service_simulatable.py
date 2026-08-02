"""Unit coverage for policy_service._is_policy_simulatable (is_simulatable field)."""

from __future__ import annotations

from app.crud.policies import PolicyBundle
from app.models.policy import BenefitType, Policy, PolicyBenefit
from app.models.user_category_profile import Category, CategoryCode
from app.services.policy_service import _is_policy_simulatable

_VALID_HOUSING_RENT_RULE = {
    "monthly_support_cap_amount": 200000,
    "support_months": 12,
}

_VALID_LOAN_INTEREST_RULE = {
    "policy_interest_rate_percent": 1.8,
    "max_loan_amount": 200000000,
    "max_support_months": 24,
    "repayment_type": "BULLET",
}


def _bundle(
    *,
    benefit_types: list[BenefitType],
    category_codes: list[CategoryCode],
    calculation_rule_json: list[dict | None] | None = None,
) -> PolicyBundle:
    rule_jsons = calculation_rule_json or [None] * len(benefit_types)
    return PolicyBundle(
        policy=Policy(title="테스트 정책"),
        categories=[Category(code=code, name=str(code)) for code in category_codes],
        benefits=[
            PolicyBenefit(
                benefit_type=benefit_type,
                amount_type="FIXED",
                calculation_rule_json=rule_json,
            )
            for benefit_type, rule_json in zip(benefit_types, rule_jsons, strict=True)
        ],
        conditions=[],
        documents=[],
    )


def test_simulatable_when_a_benefit_resolves_to_a_calc_type() -> None:
    bundle = _bundle(
        benefit_types=[BenefitType.CASH],
        category_codes=[CategoryCode.HOUSING],
        calculation_rule_json=[_VALID_HOUSING_RENT_RULE],
    )

    assert _is_policy_simulatable(bundle) is True


def test_not_simulatable_when_only_benefit_is_service() -> None:
    bundle = _bundle(benefit_types=[BenefitType.SERVICE], category_codes=[CategoryCode.TRANSPORT])

    assert _is_policy_simulatable(bundle) is False


def test_not_simulatable_with_no_benefits() -> None:
    bundle = _bundle(benefit_types=[], category_codes=[CategoryCode.HOUSING])

    assert _is_policy_simulatable(bundle) is False


def test_simulatable_if_any_one_of_several_benefits_resolves() -> None:
    """SERVICE alone would be False, but LOAN in the same policy makes it True."""

    bundle = _bundle(
        benefit_types=[BenefitType.SERVICE, BenefitType.LOAN],
        category_codes=[CategoryCode.FINANCE],
        calculation_rule_json=[None, _VALID_LOAN_INTEREST_RULE],
    )

    assert _is_policy_simulatable(bundle) is True


def test_not_simulatable_when_calc_type_resolves_but_rule_json_is_missing() -> None:
    """CASH resolves to a CalcType, but with no calculation_rule_json at all the
    simulator can't actually run - is_simulatable must stay False so the
    button doesn't light up for data-less policies."""

    bundle = _bundle(benefit_types=[BenefitType.CASH], category_codes=[CategoryCode.HOUSING])

    assert _is_policy_simulatable(bundle) is False


def test_not_simulatable_when_rule_json_is_missing_required_fields() -> None:
    bundle = _bundle(
        benefit_types=[BenefitType.LOAN],
        category_codes=[CategoryCode.FINANCE],
        calculation_rule_json=[{"policy_interest_rate_percent": 1.8}],
    )

    assert _is_policy_simulatable(bundle) is False
