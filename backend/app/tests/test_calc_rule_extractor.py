"""Tests for calc_rule_extractor.py: CalcType resolution adapter and the
per-type calculation_rule_json extraction (accept complete, reject partial).
"""

from __future__ import annotations

import asyncio

from app.models.policy import CalcType
from app.services.ai.calc_rule_extractor import (
    extract_calculation_rule,
    is_calculation_rule_complete,
    resolve_calc_type_for_codes,
)


class _FakeSolarClient:
    """Minimal double matching SolarClient.complete_json()'s signature."""

    def __init__(self, response: dict) -> None:
        self._response = response

    async def complete_json(self, system_prompt: str, user_content: str) -> dict:
        del system_prompt, user_content
        return self._response


class _RecordingSolarClient:
    """Captures the user_content it was called with, for asserting prompt contents."""

    def __init__(self, response: dict) -> None:
        self._response = response
        self.last_user_content: str | None = None

    async def complete_json(self, system_prompt: str, user_content: str) -> dict:
        del system_prompt
        self.last_user_content = user_content
        return self._response


class _ContextAwareSolarClient:
    """Returns a different response depending on which display_text was named in the
    [이 혜택 항목] hint - simulates the AI correctly disambiguating between multiple
    benefits described in the same policy text (reproduces the real "찐이 4기" bug
    scenario). Only looks at the hint section, not the full support_content_text
    (which always contains every benefit's wording regardless of which one is being
    asked about right now)."""

    def __init__(self, responses_by_marker: dict[str, dict]) -> None:
        self._responses_by_marker = responses_by_marker

    async def complete_json(self, system_prompt: str, user_content: str) -> dict:
        del system_prompt
        marker_start = user_content.find("[이 혜택 항목]")
        content_start = user_content.find("[지원 내용]")
        hint_section = (
            user_content[marker_start:content_start]
            if marker_start != -1 and content_start != -1
            else ""
        )
        for marker, response in self._responses_by_marker.items():
            if marker in hint_section:
                return response
        raise AssertionError(f"no marker matched in hint section: {hint_section!r}")


def _policy_payload(title: str, support_content: str) -> dict:
    return {"title": title, "raw_payload": {"plcyNm": title, "plcySprtCn": support_content}}


# ---------------------------------------------------------------------------
# resolve_calc_type_for_codes() - thin adapter over resolve_calc_type()
# ---------------------------------------------------------------------------


def test_resolve_calc_type_for_codes_direct_mapping() -> None:
    assert resolve_calc_type_for_codes("LOAN", []) is CalcType.LOAN_INTEREST
    assert resolve_calc_type_for_codes("SAVINGS", []) is CalcType.SAVINGS_ASSET
    assert resolve_calc_type_for_codes("TAX_REDUCTION", []) is CalcType.TAX_DEDUCTION


def test_resolve_calc_type_for_codes_cash_like_prefers_housing_then_employment() -> None:
    assert resolve_calc_type_for_codes("CASH", ["EMPLOYMENT", "HOUSING"]) is CalcType.HOUSING_RENT
    assert resolve_calc_type_for_codes("CASH", ["EMPLOYMENT"]) is CalcType.EMPLOYMENT_EDUCATION
    assert resolve_calc_type_for_codes("DISCOUNT", ["WELFARE"]) is CalcType.CASH_VOUCHER


def test_resolve_calc_type_for_codes_non_simulatable_returns_none() -> None:
    assert resolve_calc_type_for_codes("SERVICE", ["HOUSING"]) is None
    assert resolve_calc_type_for_codes("OTHER", []) is None


# ---------------------------------------------------------------------------
# extract_calculation_rule() - LOAN_INTEREST
# ---------------------------------------------------------------------------


def test_extract_calculation_rule_loan_interest_accepts_complete_response() -> None:
    client = _FakeSolarClient(
        {
            "policy_interest_rate_percent": 1.8,
            "interest_reduction_rate_percent": 2.2,
            "max_loan_amount": 200000000,
            "max_support_months": 24,
            "repayment_type": "BULLET",
        }
    )

    result = asyncio.run(
        extract_calculation_rule(
            _policy_payload("전세자금 대출이자 지원", "금리 1.8%, 최대 2억원, 24개월"),
            calc_type=CalcType.LOAN_INTEREST,
            client=client,
        )
    )

    assert result == {
        "type": "LOAN_INTEREST",
        "policy_interest_rate_percent": 1.8,
        "interest_reduction_rate_percent": 2.2,
        "max_loan_amount": 200000000,
        "max_support_months": 24,
        "repayment_type": "BULLET",
    }


def test_extract_calculation_rule_loan_interest_rejects_missing_required_field() -> None:
    client = _FakeSolarClient(
        {
            "policy_interest_rate_percent": 1.8,
            "interest_reduction_rate_percent": None,
            "max_loan_amount": None,
            "max_support_months": 24,
            "repayment_type": "BULLET",
        }
    )

    result = asyncio.run(
        extract_calculation_rule(
            _policy_payload("전세자금 대출이자 지원", "금리 1.8%만 언급, 한도는 불명확"),
            calc_type=CalcType.LOAN_INTEREST,
            client=client,
        )
    )

    assert result is None


