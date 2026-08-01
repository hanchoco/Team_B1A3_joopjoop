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
from app.services.ai.category_classifier import classify_policy_category
from app.services.ai.rule_extractor import (
    ALLOWED_CONDITION_KEYS,
    extract_conditions,
    structured_income_condition,
    validate_condition_payload,
    validate_conditions,
)
from scripts.seed_policy_data import SeedDraftError, validated_bundles


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
# Bug 4: AI-extracted structured conditions were always forced to MANUAL,
# so matcher.evaluate_condition() could never auto-check anything besides
# the two hardcoded age/region conditions.
# ---------------------------------------------------------------------------


def test_validate_conditions_drops_ai_submitted_region_code() -> None:
    """Reproduces a real Solar response: told 'don't create region conditions',
    the AI still emitted profile.region_code with a made-up non-code value
    ('BUPYEONG') instead of a real zipCd - this must always be dropped so
    it can never overwrite/duplicate the hardcoded zipCd-based condition."""

    cleaned, dropped = validate_conditions(
        [
            {
                "condition_key": "profile.region_code",
                "operator": "EQ",
                "expected_value": "BUPYEONG",
                "is_required": True,
                "description": "부평구 주민등록 또는 생활권자",
            },
            {
                "condition_key": "employment.company_size_code",
                "operator": "IN",
                "expected_value": {"values": ["SMALL"]},
                "is_required": False,
                "description": "소기업 재직자",
            },
        ]
    )

    assert {c["condition_key"] for c in cleaned} == {"employment.company_size_code"}
    assert dropped[0]["condition_key"] == "profile.region_code"
    assert "하드코딩" in dropped[0]["_drop_reason"]


def test_validate_conditions_drops_ai_submitted_age() -> None:
    cleaned, dropped = validate_conditions(
        [
            {
                "condition_key": "profile.age",
                "operator": "BETWEEN",
                "expected_value": {"min": 20, "max": 30},
                "is_required": True,
                "description": "AI가 만든 나이 조건",
            },
        ]
    )

    assert cleaned == []
    assert dropped[0]["condition_key"] == "profile.age"


def test_extract_conditions_never_duplicates_region_code_from_ai() -> None:
    client = _FakeSolarClient(
        {
            "conditions": [
                {
                    "condition_key": "profile.region_code",
                    "operator": "EQ",
                    "expected_value": "BUPYEONG",
                    "is_required": True,
                    "description": "부평구 주민등록 또는 생활권자",
                    "failure_message": None,
                },
            ],
            "income_note": {"has_income_condition": False},
            "participation_notes": [],
        }
    )

    conditions = asyncio.run(
        extract_conditions(
            {"title": "부평 청년주간행사", "raw_payload": {"plcyNm": "부평 청년주간행사", "zipCd": "28237"}},
            client=client,
        )
    )

    region_conditions = [c for c in conditions if c.condition_key == "profile.region_code"]
    assert len(region_conditions) == 1
    assert region_conditions[0].expected_value_json == {"values": ["28237"]}


def test_extract_conditions_marks_structured_ai_condition_as_auto() -> None:
    client = _FakeSolarClient(
        {
            "conditions": [
                {
                    "condition_key": "employment.company_size_code",
                    "operator": "IN",
                    "expected_value": {"values": ["SMALL", "MICRO"]},
                    "is_required": True,
                    "description": "중소기업 재직자만 지원",
                    "failure_message": "중소기업 재직자만 신청할 수 있습니다.",
                }
            ],
            "income_note": {"has_income_condition": False},
            "participation_notes": [],
        }
    )

    conditions = asyncio.run(
        extract_conditions(
            {"title": "청년 취업 지원", "raw_payload": {"plcyNm": "청년 취업 지원"}},
            client=client,
        )
    )

    ai_condition = next(
        c for c in conditions if c.condition_key == "employment.company_size_code"
    )
    assert ai_condition.check_mode == "AUTO"


def test_extract_conditions_keeps_manual_check_operator_as_manual() -> None:
    client = _FakeSolarClient(
        {
            "conditions": [
                {
                    "condition_key": "housing.has_lease_contract",
                    "operator": "MANUAL_CHECK",
                    "expected_value": None,
                    "is_required": False,
                    "description": "임대차 계약서 확인 필요",
                    "failure_message": None,
                }
            ],
            "income_note": {"has_income_condition": False},
            "participation_notes": [],
        }
    )

    conditions = asyncio.run(
        extract_conditions(
            {"title": "청년 월세 지원", "raw_payload": {"plcyNm": "청년 월세 지원"}},
            client=client,
        )
    )

    ai_condition = next(
        c for c in conditions if c.condition_key == "housing.has_lease_contract"
    )
    assert ai_condition.check_mode == "MANUAL"


