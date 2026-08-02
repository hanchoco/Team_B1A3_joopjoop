"""
정책 원문 -> policy_benefits.calculation_rule_json 초안 추출

rule_extractor.py(자격조건), benefit_extractor.py(혜택 금액)와 동일한 구조를 따릅니다.
계약은 docs/simulator_calc_rules.md를 참고하세요.

CalcType 판정과 필드 채우기를 분리합니다:
  - CalcType 판정은 services/policy_engine/calc_type.py의 resolve_calc_type()이
    benefit_type + 카테고리만으로 100% 결정론적으로 계산합니다 - AI가 고를 필요가
    없습니다.
  - 이 모듈은 이미 정해진 CalcType 하나에 대한 필드만 AI로 채웁니다. 필수 필드를
    하나라도 못 채우면 전체를 None으로 버립니다(부분적으로 채운 JSON을 쓰지 않음).
"""

from types import SimpleNamespace

try:
    from .prompt_templates import (
        CALC_RULE_CASH_VOUCHER_PROMPT,
        CALC_RULE_EMPLOYMENT_EDUCATION_PROMPT,
        CALC_RULE_HOUSING_RENT_PROMPT,
        CALC_RULE_LOAN_INTEREST_PROMPT,
        CALC_RULE_SAVINGS_ASSET_PROMPT,
        CALC_RULE_TAX_DEDUCTION_PROMPT,
    )
    from .solar_client import SolarClient
except ImportError:
    from prompt_templates import (
        CALC_RULE_CASH_VOUCHER_PROMPT,
        CALC_RULE_EMPLOYMENT_EDUCATION_PROMPT,
        CALC_RULE_HOUSING_RENT_PROMPT,
        CALC_RULE_LOAN_INTEREST_PROMPT,
        CALC_RULE_SAVINGS_ASSET_PROMPT,
        CALC_RULE_TAX_DEDUCTION_PROMPT,
    )
    from solar_client import SolarClient

from app.models.policy import CalcType
from app.services.policy_engine.calc_type import resolve_calc_type

# ============================================================
# CalcType 판정 - resolve_calc_type()을 그대로 재사용 (직접 분기 금지, AGENTS.md 5번)
# ============================================================


def resolve_calc_type_for_codes(benefit_type: str, category_codes: list[str]) -> CalcType | None:
    """추출 파이프라인 시점(아직 DB에 쓰기 전)의 benefit_type 문자열과
    category_codes 리스트만으로 resolve_calc_type()을 그대로 호출하기 위한 어댑터.

    resolve_calc_type()은 구조적 타이핑(Protocol)이라 실제 ORM 객체 없이도
    SimpleNamespace로 최소 형태만 갖추면 그대로 통과한다.
    """

    fake_benefit = SimpleNamespace(benefit_type=benefit_type)
    fake_policy = SimpleNamespace(
        category_links=[
            SimpleNamespace(category=SimpleNamespace(code=code)) for code in category_codes
        ]
    )
    return resolve_calc_type(fake_benefit, fake_policy)


# ============================================================
# 타입별 프롬프트 / 필수 필드 레지스트리 (docs/simulator_calc_rules.md와 동일한 값)
# ============================================================

_PROMPTS: dict[CalcType, str] = {
    CalcType.LOAN_INTEREST: CALC_RULE_LOAN_INTEREST_PROMPT,
    CalcType.SAVINGS_ASSET: CALC_RULE_SAVINGS_ASSET_PROMPT,
    CalcType.CASH_VOUCHER: CALC_RULE_CASH_VOUCHER_PROMPT,
    CalcType.HOUSING_RENT: CALC_RULE_HOUSING_RENT_PROMPT,
    CalcType.EMPLOYMENT_EDUCATION: CALC_RULE_EMPLOYMENT_EDUCATION_PROMPT,
    CalcType.TAX_DEDUCTION: CALC_RULE_TAX_DEDUCTION_PROMPT,
}

_REQUIRED_FIELDS: dict[CalcType, tuple[str, ...]] = {
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
    CalcType.HOUSING_RENT: ("monthly_support_cap_amount", "support_months"),
    CalcType.TAX_DEDUCTION: ("deduction_rate_percent", "deduction_type"),
}

# EMPLOYMENT_EDUCATION은 아래 금액 필드 중 최소 하나가 있어야 완전한 것으로 본다
# (support_months만 있고 금액이 전부 비어있으면 불완전 - 0원짜리 시뮬레이션 방지).
# services/policy_engine/calc_type.py의 _EMPLOYMENT_EDUCATION_AMOUNT_FIELDS와
# 반드시 함께 갱신한다.
_EMPLOYMENT_EDUCATION_AMOUNT_FIELDS: tuple[str, ...] = (
    "training_allowance_amount",
    "education_subsidy_amount",
    "employment_success_bonus_amount",
)

