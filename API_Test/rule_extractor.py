"""
정책 원문 -> 팀이 정한 DB 스키마에 맞춘 Rule 초안 추출

팀 DB 설계서 기준으로 데이터 생성

원칙:
  - 숫자로 이미 구조화된 조건(나이, 지역)은 AI 없이 그대로 매핑.
  - AI(Solar)는 자유 텍스트만 다룹니다: 서류 목록 파싱, 소득/추가조건 요약, 혜택 계산규칙 추정.
  - AI가 만든 결과는 전부 초안입니다.
"""

import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.environ["UPSTAGE_API_KEY"],
    base_url="https://api.upstage.ai/v1",
)

# 온통청년 대분류(lclsfNm) -> 우리 category 값 매핑
# TODO: 실제 enum 값은 팀이랑 확정 필요, 일단 policies.category 예시(HOUSING/TRANSPORT 등)에 맞춰 추정
CATEGORY_MAP = {
    "주거": "HOUSING",
    "금융･복지･문화": "FINANCE",
    "일자리": "EMPLOYMENT",
    "참여･기반": "PARTICIPATION",
    "교육": "EDUCATION",
}


def map_category(lclsf_nm: str) -> str:
    return CATEGORY_MAP.get(lclsf_nm, "ETC")


AI_SYSTEM_PROMPT = """당신은 한국 청년 정책 데이터를 정리하는 도우미입니다.
아래 자유 텍스트를 읽고 3가지를 만드세요. 반드시 JSON으로만 답하세요.

1. income_note: 소득조건 텍스트 요약 (summary, evidence). 기계로 정확히 계산 불가능한
   경우가 많으니(예: "기준중위소득 60%이하") 판정하지 말고 요약만 하세요.
2. requirements: 제출서류 텍스트를 항목별로 쪼갠 리스트.
   각 항목: {"title": "서류명", "is_required": true/false, "description": "간단 설명"}
   원문에 "(필수)","(선택)" 표시가 있으면 그대로 반영하세요.

   서류 정보가 없는 경우, 아래 두 가지를 구분하세요:
   a) 원문이 "제출서류 없음", "해당없음"처럼 서류가 아예 필요 없다는 뜻이면
      -> requirements를 빈 배열([])로 두세요.
   b) 원문이 "붙임파일 확인", "첨부파일 참조"처럼 서류는 있지만 이 텍스트에
      구체적인 이름이 없는 경우 -> requirements에 아래처럼 안내용 항목 하나를 넣으세요.
      {"title": "첨부파일 확인 필요", "is_required": true,
       "description": "정확한 제출 서류 목록은 정책 공고문 첨부파일에서 확인해야 합니다."}
   빈 배열로 둘지 안내 항목을 넣을지 헷갈리면 b)를 선택하세요 (정보 누락보다 안내가 안전).
3. benefit_hint: 지원내용 텍스트에서 계산 방식을 추정.
   {"calculator_type": "FIXED_MONTHLY|FIXED_ONCE|RENT_SUPPORT|TRANSPORT_REFUND|SAVINGS_MATCH|TAX_ESTIMATE|CUSTOM",
    "monthly_cap": 숫자 또는 null, "duration_months": 숫자 또는 null,
    "confidence": 0~1, "evidence": "근거 문장"}
   확실하지 않으면 calculator_type을 "CUSTOM"으로 하고 confidence를 낮게 주세요.
4. period_hint: [사업기간 텍스트]에 실제 신청 시작일/종료일이 적혀있으면 YYYY-MM-DD로 뽑으세요.
   {"start_date": "2026-03-30" 또는 null, "end_date": "2026-05-29" 또는 null, "evidence": "근거 문장"}
   날짜를 특정할 수 없으면 둘 다 null로 하세요.

출력 형식:
{
  "income_note": {"summary": "...", "evidence": "..."},
  "requirements": [{"title": "...", "is_required": true, "description": "..."}],
  "benefit_hint": {"calculator_type": "...", "monthly_cap": 200000, "duration_months": 12, "confidence": 0.8, "evidence": "..."},
  "period_hint": {"start_date": "2026-03-30", "end_date": "2026-05-29", "evidence": "..."}
}
"""


def ai_interpret_free_text(plcy_sprt_cn: str, earn_etc_cn: str, sbmsn_dcmnt_cn: str, biz_prd_etc_cn: str = "") -> dict:
    user_input = f"""
[지원내용] {plcy_sprt_cn or '(없음)'}
[소득조건 상세] {earn_etc_cn or '(없음)'}
[제출서류] {sbmsn_dcmnt_cn or '(없음)'}
[사업기간 텍스트] {biz_prd_etc_cn or '(없음)'}
"""
    response = client.chat.completions.create(
        model="solar-pro2",
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": AI_SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ],
    )
    return json.loads(response.choices[0].message.content)


ALWAYS_OPEN_KEYWORDS = ["연중", "상시"]