def test_extract_conditions_attaches_exception_note_to_matching_condition() -> None:
    """condition_exceptions should attach to age (hardcoded, not AI-authored)
    and to a normal AI-authored condition by condition_key, leaving unmatched
    conditions (e.g. region) untouched."""

    client = _FakeSolarClient(
        {
            "conditions": [
                {
                    "condition_key": "employment.company_size_code",
                    "operator": "IN",
                    "expected_value": {"values": ["SMALL", "MICRO"]},
                    "is_required": True,
                    "description": "중소기업 재직자만 지원",
                    "failure_message": "중소기업 재직자만 신청할 수 있습니다.",
                }
            ],
            "income_note": {"has_income_condition": False},
            "condition_exceptions": [
                {
                    "condition_key": "profile.age",
                    "summary": "군필자는 만 32세까지 인정됩니다.",
                    "evidence": "군 복무기간만큼 연장 가능",
                },
                {
                    "condition_key": "employment.company_size_code",
                    "summary": "중견기업도 매출 기준 충족 시 인정됩니다.",
                    "evidence": "중견기업 중 일부 예외 인정",
                },
            ],
            "participation_notes": [],
        }
    )

    conditions = asyncio.run(
        extract_conditions(
            {
                "title": "청년 취업 지원",
                "raw_payload": {
                    "plcyNm": "청년 취업 지원",
                    "sprtTrgtMinAge": "19",
                    "sprtTrgtMaxAge": "34",
                    "zipCd": "11,41",
                    "addAplyQlfcCndCn": (
                        "군 복무기간만큼 연장 가능. 중견기업 중 일부 예외 인정."
                    ),
                },
            },
            client=client,
        )
    )

    by_key = {c.condition_key: c for c in conditions}
    assert by_key["profile.age"].exception_note == "군필자는 만 32세까지 인정됩니다."
    assert (
        by_key["employment.company_size_code"].exception_note
        == "중견기업도 매출 기준 충족 시 인정됩니다."
    )
    assert by_key["profile.region_code"].exception_note is None


def test_extract_conditions_drops_exception_note_with_ungrounded_evidence() -> None:
    """Reproduces a real hallucination: the AI attached '군필자는 만 32세까지
    인정' to two policies whose source text never mentions military service at
    all - it echoed the illustrative example from our own prompt. evidence
    that doesn't literally appear in what the AI was shown must be dropped."""

    client = _FakeSolarClient(
        {
            "conditions": [],
            "income_note": {"has_income_condition": False},
            "condition_exceptions": [
                {
                    "condition_key": "profile.age",
                    "summary": "군필자는 만 32세까지 인정",
                    "evidence": "군필자는 만 32세까지 인정",
                },
            ],
            "participation_notes": [],
        }
    )

    conditions = asyncio.run(
        extract_conditions(
            {
                "title": "검단구 청년월세 지원사업",
                "raw_payload": {
                    "plcyNm": "검단구 청년월세 지원사업",
                    "sprtTrgtMinAge": "19",
                    "sprtTrgtMaxAge": "34",
                    "zipCd": "28290",
                    "addAplyQlfcCndCn": "",
                    "ptcpPrpTrgtCn": "",
                    "earnEtcCn": "",
                },
            },
            client=client,
        )
    )

    age_condition = next(c for c in conditions if c.condition_key == "profile.age")
    assert age_condition.exception_note is None


def test_extract_conditions_keeps_exception_note_grounded_in_this_policys_text() -> None:
    client = _FakeSolarClient(
        {
            "conditions": [],
            "income_note": {"has_income_condition": False},
            "condition_exceptions": [
                {
                    "condition_key": "profile.age",
                    "summary": "군복무 기간에 따라 최대 3세까지 연장 인정",
                    "evidence": "군복무 기간이 2년 이상인 경우 3세 연장",
                },
            ],
            "participation_notes": [],
        }
    )

    conditions = asyncio.run(
        extract_conditions(
            {
                "title": "영종구 청년월세 지원사업",
                "raw_payload": {
                    "plcyNm": "영종구 청년월세 지원사업",
                    "sprtTrgtMinAge": "35",
                    "sprtTrgtMaxAge": "39",
                    "zipCd": "28155",
                    "addAplyQlfcCndCn": "군복무 기간이 2년 이상인 경우 3세 연장(1983년생)",
                },
            },
            client=client,
        )
    )

    age_condition = next(c for c in conditions if c.condition_key == "profile.age")
    assert age_condition.exception_note == "군복무 기간에 따라 최대 3세까지 연장 인정"


