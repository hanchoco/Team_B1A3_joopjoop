"""
정책 원문 -> 팀이 정한 DB 스키마에 맞춘 Rule 초안 추출

팀 DB 설계서 기준으로 데이터 생성

원칙:
  - 숫자로 이미 구조화된 조건(나이, 지역)은 AI 없이 그대로 매핑.
  - AI(Solar)는 자유 텍스트만 다룹니다: 서류 목록 파싱, 소득/추가조건 요약, 혜택 계산규칙 추정.
  - AI가 만든 결과는 전부 초안입니다.
"""

from dataclasses import dataclass, asdict, field
from collections import defaultdict

try:
    from .solar_client import SolarClient
    from .prompt_templates import CONDITION_SYSTEM_PROMPT
except ImportError:
    from solar_client import SolarClient
    from prompt_templates import CONDITION_SYSTEM_PROMPT


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
    exception_note: str = None
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

INCOME_BAND_ORDER = ["BELOW_50", "BETWEEN_50_75", "BETWEEN_75_100", "BETWEEN_100_120", "BETWEEN_120_150", "ABOVE_150"]
INCOME_BAND_UPPER_BOUND = {
    "BELOW_50": 50, "BETWEEN_50_75": 75, "BETWEEN_75_100": 100,
    "BETWEEN_100_120": 120, "BETWEEN_120_150": 150, "ABOVE_150": None,
}

ALLOWED_CONDITION_KEYS = {
    "profile.age", "profile.region_code",
    "profile.income_band_code", "profile.housing_type_code", "profile.household_type_code",
    "profile.employment_status_code", "profile.household_size",
    "employment.company_size_code", "employment.contract_type_code", "employment.tenure_months",
    "employment.insurance_enrolled", "employment.job_field_code",
    "housing.deposit_amount", "housing.monthly_rent_amount", "housing.is_household_head",
    "housing.has_lease_contract", "housing.residence_months",
    "finance.monthly_income_amount", "finance.annual_income_amount", "finance.total_asset_amount",
    "finance.total_debt_amount", "finance.fixed_monthly_expense_amount",
    "welfare.is_basic_livelihood_recipient", "welfare.is_near_poverty_household",
}
CHECKBOX_ONLY_CONDITION_KEYS = {"participation_limit"}

# profile.age/profile.region_code는 extract_conditions()의 하드코딩 경로(나이/지역 숫자
# 필드 직접 매핑)에서만 만들어져야 한다. AI가 이 키로 조건을 제출하면 - 프롬프트가
# "지역/나이는 만들지 마세요"라고 지시해도 가끔 무시하고 만들어내는데, 실제 지역코드가
# 아닌 값을 지어내 넣는 경우가 있었다(예: "BUPYEONG") - 무조건 드롭한다.
AI_FORBIDDEN_CONDITION_KEYS = {"profile.age", "profile.region_code"}

CODE_REGISTRY_VALUES = {
    "housing_type_code": {"OWNED", "JEONSE", "MONTHLY_RENT", "PUBLIC_RENTAL", "DORMITORY", "WITH_FAMILY", "OTHER"},
    "household_type_code": {"SINGLE", "COUPLE", "WITH_PARENTS", "SINGLE_PARENT", "MULTI_PERSON", "OTHER"},
    "employment_status_code": {"EMPLOYED", "SELF_EMPLOYED", "UNEMPLOYED", "JOB_SEEKER", "STUDENT", "ON_LEAVE", "OTHER"},
    "company_size_code": {"MICRO", "SMALL", "MEDIUM", "LARGE", "PUBLIC", "UNKNOWN"},
    "contract_type_code": {
        "PERMANENT", "FIXED_TERM", "DISPATCHED", "FREELANCER", "DAILY", "UNKNOWN",
    },
    "job_field_code": {
        "IT", "MARKETING", "DESIGN", "SALES", "MANUFACTURING",
        "SERVICE", "EDUCATION", "MEDICAL", "ADMIN", "OTHER",
    },
}

NO_RESTRICTION_PHRASES = ["제한 없음", "모든", "무관", "관계없이", "누구나", "가능(모든"]
ENUM_COVERAGE_DROP_THRESHOLD = 0.8

# operator가 MANUAL_CHECK가 아니면 matcher.evaluate_rule()이 자동 판정할 수 있으므로
# AUTO로 저장한다. condition_key는 이미 validate_conditions()에서 ALLOWED_CONDITION_KEYS로
# 걸러졌고, ALLOWED_CONDITION_KEYS는 전부 policy_engine.rules의 자동판정 레지스트리에 등록돼
# 있다. 값 파싱이 잘못돼도 matcher.evaluate_condition()이 NEEDS_REVIEW로 안전하게 낮춘다.
AUTO_EVALUABLE_OPERATORS = {
    "EQ", "NE", "IN", "NOT_IN", "GT", "GTE", "LT", "LTE", "BETWEEN",
    "CONTAINS_ANY", "CONTAINS_ALL", "EXISTS",
}

