"""Unit coverage for the 추천순 정렬 규칙 (user_flow 7절: 가능성 높음 → 추가 확인 필요 순)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.models.user_policy import EligibilityStatus
from app.services.policy_service import _recommendation_sort_key, _status_sort_priority


def _evaluated(status: EligibilityStatus, match_score: str, published_date: date) -> object:
    return SimpleNamespace(
        evaluation=SimpleNamespace(status=status),
        match=SimpleNamespace(match_score=Decimal(match_score)),
        bundle=SimpleNamespace(policy=SimpleNamespace(published_date=published_date)),
    )


@pytest.mark.parametrize(
    ("status", "expected_priority"),
    [
        (EligibilityStatus.ELIGIBLE, 2),
        (EligibilityStatus.NEEDS_REVIEW, 1),
        (EligibilityStatus.INELIGIBLE, 0),
    ],
)
def test_status_sort_priority_orders_three_tiers(
    status: EligibilityStatus,
    expected_priority: int,
) -> None:
    assert _status_sort_priority(SimpleNamespace(evaluation=SimpleNamespace(status=status))) == (
        expected_priority
    )


def test_high_match_score_ineligible_policy_still_sorts_last() -> None:
    """조건을 많이 만족해 match_score가 높아도 필수 조건 미충족(INELIGIBLE)이면
    NEEDS_REVIEW보다 뒤로 밀려야 한다(gpt의견 4-4절, user_flow 7절)."""

    ineligible_high_score = _evaluated(EligibilityStatus.INELIGIBLE, "95.00", date(2026, 1, 1))
    needs_review_low_score = _evaluated(EligibilityStatus.NEEDS_REVIEW, "40.00", date(2026, 1, 1))
    eligible = _evaluated(EligibilityStatus.ELIGIBLE, "60.00", date(2026, 1, 1))

    ordered = sorted(
        [ineligible_high_score, needs_review_low_score, eligible],
        key=_recommendation_sort_key,
        reverse=True,
    )

    assert [item.evaluation.status for item in ordered] == [
        EligibilityStatus.ELIGIBLE,
        EligibilityStatus.NEEDS_REVIEW,
        EligibilityStatus.INELIGIBLE,
    ]


def test_same_tier_breaks_tie_by_match_score_then_published_date() -> None:
    older_higher_score = _evaluated(EligibilityStatus.ELIGIBLE, "90.00", date(2026, 1, 1))
    newer_lower_score = _evaluated(EligibilityStatus.ELIGIBLE, "80.00", date(2026, 3, 1))
    same_score_older = _evaluated(EligibilityStatus.ELIGIBLE, "80.00", date(2026, 2, 1))

    ordered = sorted(
        [newer_lower_score, same_score_older, older_higher_score],
        key=_recommendation_sort_key,
        reverse=True,
    )

    assert ordered == [older_higher_score, newer_lower_score, same_score_older]
