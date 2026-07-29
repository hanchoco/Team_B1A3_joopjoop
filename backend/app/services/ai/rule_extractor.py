"""
정책 원문 -> 팀이 정한 DB 스키마에 맞춘 Rule 초안 추출

팀 DB 설계서 기준으로 데이터 생성

원칙:
  - 숫자로 이미 구조화된 조건(나이, 지역)은 AI 없이 그대로 매핑.
  - AI(Solar)는 자유 텍스트만 다룹니다: 서류 목록 파싱, 소득/추가조건 요약, 혜택 계산규칙 추정.
  - AI가 만든 결과는 전부 초안입니다.
"""

import json
from datetime import datetime

try:
    from .solar_client import client
    from .prompt_templates import EXTRACTOR_SYSTEM_PROMPT
except ImportError:
    # 독립 실행(python rule_extractor.py)일 때는 상대 import가 안 되니 이쪽으로
    from solar_client import client
    from prompt_templates import EXTRACTOR_SYSTEM_PROMPT

# ============================================================
# 코드 레지스트리 (DB.pdf 4장 / 6장 기준)
# ============================================================

# categories 테이블 초기 데이터와 동일해야 함
CATEGORY_CODES = ["HOUSING", "TRANSPORT", "FINANCE", "TAX", "EMPLOYMENT", "WELFARE", "PARTICIPATION", "ETC"]

# 온통청년 lclsfNm/mclsfNm(대/중분류 텍스트) -> category_code 키워드 매핑
# 1:1이 아니라 여러 카테고리에 해당할 수 있어서 리스트로 반환합니다.
# TODO: 이 매핑은 추정치입니다. 나경님과 실제 정책 몇 개로 대조 확인 필요.
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
INCOME_BAND_UPPER_BOUND = {  # 각 구간의 상한(%), ABOVE_150은 상한 없음
    "BELOW_50": 50, "BETWEEN_50_75": 75, "BETWEEN_75_100": 100,
    "BETWEEN_100_120": 120, "BETWEEN_120_150": 150, "ABOVE_150": None,
}

# ------------------------------------------------------------------
# AI가 만든 condition_key는 신뢰하지 않고 여기서 한 번 더 검증합니다.
# 실전 테스트에서 발견된 버그: (1) operator 값(MANUAL_CHECK)을 condition_key로 착각,
# (2) "profile." 접두사 누락, (3) 코드값 전체를 나열해서 사실상 무의미한 조건 생성.
# ------------------------------------------------------------------

ALLOWED_CONDITION_KEYS = {
    "profile.income_band_code", "profile.housing_type_code", "profile.household_type_code",
    "profile.employment_status_code", "profile.household_size",
    "employment.company_size", "employment.contract_type", "employment.tenure_months",
    "employment.insurance_enrolled", "employment.job_field",
}

# 프로필 속성이 아니라, 자동판정 없이 체크박스로만 노출하는 특수 키
# (참여제한/중복수혜 안내 등 - policy_documents와 같은 성격)
CHECKBOX_ONLY_CONDITION_KEYS = {"participation_limit"}

CODE_REGISTRY_VALUES = {
    "housing_type_code": {"OWNED", "JEONSE", "MONTHLY_RENT", "PUBLIC_RENTAL", "DORMITORY", "WITH_FAMILY", "OTHER"},
    "household_type_code": {"SINGLE", "COUPLE", "WITH_PARENTS", "SINGLE_PARENT", "MULTI_PERSON", "OTHER"},
    "employment_status_code": {"EMPLOYED", "SELF_EMPLOYED", "UNEMPLOYED", "JOB_SEEKER", "STUDENT", "ON_LEAVE", "OTHER"},
}


NO_RESTRICTION_PHRASES = ["제한 없음", "모든", "무관", "관계없이", "누구나", "가능(모든"]
ENUM_COVERAGE_DROP_THRESHOLD = 0.8  # 레지스트리의 80% 이상을 나열하면 "사실상 무제한"으로 간주

# 이 condition_key는 설명에 아래 키워드가 하나라도 있어야 인정 (엉뚱한 내용 끼워넣기 방지)
TOPIC_KEYWORDS = {
    "employment.insurance_enrolled": ["보험"],
}