TOPIC_KEYWORDS = {
    "employment.insurance_enrolled": ["보험"],
    # profile.age 예외조항은 실제 사례상 거의 항상 군복무 연장 패턴이다. "원가구 소득
    # 미고려" 같은 다른 주제의 문장(우연히 "OO세 이상"이 포함됨)이 나이 조건에 잘못
    # 붙는 사고가 있었다 - 이 키워드가 없으면 evidence가 원문에 있어도 버린다.
    "profile.age": ["군복무", "군필", "제대", "복무"],
}


def categorize_policy(lclsf_nm: str, mclsf_nm: str) -> list:
    text = f"{lclsf_nm or ''} {mclsf_nm or ''}"
    matched = [code for code, keywords in CATEGORY_KEYWORD_MAP.items() if any(kw in text for kw in keywords)]
    return matched or ["ETC"]


def income_threshold_to_bands(percent: float) -> list:
    bands = [code for code in INCOME_BAND_ORDER if percent <= (INCOME_BAND_UPPER_BOUND[code] or 9999)]
    return bands or ["UNKNOWN"]


def _parse_positive_amount(value: object) -> int | None:
    """Parse earnMinAmt/earnMaxAmt into a positive int, or None if absent/zero.

    ``0``/``"0"``/blank means "해당 없음" in this API, not a real zero cap.
    """
    try:
        amount = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return amount if amount > 0 else None


def _format_manwon(amount: int) -> str:
    return f"{amount:,}만원"


def structured_income_condition(raw: dict) -> dict | None:
    """Map raw 온통청년 income fields (earnMinAmt/earnMaxAmt) directly - no AI.

    earnEtcCn(자유서술)이 비어 있어도 이 필드들엔 실제 소득 상한/하한이 숫자로
    들어있는 경우가 있다(예: 자산형성지원류 정책). check_mode는 AUTO로 두지 않는다 -
    금액 단위(만원 가정)를 API 문서로 확정할 수 없어서, 사람이 승인 전에 확인하도록
    기존 income_note 조건과 동일하게 MANUAL로 둔다.
    """
    min_amt = _parse_positive_amount(raw.get("earnMinAmt"))
    max_amt = _parse_positive_amount(raw.get("earnMaxAmt"))
    if min_amt is None and max_amt is None:
        return None

    if min_amt is not None and max_amt is not None:
        operator = "BETWEEN"
        expected_value_json = {"min": min_amt * 10000, "max": max_amt * 10000}
        description = f"연 소득 {_format_manwon(min_amt)} ~ {_format_manwon(max_amt)} (단위 확인 필요)"
    elif max_amt is not None:
        operator = "LTE"
        expected_value_json = {"value": max_amt * 10000}
        description = f"연 소득 {_format_manwon(max_amt)} 이하 (단위 확인 필요)"
    else:
        operator = "GTE"
        expected_value_json = {"value": min_amt * 10000}
        description = f"연 소득 {_format_manwon(min_amt)} 이상 (단위 확인 필요)"

    return {
        "condition_key": "finance.annual_income_amount",
        "operator": operator,
        "expected_value_json": expected_value_json,
        "condition_group_no": 1,
        "is_required": False,
        "check_mode": "MANUAL",
        "description": description,
        "failure_message": "소득 조건은 정확한 확인이 필요합니다.",
    }


def _normalize_expected_value(operator: str, expected_value):
    if operator in ("IN", "NOT_IN") and isinstance(expected_value, dict) and "values" in expected_value:
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
        if key in AI_FORBIDDEN_CONDITION_KEYS:
            dropped += [
                {**c, "_drop_reason": f"{key}는 하드코딩 경로 전용 - AI 제출은 항상 거부"}
                for c in items
            ]
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
                dropped += [{**c, "_drop_reason": f"코드값 {coverage:.0%} 나열 - 사실상 무제한"} for c in items]
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


def _normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def _extract_exception_notes(ai_result: dict, source_text: str) -> dict:
    """condition_exceptions를 {condition_key: 예외조항 요약} 딕셔너리로 정리.

    실제로 겪은 사고 두 가지:
    1. 프롬프트가 "원문에 근거 없으면 만들지 마세요"라고 지시해도, AI가 "청년월세
       정책엔 보통 군필자 연장이 있다"는 일반 지식으로 원문에 전혀 없는 예외조항을
       지어낸 적이 있다(검단구/서해구 정책에 "군필자는 만 32세까지 인정" 삽입, 두 정책
       원문 어디에도 군복무 언급 없음) - evidence가 실제로 AI에게 보여준 원문
       (source_text)에 포함될 때만 채택해서 막는다.
    2. evidence가 원문에 실제로 있어도(그래서 1번 검증은 통과해도) 엉뚱한 조건에 잘못
       붙는 경우가 있다(원가구 소득 미고려 조건 문장이 우연히 "OO세 이상"을 포함한다는
       이유로 profile.age에 붙음) - TOPIC_KEYWORDS로 조건 키와 evidence의 주제가
       맞는지도 확인한다.
    """
    source_normalized = _normalize_whitespace(source_text)
    notes = {}
    for item in ai_result.get("condition_exceptions", []) or []:
        key = item.get("condition_key")
        summary = item.get("summary")
        evidence = item.get("evidence")
        if key not in ALLOWED_CONDITION_KEYS:
            continue
        if not isinstance(summary, str) or not summary.strip():
            continue
        if not isinstance(evidence, str) or not evidence.strip():
            continue
        if _normalize_whitespace(evidence) not in source_normalized:
            continue
        if _topic_mismatch(key, evidence):
            continue
        notes[key] = summary.strip()
    return notes