ALLOWED_PAYMENT_CYCLES = {"ONCE", "MONTHLY", "YEARLY", "MATURITY", "VARIABLE"}
ALLOWED_DEDUCTION_TYPES = {"TAX_CREDIT", "INCOME_DEDUCTION"}


def is_calculation_rule_complete(calc_type: CalcType, result: dict) -> bool:
    """CASH_VOUCHER는 amount_type에 따라 필수 필드가 갈리므로 별도 처리한다.

    benefit_extractor.py의 validate_benefit_payload()도 이 함수를 그대로 재사용해서
    "타입별 필수 필드" 정의를 한 곳(_REQUIRED_FIELDS)에만 둔다.
    """

    if calc_type is CalcType.CASH_VOUCHER:
        amount_type = result.get("amount_type")
        if amount_type == "FIXED":
            required: tuple[str, ...] = ("amount", "payment_cycle", "max_count")
        elif amount_type == "PERCENTAGE":
            required = ("rate_percent", "cap_amount", "payment_cycle")
        else:
            return False
        if result.get("payment_cycle") not in ALLOWED_PAYMENT_CYCLES:
            return False
        return all(result.get(field) is not None for field in required)

    if calc_type is CalcType.TAX_DEDUCTION:
        if result.get("deduction_type") not in ALLOWED_DEDUCTION_TYPES:
            return False

    if calc_type is CalcType.EMPLOYMENT_EDUCATION:
        return any(result.get(field) is not None for field in _EMPLOYMENT_EDUCATION_AMOUNT_FIELDS)

    required = _REQUIRED_FIELDS.get(calc_type, ())
    return all(result.get(field) is not None for field in required)


# ============================================================
# 메인 함수 (실제 프로덕션 진입점)
# ============================================================


async def extract_calculation_rule(
    policy_payload: dict,
    *,
    calc_type: CalcType,
    client: SolarClient,
    benefit_display_text: str | None = None,
    other_benefit_display_texts: list[str] | None = None,
) -> dict | None:
    """calc_type 하나에 대한 calculation_rule_json 필드를 채운다.

    policy_payload: youth_policy_api.py가 만든 정규화된 정책 dict.
    calc_type: resolve_calc_type_for_codes()가 이미 결정한 타입(이 함수는 판정하지 않음).
    benefit_display_text: extract_benefits()가 이미 이 혜택 하나에 대해 뽑아둔 한 줄 요약.
        한 정책에 같은 CalcType의 혜택이 2개 이상 있을 때(예: "사전활동 수당 1만원"과
        "실비 3만원"이 같은 정책 원문에 함께 있는 경우), 이게 없으면 AI가 원문에서 아무
        숫자나 집어서 서로 다른 혜택끼리 값이 뒤섞이는 문제가 실제로 관측됐다.
    other_benefit_display_texts: 같은 정책의 나머지 혜택 항목들(자기 자신 제외)의 한 줄
        요약. 혜택이 2개일 때는 benefit_display_text 하나로 충분히 구분됐지만, 3개 이상일
        때(예: 구직촉진수당/참여수당/취업성공수당처럼 금액이 3개 이상 섞여 있는 정책)는
        "이 항목만 보라"는 긍정 힌트만으로는 부족해서 실제로 다른 항목의 숫자를 가져오는
        오류가 관측됐다 - "이 목록의 숫자는 쓰지 말라"는 명시적 제외 목록을 추가로 준다.
    반환: 필수 필드가 모두 채워졌으면 "type" 키를 포함한 dict, 하나라도 비어있으면 None.
    """

    prompt = _PROMPTS.get(calc_type)
    if prompt is None:
        return None

    raw = policy_payload.get("raw_payload") or policy_payload
    support_content = (
        raw.get("plcySprtCn", "") or policy_payload.get("support_content_text", "") or "(없음)"
    )
    other_benefits_block = ""
    if other_benefit_display_texts:
        other_lines = "\n".join(f"- {text}" for text in other_benefit_display_texts if text)
        if other_lines:
            other_benefits_block = f"""
같은 정책 안에 다음 다른 혜택 항목들도 있습니다. 이 항목들은 이번 추출 대상이
아닙니다 - 아래 목록에 나온 금액/기간은 절대 가져오지 마세요:
{other_lines}
"""
    benefit_hint = (
        f"""
[이 혜택 항목] {benefit_display_text}
{other_benefits_block}
지원 내용에 여러 혜택이 함께 설명되어 있다면, 위 [이 혜택 항목]에 해당하는 금액/조건만
사용하세요. 다른 혜택 항목의 숫자를 가져오지 마세요.
"""
        if benefit_display_text
        else ""
    )
    user_input = f"""
[정책명] {raw.get('plcyNm') or policy_payload.get('title')}
{benefit_hint}[지원 내용] {support_content}
"""
    result = await client.complete_json(prompt, user_input)
    if not isinstance(result, dict) or not is_calculation_rule_complete(calc_type, result):
        return None

    result = dict(result)
    result["type"] = calc_type.value
    return result