def _topic_mismatch(condition_key: str, description: str) -> bool:
    keywords = TOPIC_KEYWORDS.get(condition_key)
    if not keywords:
        return False
    return not any(kw in (description or "") for kw in keywords)


def _normalize_expected_value(operator: str, expected_value):
    """조건의 expected_value 형태를 항상 순수 값/리스트로 통일.
    AI가 가끔 {"values": [...]} 또는 {"value": ...}로 감싸서 주는 경우가 있어 여기서 벗겨냅니다."""
    if operator in ("IN", "NOT_IN") and isinstance(expected_value, dict) and "values" in expected_value:
        return expected_value["values"]
    if operator in ("EQ", "NE") and isinstance(expected_value, dict) and "value" in expected_value:
        return expected_value["value"]
    return expected_value


def validate_conditions(raw_conditions: list) -> tuple:
    """AI가 뽑은 조건 목록을 검증해서 (정상 목록, 걸러진 목록)을 반환.

    같은 condition_key로 여러 조건이 쪼개져 들어온 경우, 그 값들을 전부 합쳐서
    레지스트리의 80% 이상을 덮는지(=사실상 전체 나열) 같이 확인합니다."""
    from collections import defaultdict

    # 먼저 값 형태부터 통일
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
                dropped += [{**c, "_drop_reason": f"코드값 {coverage:.0%} 나열 - 사실상 무제한"} for c in items]
                continue

        for c in items:
            desc = c.get("description") or ""
            if any(p in desc for p in NO_RESTRICTION_PHRASES):
                dropped.append({**c, "_drop_reason": "설명상 제한 없음으로 판단됨"})
                continue
            if _topic_mismatch(key, desc):
                dropped.append({**c, "_drop_reason": f"설명이 {key}의 의미와 안 맞음 (엉뚱한 키에 끼워넣은 것으로 추정)"})
                continue
            cleaned.append(c)

    return cleaned, dropped


def categorize_policy(lclsf_nm: str, mclsf_nm: str) -> list:
    """lclsfNm/mclsfNm 텍스트를 category_code 리스트로 변환. 못 찾으면 ETC."""
    text = f"{lclsf_nm or ''} {mclsf_nm or ''}"
    matched = [code for code, keywords in CATEGORY_KEYWORD_MAP.items() if any(kw in text for kw in keywords)]
    return matched or ["ETC"]


def income_threshold_to_bands(percent: float) -> list:
    """'중위소득 60% 이하' 같은 상한 퍼센트를 받아서, 해당될 수 있는 income_band들을 반환.
    구간 경계와 정확히 안 맞을 수 있어 넓게(포함 가능성 있는 구간까지) 잡습니다.
    check_mode가 항상 MANUAL이라 사람이 최종 확인하는 걸 전제로 합니다."""
    bands = [code for code in INCOME_BAND_ORDER if percent <= (INCOME_BAND_UPPER_BOUND[code] or 9999)]
    return bands or ["UNKNOWN"]


# ============================================================
# AI 추출 (자유텍스트 -> 구조화 초안). 프롬프트는 prompt_templates.py의
# EXTRACTOR_SYSTEM_PROMPT를 사용합니다.
# ============================================================

def ai_extract(raw: dict) -> dict:
    user_input = f"""
[정책명] {raw.get('plcyNm')}
[지원내용] {raw.get('plcySprtCn', '') or '(없음)'}
[추가 신청자격] {raw.get('addAplyQlfcCndCn', '') or '(없음)'}
[참여제한 대상] {raw.get('ptcpPrpTrgtCn', '') or '(없음)'}
[소득조건 상세] {raw.get('earnEtcCn', '') or '(없음)'}
[제출서류] {raw.get('sbmsnDcmntCn', '') or '(없음)'}
[사업기간 텍스트] {raw.get('bizPrdEtcCn', '') or '(없음)'}
"""
    response = client.chat.completions.create(
        model="solar-pro2",
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": EXTRACTOR_SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ],
    )
    return json.loads(response.choices[0].message.content)


ALWAYS_OPEN_KEYWORDS = ["연중", "상시"]