# ---------------------------------------------------------------------------
# extract_calculation_rule() - SAVINGS_ASSET
# ---------------------------------------------------------------------------


def test_extract_calculation_rule_savings_asset_accepts_complete_response() -> None:
    client = _FakeSolarClient(
        {
            "government_match_rate_percent": 100,
            "monthly_max_support_amount": 100000,
            "maturity_months": 36,
            "base_interest_rate_percent": 4.5,
            "bonus_interest_rate_percent": None,
        }
    )

    result = asyncio.run(
        extract_calculation_rule(
            _policy_payload("청년내일저축계좌", "월 10만원 1:1 매칭, 3년 만기, 기본금리 4.5%"),
            calc_type=CalcType.SAVINGS_ASSET,
            client=client,
        )
    )

    assert result is not None
    assert result["type"] == "SAVINGS_ASSET"
    assert result["bonus_interest_rate_percent"] is None


# ---------------------------------------------------------------------------
# extract_calculation_rule() - CASH_VOUCHER (branches on amount_type)
# ---------------------------------------------------------------------------


def test_extract_calculation_rule_cash_voucher_fixed_branch() -> None:
    client = _FakeSolarClient(
        {
            "amount_type": "FIXED",
            "amount": 300000,
            "payment_cycle": "ONCE",
            "max_count": 1,
        }
    )

    result = asyncio.run(
        extract_calculation_rule(
            _policy_payload("청년 생활안정지원금", "1인 1회 30만원 지급"),
            calc_type=CalcType.CASH_VOUCHER,
            client=client,
        )
    )

    assert result == {
        "type": "CASH_VOUCHER",
        "amount_type": "FIXED",
        "amount": 300000,
        "payment_cycle": "ONCE",
        "max_count": 1,
    }


def test_extract_calculation_rule_cash_voucher_percentage_branch() -> None:
    client = _FakeSolarClient(
        {
            "amount_type": "PERCENTAGE",
            "rate_percent": 50,
            "cap_amount": 100000,
            "payment_cycle": "MONTHLY",
        }
    )

    result = asyncio.run(
        extract_calculation_rule(
            _policy_payload("교통비 환급 지원", "실비의 50%, 월 최대 10만원"),
            calc_type=CalcType.CASH_VOUCHER,
            client=client,
        )
    )

    assert result is not None
    assert result["amount_type"] == "PERCENTAGE"


def test_extract_calculation_rule_cash_voucher_rejects_when_amount_type_unresolved() -> None:
    client = _FakeSolarClient(
        {"amount_type": None, "amount": None, "payment_cycle": None, "max_count": None}
    )

    result = asyncio.run(
        extract_calculation_rule(
            _policy_payload("모호한 지원사업", "지원 방식이 불명확함"),
            calc_type=CalcType.CASH_VOUCHER,
            client=client,
        )
    )

    assert result is None


def test_extract_calculation_rule_cash_voucher_rejects_invalid_payment_cycle() -> None:
    client = _FakeSolarClient(
        {
            "amount_type": "FIXED",
            "amount": 300000,
            "payment_cycle": "NOT_A_REAL_CYCLE",
            "max_count": 1,
        }
    )

    result = asyncio.run(
        extract_calculation_rule(
            _policy_payload("청년 생활안정지원금", "1인 1회 30만원 지급"),
            calc_type=CalcType.CASH_VOUCHER,
            client=client,
        )
    )

    assert result is None


# ---------------------------------------------------------------------------
# extract_calculation_rule() - HOUSING_RENT
# ---------------------------------------------------------------------------


def test_extract_calculation_rule_housing_rent_accepts_complete_response() -> None:
    client = _FakeSolarClient(
        {
            "monthly_support_cap_amount": 200000,
            "support_months": 12,
            "deposit_limit_amount": None,
            "rent_limit_amount": None,
        }
    )

    result = asyncio.run(
        extract_calculation_rule(
            _policy_payload("청년 월세 지원", "월 최대 20만원, 최대 12개월"),
            calc_type=CalcType.HOUSING_RENT,
            client=client,
        )
    )

    assert result is not None
    assert result["monthly_support_cap_amount"] == 200000


# ---------------------------------------------------------------------------
# extract_calculation_rule() - EMPLOYMENT_EDUCATION (only support_months required)
# ---------------------------------------------------------------------------


def test_extract_calculation_rule_employment_education_accepts_support_months_only() -> None:
    client = _FakeSolarClient(
        {
            "training_allowance_amount": None,
            "education_subsidy_amount": None,
            "employment_success_bonus_amount": None,
            "support_months": 6,
        }
    )

    result = asyncio.run(
        extract_calculation_rule(
            _policy_payload("청년 취업 지원", "6개월간 지원, 금액은 별도 심사"),
            calc_type=CalcType.EMPLOYMENT_EDUCATION,
            client=client,
        )
    )

    assert result is not None
    assert result["support_months"] == 6


