"""Regression tests for the reviewed policy seed pipeline."""

import pytest

from app.services.ai.rule_extractor import validate_condition_payload
from scripts.seed_policy_data import (
    SeedDraftError,
    _validate_category_codes,
    category_codes_for_policy,
)


def test_generated_profile_conditions_are_accepted_for_approval() -> None:
    conditions = validate_condition_payload(
        {
            "conditions": [
                {
                    "condition_key": "profile.age",
                    "operator": "BETWEEN",
                    "expected_value_json": {"min": 19, "max": 34},
                },
                {
                    "condition_key": "profile.region_code",
                    "operator": "IN",
                    "expected_value_json": {"values": ["11"]},
                },
            ]
        }
    )

    assert [condition.condition_key for condition in conditions] == [
        "profile.age",
        "profile.region_code",
    ]


def test_seed_bundle_maps_source_classifications_to_categories() -> None:
    policy = {
        "raw_payload": {
            "lclsfNm": "금융･복지･문화",
            "mclsfNm": "취약계층 및 금융지원",
        }
    }

    assert category_codes_for_policy(policy) == ["FINANCE", "WELFARE"]


def test_seed_bundle_maps_participation_to_supported_category() -> None:
    policy = {
        "raw_payload": {
            "lclsfNm": "참여･기반",
            "mclsfNm": "청년참여",
        }
    }

    assert category_codes_for_policy(policy) == ["WELFARE"]


def test_seed_approval_preserves_only_supported_category_codes() -> None:
    assert _validate_category_codes(["FINANCE", "WELFARE", "FINANCE"]) == [
        "FINANCE",
        "WELFARE",
    ]

    with pytest.raises(SeedDraftError, match="unsupported category code"):
        _validate_category_codes(["PARTICIPATION"])