def resolve_application_period(raw: dict, ai_result: dict) -> dict:
    start_raw = (raw.get("bizPrdBgngYmd") or "").strip()
    end_raw = (raw.get("bizPrdEndYmd") or "").strip()
    etc = raw.get("bizPrdEtcCn", "") or ""

    def to_iso(yyyymmdd: str):
        try:
            return datetime.strptime(yyyymmdd, "%Y%m%d").strftime("%Y-%m-%d")
        except ValueError:
            return None

    if start_raw and end_raw:
        return {"start_date": to_iso(start_raw), "end_date": to_iso(end_raw), "is_ongoing": False}

    if any(kw in etc for kw in ALWAYS_OPEN_KEYWORDS):
        return {"start_date": None, "end_date": None, "is_ongoing": True}

    hint = ai_result.get("period_hint", {})
    if hint.get("start_date") or hint.get("end_date"):
        return {"start_date": hint.get("start_date"), "end_date": hint.get("end_date"), "is_ongoing": False}

    return {"start_date": None, "end_date": None, "is_ongoing": False}


# ============================================================
# 메인 함수
# ============================================================

def process_policy(raw: dict) -> dict:
    ai_result = ai_extract(raw)
    period = resolve_application_period(raw, ai_result)

    # ---------- policies ----------
    zip_codes = raw.get("zipCd", "").split(",") if raw.get("zipCd") else []
    policies_row = {
        "source": "ONTONG_YOUTH",
        "external_id": raw.get("plcyNo"),
        "title": raw.get("plcyNm"),
        "summary": raw.get("plcyExplnCn"),
        "description": raw.get("plcySprtCn"),
        "support_target_text": raw.get("addAplyQlfcCndCn") or None,   # API가 명확히 안 줌 -> 근사치
        "support_content_text": raw.get("plcySprtCn"),
        "application_method": raw.get("plcyAplyMthdCn") or None,
        "provider_name": raw.get("operInstCdNm") or raw.get("sprvsnInstCdNm") or None,
        "application_url": raw.get("aplyUrlAddr") or raw.get("refUrlAddr1") or None,
        "application_start_date": period["start_date"],
        "application_end_date": period["end_date"],
        "is_ongoing": period["is_ongoing"],
        "published_date": (raw.get("frstRegDt") or "")[:10] or None,
        "status": "DRAFT",  # A03 승인 후 Backend가 ACTIVE로 변경
        "raw_payload": raw,  # 원본 통째로 보관 (JSON 컬럼)
        "source_updated_at": raw.get("lastMdfcnDt") or None,
        "subcategory": raw.get("mclsfNm") or None,
        "region_scope": "LOCAL" if zip_codes else "NATIONAL",  # 근사치, 확정 아님
        "region_code": zip_codes[0] if zip_codes else None,
        "contact": raw.get("operInstPicNm") or raw.get("sprvsnInstPicNm") or None,
        "original_text": raw.get("plcySprtCn") or None,
        "is_active": True,
        # API가 아예 안 주는 값들 -> 변수명은 만들되 값은 비워둠
        "published_date_verified": None,
    }

    # ---------- policy_categories ----------
    category_codes = categorize_policy(raw.get("lclsfNm", ""), raw.get("mclsfNm", ""))
    policy_categories = [
        {"category_code": code, "is_primary": (i == 0)}
        for i, code in enumerate(category_codes)
    ]

    # ---------- policy_conditions ----------
    conditions = []

    # 나이 - AUTO (숫자 필드 직접 매핑, AI 없음)
    if raw.get("sprtTrgtMinAge") or raw.get("sprtTrgtMaxAge"):
        age_min = int(raw["sprtTrgtMinAge"]) if raw.get("sprtTrgtMinAge") else None
        age_max = int(raw["sprtTrgtMaxAge"]) if raw.get("sprtTrgtMaxAge") else None
        conditions.append({
            "condition_key": "profile.age",
            "operator": "BETWEEN",
            "expected_value_json": {"min": age_min, "max": age_max},
            "condition_group_no": 0,
            "is_required": raw.get("sprtTrgtAgeLmtYn") == "Y",
            "check_mode": "AUTO",
            "description": f"만 {age_min}세 ~ {age_max}세",
            "failure_message": f"이 정책은 만 {age_min}세~{age_max}세만 신청할 수 있습니다.",
        })

    # 지역 - AUTO
    if zip_codes:
        conditions.append({
            "condition_key": "profile.region_code",
            "operator": "IN",
            "expected_value_json": {"values": zip_codes},
            "condition_group_no": 0,
            "is_required": True,
            "check_mode": "AUTO",
            "description": "거주지역 조건",
            "failure_message": "거주지역이 이 정책의 지원 지역에 포함되지 않습니다.",
        })

    # 소득구간 - MANUAL (구간 경계 근사치라 사람 확인 필요)
    income_note = ai_result.get("income_note", {})
    if income_note.get("has_income_condition") and income_note.get("percent_threshold"):
        threshold = income_note["percent_threshold"]
        bands = income_threshold_to_bands(threshold)
        conditions.append({
            "condition_key": "profile.income_band_code",
            "operator": "IN",
            # percent_threshold를 같이 넘겨서, Policy Engine이 매칭 시점에
            # "경계에 걸친 구간만 확인필요, 나머지는 자동판정" 로직을 짤 수 있게 함
            "expected_value_json": {"values": bands, "percent_threshold": threshold},
            "condition_group_no": 0,
            "is_required": False,  # 근사치라 필수 조건으로 강제하지 않음
            "check_mode": "MANUAL",  # 기본값. Policy Engine이 경계 밖이면 AUTO처럼 취급 가능
            "description": income_note.get("summary", "소득조건 확인 필요"),
            "failure_message": "소득 조건은 정확한 확인이 필요합니다.",
        })

    # AI가 자유텍스트에서 뽑은 조건들 - 전부 MANUAL. 검증 통과한 것만 채택.
    valid_ai_conditions, dropped_ai_conditions = validate_conditions(ai_result.get("conditions", []))
    for c in valid_ai_conditions:
        conditions.append({
            "condition_key": c.get("condition_key"),
            "operator": c.get("operator", "MANUAL_CHECK"),
            "expected_value_json": c.get("expected_value"),
            "condition_group_no": 0,
            "is_required": c.get("is_required", False),
            "check_mode": "MANUAL",
            "description": c.get("description"),
            "failure_message": c.get("failure_message"),
        })

    # 참여제한/중복수혜 안내 - 판정 대상이 아니라 사용자가 스스로 체크하는 항목.
    # condition_key="participation_limit"는 프로필 속성이 아니라 이 용도 전용 키.
    # policy_documents(서류 체크리스트)와 같은 성격: 자동판정 없이 그냥 체크박스로 노출.
    for note in ai_result.get("participation_notes", []):
        conditions.append({
            "condition_key": "participation_limit",
            "operator": "MANUAL_CHECK",
            "expected_value_json": None,
            "condition_group_no": 0,
            "is_required": False,
            "check_mode": "MANUAL",
            "description": note.get("summary"),
            "failure_message": None,
        })

    for i, c in enumerate(conditions):
        c["sort_order"] = i + 1

    # ---------- policy_benefits ----------
    b = ai_result.get("benefit", {})
    policy_benefits = None
    if b:
        policy_benefits = {
            "benefit_type": b.get("benefit_type", "OTHER"),
            "amount_type": b.get("amount_type"),
            "min_amount": b.get("min_amount"),
            "max_amount": b.get("max_amount"),
            "payment_cycle": b.get("payment_cycle", "VARIABLE"),
            "duration_months": b.get("duration_months"),
            "max_total_amount": b.get("max_total_amount"),
            "calculation_rule_json": {
                "max_amount": b.get("max_amount"),
                "duration_months": b.get("duration_months"),
            },
            "display_text": b.get("display_text"),
        }

    # ---------- policy_documents ----------
    policy_documents = [
        {
            "document_code": None,  # Backend에서 채번
            "document_name": d.get("document_name"),
            "required_reason": d.get("required_reason"),
            "issuing_organization": d.get("issuing_organization"),
            "issuing_method": d.get("issuing_method"),
            "issuing_url": d.get("issuing_url"),
            "submission_format": d.get("submission_format"),
            "is_required": d.get("is_required", True),
            "display_order": i + 1,
        }
        for i, d in enumerate(ai_result.get("documents", []))
    ]

    return {
        "policies": policies_row,
        "policy_categories": policy_categories,
        "policy_benefits": policy_benefits,
        "policy_conditions": conditions,
        "policy_documents": policy_documents,
        "_dropped_conditions": dropped_ai_conditions,  # DB 컬럼 아님, QA/디버깅용
    }