"""Regression tests for the policy seed pipeline.

Covers three bugs found in a codebase audit:
  1. profile.age/profile.region_code were rejected by the approval validator.
  2. category_codes were never generated for a seed draft.
  3. benefits were never extracted for a seed draft.

No pytest-asyncio plugin is installed, so async functions are driven with
``asyncio.run`` inside ordinary sync test functions, matching this project's
existing testing conventions.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from app.services.ai.benefit_extractor import (
    ExtractedBenefit,
    extract_benefits,
    validate_benefit_payload,
)
from app.services.ai.rule_extractor import (
    ALLOWED_CONDITION_KEYS,
    categorize_policy,
    validate_condition_payload,
)
from scripts.seed_policy_data import SeedDraftError, _validated_bundles


class _FakeSolarClient:
    """Minimal double matching ``SolarClient.complete_json``'s signature."""

    def __init__(self, response: dict) -> None:
        self._response = response

    async def complete_json(self, system_prompt: str, user_content: str) -> dict:
        del system_prompt, user_content
        return self._response


def _minimal_policy() -> dict:
    return {
        "source": "ONTONG_YOUTH",
        "external_id": "seed-test-1",
        "title": "청년 월세 지원",
        "summary": "",
        "description": "",
        "support_target_text": "",
        "support_content_text": "",
        "application_method": "",
        "provider_name": "",
        "application_url": "",
        "status": "ACTIVE",
        "subcategory": "",
        "region_scope": "",
        "region_code": "",
        "contact": "",
        "original_text": "",
        "application_start_date": None,
        "application_end_date": None,
        "published_date": None,
        "is_ongoing": False,
        "is_active": True,
        "raw_payload": {"plcyNm": "청년 월세 지원"},
        "source_updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _minimal_draft(**bundle_overrides: object) -> dict:
    bundle = {
        "policy": _minimal_policy(),
        "conditions": [],
        "documents": [],
        "benefits": [],
        "category_codes": ["HOUSING"],
    }
    bundle.update(bundle_overrides)
    return {
        "schema_version": 1,
        "kind": "policy_seed_batch",
        "status": "pending_review",
        "policies": [bundle],
    }


# ---------------------------------------------------------------------------
# Bug 1: condition_key allow-list
# ---------------------------------------------------------------------------


def test_age_and_region_condition_keys_are_allowed() -> None:
    assert "profile.age" in ALLOWED_CONDITION_KEYS
    assert "profile.region_code" in ALLOWED_CONDITION_KEYS


def test_approval_accepts_age_and_region_conditions() -> None:
    """Reproduces the exact bug: extract_conditions() always emits these two
    hardcoded conditions for any policy with an age range or region list."""

    payload = {
        "conditions": [
            {
                "condition_key": "profile.age",
                "operator": "BETWEEN",
                "expected_value_json": {"min": 19, "max": 34},
                "is_required": True,
                "check_mode": "AUTO",
                "description": "만 19세 ~ 34세",
                "failure_message": "나이 조건을 확인하세요.",
            },
            {
                "condition_key": "profile.region_code",
                "operator": "IN",
                "expected_value_json": {"values": ["11", "41"]},
                "is_required": True,
                "check_mode": "AUTO",
                "description": "거주지역 조건",
                "failure_message": "거주지역을 확인하세요.",
            },
        ]
    }

    result = validate_condition_payload(payload)

    assert {condition.condition_key for condition in result} == {
        "profile.age",
        "profile.region_code",
    }


# ---------------------------------------------------------------------------
# Bug 2: category_codes generation
# ---------------------------------------------------------------------------


def test_categorize_policy_maps_known_keywords() -> None:
    assert categorize_policy("주거", "전월세") == ["HOUSING"]
    assert categorize_policy("고용", "취업") == ["EMPLOYMENT"]


def test_categorize_policy_falls_back_to_etc() -> None:
    assert categorize_policy("알 수 없는 분류", "") == ["ETC"]


# ---------------------------------------------------------------------------
# Bug 3: benefits extraction
# ---------------------------------------------------------------------------


def test_extract_benefits_parses_valid_ai_response() -> None:
    client = _FakeSolarClient(
        {
            "benefits": [
                {
                    "benefit_type": "CASH",
                    "amount_type": "FIXED",
                    "min_amount": None,
                    "max_amount": 200000,
                    "payment_cycle": "MONTHLY",
                    "duration_months": 12,
                    "max_total_amount": 2400000,
                    "display_text": "월 최대 20만 원, 최대 12개월",
                }
            ]
        }
    )

    benefits = asyncio.run(
        extract_benefits(
            {"title": "청년 월세 지원", "raw_payload": {"plcySprtCn": "월 20만원 지원"}},
            client=client,
        )
    )

    assert len(benefits) == 1
    assert benefits[0] == ExtractedBenefit(
        benefit_type="CASH",
        amount_type="FIXED",
        min_amount=None,
        max_amount=200000,
        payment_cycle="MONTHLY",
        duration_months=12,
        max_total_amount=2400000,
        display_text="월 최대 20만 원, 최대 12개월",
    )


def test_extract_benefits_drops_invalid_benefit_type() -> None:
    client = _FakeSolarClient(
        {"benefits": [{"benefit_type": "NOT_A_REAL_TYPE", "amount_type": "FIXED"}]}
    )

    benefits = asyncio.run(extract_benefits({"raw_payload": {}}, client=client))

    assert benefits == []


def test_validate_benefit_payload_accepts_valid_benefit() -> None:
    result = validate_benefit_payload(
        {
            "benefits": [
                {
                    "benefit_type": "CASH",
                    "amount_type": "FIXED",
                    "min_amount": 10000,
                    "max_amount": 200000,
                }
            ]
        }
    )
    assert len(result) == 1


def test_validate_benefit_payload_rejects_unknown_benefit_type() -> None:
    with pytest.raises(ValueError, match="benefit_type"):
        validate_benefit_payload({"benefits": [{"benefit_type": "BOGUS", "amount_type": "FIXED"}]})


def test_validate_benefit_payload_rejects_min_greater_than_max() -> None:
    with pytest.raises(ValueError, match="min_amount"):
        validate_benefit_payload(
            {
                "benefits": [
                    {
                        "benefit_type": "CASH",
                        "amount_type": "FIXED",
                        "min_amount": 500000,
                        "max_amount": 100000,
                    }
                ]
            }
        )


# ---------------------------------------------------------------------------
# Integration: a fully-populated draft (all three bugs) passes approval
# validation together.
# ---------------------------------------------------------------------------


def test_validated_bundles_accepts_a_realistic_seed_draft() -> None:
    draft = _minimal_draft(
        conditions=[
            {
                "condition_key": "profile.age",
                "operator": "BETWEEN",
                "expected_value_json": {"min": 19, "max": 34},
                "is_required": True,
                "check_mode": "AUTO",
                "description": "만 19세 ~ 34세",
                "failure_message": "나이 조건을 확인하세요.",
            },
            {
                "condition_key": "profile.region_code",
                "operator": "IN",
                "expected_value_json": {"values": ["11"]},
                "is_required": True,
                "check_mode": "AUTO",
                "description": "거주지역 조건",
                "failure_message": "거주지역을 확인하세요.",
            },
        ],
        benefits=[
            {
                "benefit_type": "CASH",
                "amount_type": "FIXED",
                "min_amount": None,
                "max_amount": 200000,
                "payment_cycle": "MONTHLY",
                "duration_months": 12,
                "max_total_amount": 2400000,
                "display_text": "월 최대 20만 원",
            }
        ],
        category_codes=["HOUSING"],
    )

    bundles = _validated_bundles(draft)

    assert len(bundles) == 1
    bundle = bundles[0]
    assert bundle["category_codes"] == ["HOUSING"]
    assert bundle["benefits"][0]["benefit_type"] == "CASH"
    assert {c["condition_key"] for c in bundle["conditions"]} == {
        "profile.age",
        "profile.region_code",
    }


def test_validated_bundles_rejects_unknown_category_code() -> None:
    draft = _minimal_draft(category_codes=["NOT_A_REAL_CATEGORY"])

    with pytest.raises(SeedDraftError, match="category_code"):
        _validated_bundles(draft)


def test_validated_bundles_rejects_empty_category_codes() -> None:
    draft = _minimal_draft(category_codes=[])

    with pytest.raises(SeedDraftError, match="category_codes"):
        _validated_bundles(draft)
