"""
정책 원문 -> 팀이 정한 DB 스키마에 맞춘 Rule 초안 추출

팀 DB 설계서 기준으로 데이터 생성

원칙:
  - 숫자로 이미 구조화된 조건(나이, 지역)은 AI 없이 그대로 매핑.
  - AI(Solar)는 자유 텍스트만 다룹니다: 서류 목록 파싱, 소득/추가조건 요약, 혜택 계산규칙 추정.
  - AI가 만든 결과는 전부 초안입니다.
"""

from collections import defaultdict
from dataclasses import asdict, dataclass

try:
    from .prompt_templates import CONDITION_SYSTEM_PROMPT
    from .solar_client import SolarClient
except ImportError:
    from prompt_templates import CONDITION_SYSTEM_PROMPT
    from solar_client import SolarClient


# ============================================================
# 타입
# ============================================================


@dataclass
class ExtractedCondition:
    """policy_conditions 한 행을 담는 타입."""

    condition_key: str
    operator: str
    expected_value_json: object = None
    condition_group_no: int = 1
    is_required: bool = False
    check_mode: str = "MANUAL"
    description: str = None
    failure_message: str = None
    sort_order: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


# ============================================================
# 코드 레지스트리
# ============================================================

CATEGORY_KEYWORD_MAP = {
    "HOUSING": ["주거", "전월세", "주택"],
    "TRANSPORT": ["교통"],
    "FINANCE": ["금융", "자산형성", "대출", "저축"],
    "TAX": ["세금", "세제"],
    "EMPLOYMENT": ["일자리", "취업", "고용", "창업"],
    "WELFARE": ["복지", "생활지원", "돌봄"],
    "PARTICIPATION": ["참여", "청년참여", "네트워크"],
}

INCOME_BAND_ORDER = [
    "BELOW_50",
    "BETWEEN_50_75",
    "BETWEEN_75_100",
    "BETWEEN_100_120",
    "BETWEEN_120_150",
    "ABOVE_150",
]
INCOME_BAND_UPPER_BOUND = {
    "BELOW_50": 50,
    "BETWEEN_50_75": 75,
    "BETWEEN_75_100": 100,
    "BETWEEN_100_120": 120,
    "BETWEEN_120_150": 150,
    "ABOVE_150": None,
}

ALLOWED_CONDITION_KEYS = {
    "profile.age",
    "profile.region_code",
    "profile.income_band_code",
    "profile.housing_type_code",
    "profile.household_type_code",
    "profile.employment_status_code",
    "profile.household_size",
    "employment.company_size",
    "employment.contract_type",
    "employment.tenure_months",
    "employment.insurance_enrolled",
    "employment.job_field",
}
CHECKBOX_ONLY_CONDITION_KEYS = {"participation_limit"}

CODE_REGISTRY_VALUES = {
    "housing_type_code": {
        "OWNED",
        "JEONSE",
        "MONTHLY_RENT",
        "PUBLIC_RENTAL",
        "DORMITORY",
        "WITH_FAMILY",
        "OTHER",
    },
    "household_type_code": {
        "SINGLE",
        "COUPLE",
        "WITH_PARENTS",
        "SINGLE_PARENT",
        "MULTI_PERSON",
        "OTHER",
    },
    "employment_status_code": {
        "EMPLOYED",
        "SELF_EMPLOYED",
        "UNEMPLOYED",
        "JOB_SEEKER",
        "STUDENT",
        "ON_LEAVE",
        "OTHER",
    },
}

NO_RESTRICTION_PHRASES = ["제한 없음", "모든", "무관", "관계없이", "누구나", "가능(모든"]
ENUM_COVERAGE_DROP_THRESHOLD = 0.8

TOPIC_KEYWORDS = {
    "employment.insurance_enrolled": ["보험"],
}


def categorize_policy(lclsf_nm: str, mclsf_nm: str) -> list:
    text = f"{lclsf_nm or ''} {mclsf_nm or ''}"
    matched = [
        code
        for code, keywords in CATEGORY_KEYWORD_MAP.items()
        if any(kw in text for kw in keywords)
    ]
    return matched or ["ETC"]