def test_extract_calculation_rule_employment_education_rejects_missing_support_months() -> None:
    client = _FakeSolarClient(
        {
            "training_allowance_amount": 300000,
            "education_subsidy_amount": None,
            "employment_success_bonus_amount": None,
            "support_months": None,
        }
    )

    result = asyncio.run(
        extract_calculation_rule(
            _policy_payload("청년 취업 지원", "훈련수당 30만원, 기간은 불명확"),
            calc_type=CalcType.EMPLOYMENT_EDUCATION,
            client=client,
        )
    )

    assert result is None


# ---------------------------------------------------------------------------
# extract_calculation_rule() - TAX_DEDUCTION
# ---------------------------------------------------------------------------


def test_extract_calculation_rule_tax_deduction_accepts_complete_response() -> None:
    client = _FakeSolarClient(
        {
            "deduction_rate_percent": 15,
            "max_deduction_amount": 3000000,
            "deduction_type": "TAX_CREDIT",
        }
    )

    result = asyncio.run(
        extract_calculation_rule(
            _policy_payload("청년 세액공제", "세액공제 15%, 한도 300만원"),
            calc_type=CalcType.TAX_DEDUCTION,
            client=client,
        )
    )

    assert result is not None
    assert result["deduction_type"] == "TAX_CREDIT"


def test_extract_calculation_rule_tax_deduction_rejects_invalid_deduction_type() -> None:
    client = _FakeSolarClient(
        {
            "deduction_rate_percent": 15,
            "max_deduction_amount": None,
            "deduction_type": "NOT_A_REAL_TYPE",
        }
    )

    result = asyncio.run(
        extract_calculation_rule(
            _policy_payload("청년 세액공제", "세액공제 15%"),
            calc_type=CalcType.TAX_DEDUCTION,
            client=client,
        )
    )

    assert result is None


# ---------------------------------------------------------------------------
# extract_calculation_rule() - benefit_display_text disambiguation
# ---------------------------------------------------------------------------


def test_extract_calculation_rule_includes_benefit_display_text_in_prompt() -> None:
    client = _RecordingSolarClient(
        {"amount_type": "FIXED", "amount": 10000, "payment_cycle": "MONTHLY", "max_count": 1}
    )

    asyncio.run(
        extract_calculation_rule(
            _policy_payload("찐이 4기 모집", "사전활동 수당 1만원 / 실비 3만원"),
            calc_type=CalcType.CASH_VOUCHER,
            client=client,
            benefit_display_text="사전활동 수당 1회 10,000원 지급(출석 체크 후 월별 지급)",
        )
    )

    assert client.last_user_content is not None
    assert "[이 혜택 항목]" in client.last_user_content
    assert "사전활동 수당 1회 10,000원" in client.last_user_content


def test_extract_calculation_rule_disambiguates_between_two_benefits_of_same_policy() -> None:
    """Reproduces the real bug: a policy with two CASH benefits in one support_content_text
    (사전활동 수당 10,000원 vs 축제기간 실비 30,000원) must extract the right amount for
    each, not silently reuse the first one for both."""

    client = _ContextAwareSolarClient(
        {
            "사전활동 수당": {
                "amount_type": "FIXED",
                "amount": 10000,
                "payment_cycle": "MONTHLY",
                "max_count": 1,
            },
            "축제기간 1일 실비": {
                "amount_type": "FIXED",
                "amount": 30000,
                "payment_cycle": "ONCE",
                "max_count": 1,
            },
        }
    )
    policy_payload = _policy_payload(
        "제23회 광주 추억의 충장축제 청년기획단 '찐이' 4기 모집",
        "◆ 사전활동 수당 1회 10,000원 지급(출석 체크 후 월별 지급)\n"
        "◆ 축제기간 1일 실비 30,000원 지급(교통비 포함 / 식사 별도 지원)",
    )

    first = asyncio.run(
        extract_calculation_rule(
            policy_payload,
            calc_type=CalcType.CASH_VOUCHER,
            client=client,
            benefit_display_text="사전활동 수당 1회 10,000원 지급(출석 체크 후 월별 지급)",
        )
    )
    second = asyncio.run(
        extract_calculation_rule(
            policy_payload,
            calc_type=CalcType.CASH_VOUCHER,
            client=client,
            benefit_display_text="축제기간 1일 실비 30,000원 지급(교통비 포함 / 식사 별도 지원)",
        )
    )

    assert first is not None and first["amount"] == 10000
    assert second is not None and second["amount"] == 30000


# ---------------------------------------------------------------------------
# is_calculation_rule_complete() direct checks (used by validate_benefit_payload too)
# ---------------------------------------------------------------------------


def test_is_calculation_rule_complete_true_for_full_loan_interest() -> None:
    assert is_calculation_rule_complete(
        CalcType.LOAN_INTEREST,
        {
            "policy_interest_rate_percent": 1.8,
            "max_loan_amount": 200000000,
            "max_support_months": 24,
            "repayment_type": "BULLET",
        },
    )


def test_is_calculation_rule_complete_false_for_partial_loan_interest() -> None:
    assert not is_calculation_rule_complete(
        CalcType.LOAN_INTEREST,
        {"policy_interest_rate_percent": 1.8},
    )