def test_extract_conditions_drops_age_exception_about_a_different_topic() -> None:
    """Reproduces a second, subtler bug found right after the hallucination
    fix: evidence that IS genuinely present in the source text (so it passes
    grounding) can still be about the wrong topic - here an income-exemption
    clause ('원가구 소득·재산 미고려') happens to contain '30세 이상' and got
    attached to profile.age instead of being about income at all."""

    client = _FakeSolarClient(
        {
            "conditions": [],
            "income_note": {"has_income_condition": False},
            "condition_exceptions": [
                {
                    "condition_key": "profile.age",
                    "summary": (
                        "30세 이상, 혼인, 미혼부·모, 30세 미만 미혼 청년의 소득이 중위 "
                        "50% 이상으로 생계를 달리한다고 구청장이 인정하는 경우"
                    ),
                    "evidence": "원가구(부모님) 소득·재산 미고려 : 30세 이상",
                },
            ],
            "participation_notes": [],
        }
    )

    conditions = asyncio.run(
        extract_conditions(
            {
                "title": "서해구 청년월세지원",
                "raw_payload": {
                    "plcyNm": "서해구 청년월세지원",
                    "sprtTrgtMinAge": "35",
                    "sprtTrgtMaxAge": "39",
                    "zipCd": "28275",
                    "addAplyQlfcCndCn": "원가구(부모님) 소득·재산 미고려 : 30세 이상",
                },
            },
            client=client,
        )
    )

    age_condition = next(c for c in conditions if c.condition_key == "profile.age")
    assert age_condition.exception_note is None


def test_participation_note_description_is_labelled_as_exclusion() -> None:
    """ptcpPrpTrgtCn(참여제한 대상) items are always exclusion criteria, but a
    bare summary like '부모와 함께 거주하는 경우' doesn't say whether matching
    it helps or hurts. It must be prefixed so it reads unambiguously."""

    client = _FakeSolarClient(
        {
            "conditions": [],
            "income_note": {"has_income_condition": False},
            "participation_notes": [
                {
                    "summary": "부모와 함께 거주(원가구와 세대분리하지 않은 자)하는 경우",
                    "evidence": "부모와 함께 거주(원가구와 세대분리하지 않은 자)하는 경우",
                },
            ],
        }
    )

    conditions = asyncio.run(
        extract_conditions(
            {"title": "청년월세지원", "raw_payload": {"plcyNm": "청년월세지원"}},
            client=client,
        )
    )

    note = next(c for c in conditions if c.condition_key == "participation_limit")
    assert note.description == (
        "[신청 제외 대상] 부모와 함께 거주(원가구와 세대분리하지 않은 자)하는 경우"
    )


# ---------------------------------------------------------------------------
# Bug 5: earnMinAmt/earnMaxAmt (구조화된 소득 상한/하한) never read - only the
# free-text earnEtcCn was, which 온통청년 leaves empty for most policies even
# when earnMinAmt/earnMaxAmt carry a real number.
# ---------------------------------------------------------------------------


def test_structured_income_condition_reads_max_amount_only() -> None:
    condition = structured_income_condition(
        {"earnCndSeCd": "0043002", "earnMinAmt": "0", "earnMaxAmt": "3500"}
    )

    assert condition is not None
    assert condition["condition_key"] == "finance.annual_income_amount"
    assert condition["operator"] == "LTE"
    assert condition["expected_value_json"] == {"value": 35_000_000}
    assert condition["check_mode"] == "MANUAL"


def test_structured_income_condition_reads_min_and_max() -> None:
    condition = structured_income_condition({"earnMinAmt": "1000", "earnMaxAmt": "3500"})

    assert condition is not None
    assert condition["operator"] == "BETWEEN"
    assert condition["expected_value_json"] == {"min": 10_000_000, "max": 35_000_000}


def test_structured_income_condition_none_when_amounts_are_zero_or_absent() -> None:
    assert structured_income_condition({"earnMinAmt": "0", "earnMaxAmt": "0"}) is None
    assert structured_income_condition({}) is None


