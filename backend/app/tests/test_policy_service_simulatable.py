"""Unit coverage for policy_service._is_policy_simulatable (is_simulatable field)."""

from __future__ import annotations

from app.crud.policies import PolicyBundle
from app.models.policy import BenefitType, Policy, PolicyBenefit
from app.models.user_category_profile import Category, CategoryCode
from app.services.policy_service import _is_policy_simulatable


def _bundle(
    *,
    benefit_types: list[BenefitType],
    category_codes: list[CategoryCode],
) -> PolicyBundle:
    return PolicyBundle(
        policy=Policy(title="테스트 정책"),
        categories=[Category(code=code, name=str(code)) for code in category_codes],
        benefits=[
            PolicyBenefit(benefit_type=benefit_type, amount_type="FIXED")
            for benefit_type in benefit_types
        ],
        conditions=[],
        documents=[],
    )


def test_simulatable_when_a_benefit_resolves_to_a_calc_type() -> None:
    bundle = _bundle(benefit_types=[BenefitType.CASH], category_codes=[CategoryCode.HOUSING])

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
    )

    assert _is_policy_simulatable(bundle) is True