def resolve_application_period(raw: dict, ai_result: dict) -> dict:
    """
    3가지 패턴을 순서대로 확인:
    1. bizPrdBgngYmd/EndYmd가 채워져 있으면 그대로 사용 (AI 필요 없음)
    2. bizPrdEtcCn에 "연중"/"상시" 키워드가 있으면 -> 마감일 없는 정책으로 표시 (AI 필요 없음)
    3. 그 외 -> AI가 bizPrdEtcCn에서 뽑아낸 period_hint 사용 (사람 검수 전제)
    """
    start_raw = raw.get("bizPrdBgngYmd", "").strip()
    end_raw = raw.get("bizPrdEndYmd", "").strip()
    etc = raw.get("bizPrdEtcCn", "") or ""

    if start_raw and end_raw:
        return {"start_date": start_raw, "end_date": end_raw, "is_ongoing": False, "source": "structured"}

    if any(kw in etc for kw in ALWAYS_OPEN_KEYWORDS):
        return {"start_date": None, "end_date": None, "is_ongoing": True, "source": "keyword_detected"}

    hint = ai_result.get("period_hint", {})
    if hint.get("start_date") or hint.get("end_date"):
        return {
            "start_date": hint.get("start_date"),
            "end_date": hint.get("end_date"),
            "is_ongoing": False,
            "source": "ai_parsed",  # A03에서 근거(evidence) 같이 보여주고 검수 필요
            "evidence": hint.get("evidence"),
        }

    return {"start_date": None, "end_date": None, "is_ongoing": False, "source": "unknown"}


def process_policy(raw: dict) -> dict:
    """
    온통청년 API 정책 원본(raw dict) 하나 -> 팀 DB 스키마에 맞춘 초안 dict.
    이 결과를 그대로 A03 검수 화면에 올려서, policies/policy_conditions/
    policy_requirements/policy_benefit_rules에 각각 INSERT하면 됩니다.
    """

    # ---------- policy_conditions: 숫자 조건은 AI 없이 직접 매핑 ----------
    conditions = []
    sort_order = 1

    if raw.get("sprtTrgtMinAge") or raw.get("sprtTrgtMaxAge"):
        conditions.append({
            "attribute_key": "age",  # user_profiles엔 없고 birth_date에서 계산되는 파생값
            "operator": "BETWEEN",
            "expected_value": {
                "min": int(raw["sprtTrgtMinAge"]) if raw.get("sprtTrgtMinAge") else None,
                "max": int(raw["sprtTrgtMaxAge"]) if raw.get("sprtTrgtMaxAge") else None,
            },
            "is_required": raw.get("sprtTrgtAgeLmtYn") == "Y",
            "description": f"만 {raw.get('sprtTrgtMinAge')}세 ~ {raw.get('sprtTrgtMaxAge')}세",
            "group_no": 0,
            "sort_order": sort_order,
        })
        sort_order += 1

    if raw.get("zipCd"):
        conditions.append({
            "attribute_key": "region_code",
            "operator": "IN",
            "expected_value": raw["zipCd"].split(","),
            "is_required": True,
            "description": "거주지역 조건",
            "group_no": 0,
            "sort_order": sort_order,
        })
        sort_order += 1

    # ---------- 자유 텍스트는 AI가 초안만 (사람 검수 전제) ----------
    ai_result = ai_interpret_free_text(
        plcy_sprt_cn=raw.get("plcySprtCn", ""),
        earn_etc_cn=raw.get("earnEtcCn", ""),
        sbmsn_dcmnt_cn=raw.get("sbmsnDcmntCn", ""),
        biz_prd_etc_cn=raw.get("bizPrdEtcCn", ""),
    )

    period = resolve_application_period(raw, ai_result)

    # 소득조건은 기계 판정이 어려운 경우가 많아 policy_conditions에 바로 넣지 않고
    # is_required=False + 낮은 신뢰도로 별도 표시. A03에서 사람이 최종 결정.
    if raw.get("earnEtcCn"):
        conditions.append({
            "attribute_key": "household_monthly_income",
            "operator": "EXISTS",  # 정확한 계산식 대신 "확인 필요" 상태로 표시
            "expected_value": None,
            "is_required": False,
            "description": ai_result.get("income_note", {}).get("summary", "소득조건 확인 필요"),
            "group_no": 0,
            "sort_order": sort_order,
            "needs_admin_review": True,  # A03 화면에서만 쓰는 임시 플래그, DB 컬럼 아님
        })
        sort_order += 1

    # ---------- policies 테이블 행 ----------
    policies_row = {
        "external_id": raw.get("plcyNo"),
        "source": "YOUTH_CENTER",
        "title": raw.get("plcyNm"),
        "category": map_category(raw.get("lclsfNm", "")),
        "subcategory": raw.get("mclsfNm"),
        "provider_name": raw.get("operInstCdNm") or raw.get("sprvsnInstCdNm"),
        "region_scope": "LOCAL" if raw.get("zipCd") else "NATIONAL",
        "region_code": (raw.get("zipCd", "").split(",")[0] if raw.get("zipCd") else None),
        "summary": raw.get("plcyExplnCn"),
        "description": raw.get("plcySprtCn"),
        "application_start_date": period["start_date"],
        "application_end_date": period["end_date"],
        "is_ongoing": period["is_ongoing"],  # 마감일 없는 정책(연중/상시) 표시용
        "application_method": raw.get("plcyAplyMthdCn"),
        "application_url": raw.get("aplyUrlAddr") or raw.get("refUrlAddr1"),
        "contact": raw.get("operInstPicNm") or raw.get("sprvsnInstPicNm"),
        "original_text": raw.get("plcySprtCn", ""),
        "status": "ACTIVE",
        "is_active": True,
    }

    # ---------- policy_requirements 테이블 행들 (AI가 서류 텍스트를 쪼갠 것) ----------
    requirements = [
        {
            "requirement_type": "DOCUMENT",
            "title": r.get("title"),
            "description": r.get("description"),
            "is_required": r.get("is_required", True),
            "sort_order": i + 1,
        }
        for i, r in enumerate(ai_result.get("requirements", []))
    ]

    # ---------- policy_benefit_rules (AI 추정치, 확신 낮으면 사람이 확인) ----------
    hint = ai_result.get("benefit_hint", {})
    benefit_rule = {
        "calculator_type": hint.get("calculator_type", "CUSTOM"),
        "params_json": {
            "monthly_cap": hint.get("monthly_cap"),
            "duration_months": hint.get("duration_months"),
        },
        "description": hint.get("evidence", ""),
        "confidence": hint.get("confidence", 0.0),  # DB 컬럼 아님, A03 화면 표시용
    }

    return {
        "policies": policies_row,
        "policy_conditions": conditions,
        "policy_requirements": requirements,
        "policy_benefit_rules": benefit_rule,
    }