def test_extract_conditions_includes_structured_income_even_without_free_text() -> None:
    """Reproduces the real 온통청년 sample: earnEtcCn is empty but earnMaxAmt
    carries the actual income ceiling - the condition must still be created."""

    client = _FakeSolarClient(
        {"conditions": [], "income_note": {"has_income_condition": False}, "participation_notes": []}
    )

    conditions = asyncio.run(
        extract_conditions(
            {
                "title": "청년 자산형성지원",
                "raw_payload": {
                    "plcyNm": "청년 자산형성지원",
                    "sprtTrgtMinAge": "19",
                    "sprtTrgtMaxAge": "34",
                    "zipCd": "11",
                    "earnCndSeCd": "0043002",
                    "earnMinAmt": "0",
                    "earnMaxAmt": "3500",
                    "earnEtcCn": "",
                },
            },
            client=client,
        )
    )

    income_condition = next(
        c for c in conditions if c.condition_key == "finance.annual_income_amount"
    )
    assert income_condition.operator == "LTE"
    assert income_condition.expected_value_json == {"value": 35_000_000}


# ---------------------------------------------------------------------------
# Bug 2: category_codes generation
# ---------------------------------------------------------------------------


def test_classify_policy_category_keeps_valid_ai_codes_in_order() -> None:
    client = _FakeSolarClient({"category_codes": ["HOUSING", "FINANCE"]})

    codes = asyncio.run(
        classify_policy_category(
            {"title": "청년 월세 지원", "raw_payload": {"plcyNm": "청년 월세 지원"}},
            client=client,
        )
    )

    assert codes == ["HOUSING", "FINANCE"]


def test_classify_policy_category_drops_unknown_codes() -> None:
    client = _FakeSolarClient({"category_codes": ["HOUSING", "NOT_A_REAL_CATEGORY"]})

    codes = asyncio.run(classify_policy_category({"raw_payload": {}}, client=client))

    assert codes == ["HOUSING"]


def test_classify_policy_category_falls_back_to_etc() -> None:
    client = _FakeSolarClient({"category_codes": []})

    codes = asyncio.run(classify_policy_category({"raw_payload": {}}, client=client))

    assert codes == ["ETC"]


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


def test_validate_benefit_payload_accepts_null_calculation_rule_json() -> None:
    """Every already-approved draft before this feature existed has this field
    absent - it must always pass, or app boot breaks re-validating old drafts."""

    result = validate_benefit_payload(
        {
            "benefits": [
                {
                    "benefit_type": "SERVICE",
                    "amount_type": "VARIABLE",
                }
            ]
        }
    )
    assert result[0].calculation_rule_json is None


def test_validate_benefit_payload_accepts_complete_calculation_rule_json() -> None:
    result = validate_benefit_payload(
        {
            "benefits": [
                {
                    "benefit_type": "LOAN",
                    "amount_type": "FORMULA",
                    "calculation_rule_json": {
                        "type": "LOAN_INTEREST",
                        "policy_interest_rate_percent": 1.8,
                        "max_loan_amount": 200000000,
                        "max_support_months": 24,
                        "repayment_type": "BULLET",
                    },
                }
            ]
        }
    )
    assert result[0].calculation_rule_json["type"] == "LOAN_INTEREST"


def test_validate_benefit_payload_rejects_unsupported_calculation_rule_type() -> None:
    with pytest.raises(ValueError, match="calculation_rule_json.type"):
        validate_benefit_payload(
            {
                "benefits": [
                    {
                        "benefit_type": "CASH",
                        "amount_type": "FIXED",
                        "calculation_rule_json": {"type": "NOT_A_REAL_TYPE"},
                    }
                ]
            }
        )


def test_validate_benefit_payload_rejects_incomplete_calculation_rule_json() -> None:
    with pytest.raises(ValueError, match="missing required fields"):
        validate_benefit_payload(
            {
                "benefits": [
                    {
                        "benefit_type": "LOAN",
                        "amount_type": "FORMULA",
                        "calculation_rule_json": {
                            "type": "LOAN_INTEREST",
                            "policy_interest_rate_percent": 1.8,
                        },
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

    bundles = validated_bundles(draft)

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
        validated_bundles(draft)


def test_validated_bundles_rejects_empty_category_codes() -> None:
    draft = _minimal_draft(category_codes=[])

    with pytest.raises(SeedDraftError, match="category_codes"):
        validated_bundles(draft)


def test_validated_bundles_accepts_approved_status_with_expected_status_override() -> None:
    """policy_seed_loader loads already-approved, git-committed drafts - these
    have status='approved' (not 'pending_review'), so the default rejects
    them unless expected_status is overridden."""

    draft = _minimal_draft()
    draft["status"] = "approved"

    with pytest.raises(SeedDraftError, match="pending_review"):
        validated_bundles(draft)

    bundles = validated_bundles(draft, expected_status="approved")
    assert len(bundles) == 1