# ============================================================
# 메인 함수 (실제 프로덕션 진입점)
# ============================================================

async def extract_conditions(policy_payload: dict, *, client: SolarClient) -> list[ExtractedCondition]:
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
        conditions.append({
            "condition_key": "profile.age",
            "operator": "BETWEEN",
            "expected_value_json": {"min": age_min, "max": age_max},
            "condition_group_no": 1,
            "is_required": raw.get("sprtTrgtAgeLmtYn") == "Y",
            "check_mode": "AUTO",
            "description": f"만 {age_min}세 ~ {age_max}세",
            "failure_message": f"이 정책은 만 {age_min}세~{age_max}세만 신청할 수 있습니다.",
        })

    # 지역 - AUTO
    zip_codes = raw.get("zipCd", "").split(",") if raw.get("zipCd") else []
    if zip_codes:
        conditions.append({
            "condition_key": "profile.region_code",
            "operator": "IN",
            "expected_value_json": {"values": zip_codes},
            "condition_group_no": 1,
            "is_required": True,
            "check_mode": "AUTO",
            "description": "거주지역 조건",
            "failure_message": "거주지역이 이 정책의 지원 지역에 포함되지 않습니다.",
        })

    # 소득구간 - MANUAL
    income_note = ai_result.get("income_note", {})
    if income_note.get("has_income_condition") and income_note.get("percent_threshold"):
        threshold = income_note["percent_threshold"]
        bands = income_threshold_to_bands(threshold)
        conditions.append({
            "condition_key": "profile.income_band_code",
            "operator": "IN",
            "expected_value_json": {"values": bands, "percent_threshold": threshold},
            "condition_group_no": 1,
            "is_required": False,
            "check_mode": "MANUAL",
            "description": income_note.get("summary", "소득조건 확인 필요"),
            "failure_message": "소득 조건은 정확한 확인이 필요합니다.",
        })

    # 소득 상한/하한 - earnMinAmt/earnMaxAmt 숫자 필드 직접 매핑 (AI 없음, MANUAL)
    # earnEtcCn(자유서술)이 비어 있어도 이 필드들엔 실제 값이 들어있는 경우가 있다.
    structured_income = structured_income_condition(raw)
    if structured_income:
        conditions.append(structured_income)

    # AI가 자유텍스트에서 뽑은 조건들 - 검증 통과한 것만
    valid_ai_conditions, dropped_ai_conditions = validate_conditions(ai_result.get("conditions", []))
    for c in valid_ai_conditions:
        operator = c.get("operator", "MANUAL_CHECK")
        conditions.append({
            "condition_key": c.get("condition_key"),
            "operator": operator,
            "expected_value_json": c.get("expected_value"),
            "condition_group_no": 1,
            "is_required": c.get("is_required", False),
            "check_mode": "AUTO" if operator in AUTO_EVALUABLE_OPERATORS else "MANUAL",
            "description": c.get("description"),
            "failure_message": c.get("failure_message"),
        })

    # 참여제한/중복수혜 안내 - 체크박스 전용
    # ptcpPrpTrgtCn(참여제한 대상) 원문 자체가 "해당하면 제외"라는 의미인데, summary만
    # 그대로 보여주면 "해당하면 되는 건지 안 되는 건지" 구분이 안 된다는 지적을 받아
    # 항상 "제외 대상" 라벨을 붙여 명확히 한다.
    for note in ai_result.get("participation_notes", []):
        conditions.append({
            "condition_key": "participation_limit",
            "operator": "MANUAL_CHECK",
            "expected_value_json": None,
            "condition_group_no": 1,
            "is_required": False,
            "check_mode": "MANUAL",
            "description": f"[신청 제외 대상] {note.get('summary')}",
            "failure_message": None,
        })

    # 조건별 예외조항 - 나이/지역/소득/AI 조건 전부 condition_key로 일괄 매칭
    exception_notes = _extract_exception_notes(ai_result, user_input)
    for c in conditions:
        note = exception_notes.get(c.get("condition_key"))
        if note:
            c["exception_note"] = note

    for i, c in enumerate(conditions):
        c["sort_order"] = i + 1

    valid_fields = ExtractedCondition.__dataclass_fields__.keys()
    return [ExtractedCondition(**{k: v for k, v in c.items() if k in valid_fields}) for c in conditions]


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
        if (item["condition_key"] not in ALLOWED_CONDITION_KEYS
                and item["condition_key"] not in CHECKBOX_ONLY_CONDITION_KEYS):
            raise ValueError(f"unknown condition_key: {item['condition_key']}")
        result.append(ExtractedCondition(**{k: v for k, v in item.items() if k in valid_fields}))
    return result