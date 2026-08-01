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

from collections.abc import Iterable
from enum import Enum
from typing import Protocol

from app.models.policy import BenefitType
from app.models.user_category_profile import CategoryCode


class CalcType(str, Enum):
    """Logical calculation shape consumed by the future simulator engine."""

    LOAN_INTEREST = "LOAN_INTEREST"
    SAVINGS_ASSET = "SAVINGS_ASSET"
    CASH_VOUCHER = "CASH_VOUCHER"
    HOUSING_RENT = "HOUSING_RENT"
    EMPLOYMENT_EDUCATION = "EMPLOYMENT_EDUCATION"
    TAX_DEDUCTION = "TAX_DEDUCTION"


class _CategoryLike(Protocol):
    code: CategoryCode | str


class _CategoryLinkLike(Protocol):
    category: _CategoryLike


class BenefitLike(Protocol):
    """Minimal structural contract accepted from a model or DTO."""

    benefit_type: BenefitType | str


class PolicyLike(Protocol):
    """Minimal structural contract accepted from a model or DTO."""

    category_links: Iterable[_CategoryLinkLike]


_DIRECT_CALC_TYPE_BY_BENEFIT_TYPE: dict[BenefitType, CalcType] = {
    BenefitType.LOAN: CalcType.LOAN_INTEREST,
    BenefitType.SAVINGS: CalcType.SAVINGS_ASSET,
    BenefitType.TAX_REDUCTION: CalcType.TAX_DEDUCTION,
}

_CASH_LIKE_BENEFIT_TYPES = frozenset({BenefitType.CASH, BenefitType.DISCOUNT})


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
    """Return whether a simulator calculation can be derived for this benefit."""

    return resolve_calc_type(benefit, policy) is not None


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