if __name__ == "__main__":
    # 날짜 3가지 패턴을 각각 확인
    print("=" * 15, "케이스 A: 날짜 필드 직접 채워짐 (AI 안 씀)", "=" * 15)
    result_a = process_policy({
        "plcyNo": "20260724005400213303",
        "plcyNm": "(검단구) 인천시 청년월세 지원사업",
        "lclsfNm": "주거",
        "operInstCdNm": "인천광역시 검단구",
        "sprtTrgtMinAge": "35", "sprtTrgtMaxAge": "39", "sprtTrgtAgeLmtYn": "Y",
        "zipCd": "28290",
        "earnEtcCn": "소득 : (청년독립가구) 기준 중위소득 60%이하",
        "plcySprtCn": "지원금액 : 1인 월 20만원씩, 최대 24개월 월세 지원",
        "plcyAplyMthdCn": "복지로를 통한 온라인신청",
        "sbmsnDcmntCn": "월세지원 신청서(필수)\n소득·재산 신고서(필수)",
        "bizPrdBgngYmd": "20260330", "bizPrdEndYmd": "20260529", "bizPrdEtcCn": "",
    })
    print("application_start_date:", result_a["policies"]["application_start_date"])
    print("application_end_date:", result_a["policies"]["application_end_date"])
    print("is_ongoing:", result_a["policies"]["is_ongoing"])

    print("\n" + "=" * 15, "케이스 B: 연중/상시 (AI 안 씀, 마감일 없음)", "=" * 15)
    result_b = process_policy({
        "plcyNo": "TEST-B", "plcyNm": "청년 자금지원을 위한 햇살론유스 운영",
        "lclsfNm": "금융･복지･문화", "sprtTrgtMinAge": "19", "sprtTrgtMaxAge": "34",
        "sprtTrgtAgeLmtYn": "N", "zipCd": "",
        "plcySprtCn": "저소득 청년층을 위한 보증부대출",
        "bizPrdBgngYmd": "        ", "bizPrdEndYmd": "        ", "bizPrdEtcCn": "상시진행",
    })
    print("application_start_date:", result_b["policies"]["application_start_date"])
    print("is_ongoing:", result_b["policies"]["is_ongoing"])

    print("\n" + "=" * 15, "케이스 C: 날짜 없는데 텍스트에 실제 기간 있음 (AI가 파싱)", "=" * 15)
    result_c = process_policy({
        "plcyNo": "TEST-C", "plcyNm": "(서해구) 인천시 청년월세 지원사업",
        "lclsfNm": "주거", "sprtTrgtMinAge": "19", "sprtTrgtMaxAge": "34",
        "sprtTrgtAgeLmtYn": "Y", "zipCd": "28110",
        "plcySprtCn": "1인 월 20만원 월세 지원",
        "bizPrdBgngYmd": "", "bizPrdEndYmd": "",
        "bizPrdEtcCn": "* 신청기간 : 2026. 3.30. 09시 ~ 5.29. 18시",
    })
    print("application_start_date:", result_c["policies"]["application_start_date"])
    print("application_end_date:", result_c["policies"]["application_end_date"])
    print("is_ongoing:", result_c["policies"]["is_ongoing"])