def income_threshold_to_bands(percent: float) -> list:
    bands = [
        code for code in INCOME_BAND_ORDER if percent <= (INCOME_BAND_UPPER_BOUND[code] or 9999)
    ]
    return bands or ["UNKNOWN"]


def _normalize_expected_value(operator: str, expected_value):
    if (
        operator in ("IN", "NOT_IN")
        and isinstance(expected_value, dict)
        and "values" in expected_value
    ):
        return expected_value["values"]
    if operator in ("EQ", "NE") and isinstance(expected_value, dict) and "value" in expected_value:
        return expected_value["value"]
    return expected_value


def _topic_mismatch(condition_key: str, description: str) -> bool:
    keywords = TOPIC_KEYWORDS.get(condition_key)
    if not keywords:
        return False
    return not any(kw in (description or "") for kw in keywords)


def validate_conditions(raw_conditions: list) -> tuple:
    """AI가 뽑은 조건 목록을 검증해서 (정상 목록, 걸러진 목록)을 반환."""
    for c in raw_conditions:
        c["expected_value"] = _normalize_expected_value(c.get("operator"), c.get("expected_value"))

    grouped = defaultdict(list)
    for c in raw_conditions:
        grouped[c.get("condition_key")].append(c)

    cleaned, dropped = [], []
    for key, items in grouped.items():
        if key not in ALLOWED_CONDITION_KEYS:
            dropped += [{**c, "_drop_reason": f"허용되지 않은 condition_key: {key}"} for c in items]
            continue

        suffix = key.split(".")[-1]
        registry = CODE_REGISTRY_VALUES.get(suffix)
        if registry:
            collected = set()
            for c in items:
                vals = c.get("expected_value")
                if isinstance(vals, list):
                    collected.update(vals)
                elif isinstance(vals, str):
                    collected.add(vals)
            coverage = len(collected & registry) / len(registry)
            if coverage >= ENUM_COVERAGE_DROP_THRESHOLD:
                dropped += [
                    {**c, "_drop_reason": f"코드값 {coverage:.0%} 나열 - 사실상 무제한"}
                    for c in items
                ]
                continue

        for c in items:
            desc = c.get("description") or ""
            if any(p in desc for p in NO_RESTRICTION_PHRASES):
                dropped.append({**c, "_drop_reason": "설명상 제한 없음으로 판단됨"})
                continue
            if _topic_mismatch(key, desc):
                dropped.append({**c, "_drop_reason": f"설명이 {key}의 의미와 안 맞음"})
                continue
            cleaned.append(c)

    return cleaned, dropped


# ============================================================
# 메인 함수 (실제 프로덕션 진입점)
# ============================================================


async def extract_conditions(
    policy_payload: dict, *, client: SolarClient
) -> list[ExtractedCondition]:
    """
    policy_payload: youth_policy_api.py가 만든 정규화된 정책 dict.
    client: SolarClient 인스턴스 (seed_policy_data.py가 생성해서 넘겨줌)
    반환: ExtractedCondition 리스트
    """
    raw = policy_payload.get("raw_payload") or policy_payload

    user_input = f"""
[정책명] {raw.get('plcyNm') or policy_payload.get('title')}
[추가 신청자격] {raw.get('addAplyQlfcCndCn', '') or '(없음)'}
[참여제한 대상] {raw.get('ptcpPrpTrgtCn', '') or '(없음)'}
[소득조건 상세] {raw.get('earnEtcCn', '') or '(없음)'}
"""
    ai_result = await client.complete_json(CONDITION_SYSTEM_PROMPT, user_input)

    conditions = []

    # 나이 - AUTO (숫자 필드 직접 매핑, AI 없음)
    if raw.get("sprtTrgtMinAge") or raw.get("sprtTrgtMaxAge"):
        age_min = int(raw["sprtTrgtMinAge"]) if raw.get("sprtTrgtMinAge") else None
        age_max = int(raw["sprtTrgtMaxAge"]) if raw.get("sprtTrgtMaxAge") else None
        conditions.append(
            {
                "condition_key": "profile.age",
                "operator": "BETWEEN",
                "expected_value_json": {"min": age_min, "max": age_max},
                "condition_group_no": 1,
                "is_required": raw.get("sprtTrgtAgeLmtYn") == "Y",
                "check_mode": "AUTO",
                "description": f"만 {age_min}세 ~ {age_max}세",
                "failure_message": f"이 정책은 만 {age_min}세~{age_max}세만 신청할 수 있습니다.",
            }
        )

    # 지역 - AUTO
    zip_codes = raw.get("zipCd", "").split(",") if raw.get("zipCd") else []
    if zip_codes:
        conditions.append(
            {
                "condition_key": "profile.region_code",
                "operator": "IN",
                "expected_value_json": {"values": zip_codes},
                "condition_group_no": 1,
                "is_required": True,
                "check_mode": "AUTO",
                "description": "거주지역 조건",
                "failure_message": "거주지역이 이 정책의 지원 지역에 포함되지 않습니다.",
            }
        )

    # 소득구간 - MANUAL
    income_note = ai_result.get("income_note", {})
    if income_note.get("has_income_condition") and income_note.get("percent_threshold"):
        threshold = income_note["percent_threshold"]
        bands = income_threshold_to_bands(threshold)
        conditions.append(
            {
                "condition_key": "profile.income_band_code",
                "operator": "IN",
                "expected_value_json": {"values": bands, "percent_threshold": threshold},
                "condition_group_no": 1,
                "is_required": False,
                "check_mode": "MANUAL",
                "description": income_note.get("summary", "소득조건 확인 필요"),
                "failure_message": "소득 조건은 정확한 확인이 필요합니다.",
            }
        )

    # AI가 자유텍스트에서 뽑은 조건들 - 검증 통과한 것만
    valid_ai_conditions, dropped_ai_conditions = validate_conditions(
        ai_result.get("conditions", [])
    )
    for c in valid_ai_conditions:
        conditions.append(
            {
                "condition_key": c.get("condition_key"),
                "operator": c.get("operator", "MANUAL_CHECK"),
                "expected_value_json": c.get("expected_value"),
                "condition_group_no": 1,
                "is_required": c.get("is_required", False),
                "check_mode": "MANUAL",
                "description": c.get("description"),
                "failure_message": c.get("failure_message"),
            }
        )

    # 참여제한/중복수혜 안내 - 체크박스 전용
    for note in ai_result.get("participation_notes", []):
        conditions.append(
            {
                "condition_key": "participation_limit",
                "operator": "MANUAL_CHECK",
                "expected_value_json": None,
                "condition_group_no": 1,
                "is_required": False,
                "check_mode": "MANUAL",
                "description": note.get("summary"),
                "failure_message": None,
            }
        )

    for i, c in enumerate(conditions):
        c["sort_order"] = i + 1

    valid_fields = ExtractedCondition.__dataclass_fields__.keys()
    return [
        ExtractedCondition(**{k: v for k, v in c.items() if k in valid_fields}) for c in conditions
    ]


def create_condition_draft(extracted: ExtractedCondition) -> dict:
    """ExtractedCondition -> DB INSERT용 dict."""
    return extracted.to_dict()


def validate_condition_payload(payload: dict) -> list[ExtractedCondition]:
    """저장된 초안 JSON에서 다시 읽어들인 조건 목록을 검증하고
    ExtractedCondition 객체 리스트로 복원합니다.
    payload: {"conditions": [{...dict...}, ...]}
    """
    items = payload.get("conditions")
    if not isinstance(items, list):
        raise ValueError("conditions must be a list")

    valid_fields = ExtractedCondition.__dataclass_fields__.keys()
    result = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("each condition must be an object")
        if not item.get("condition_key") or not item.get("operator"):
            raise ValueError("condition missing condition_key/operator")
        if (
            item["condition_key"] not in ALLOWED_CONDITION_KEYS
            and item["condition_key"] not in CHECKBOX_ONLY_CONDITION_KEYS
        ):
            raise ValueError(f"unknown condition_key: {item['condition_key']}")
        result.append(ExtractedCondition(**{k: v for k, v in item.items() if k in valid_fields}))
    return result
