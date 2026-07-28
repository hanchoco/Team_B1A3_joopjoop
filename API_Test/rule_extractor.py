"""
A02. 정책 원문 -> Rule 초안 추출

Policy Engine(3번) 팀원과 맞춘 스키마를 그대로 반영했습니다.
반드시 confidence + evidence(원문 근거 문장)를 같이 뽑아야
A03 검수 화면에서 사람이 검증할 수 있습니다.

주의: 이 모듈은 '초안'만 만듭니다. 실제 자격 판정/금액 계산은
Rule DB에 반영된 뒤 Policy Engine의 Matching Engine이 담당합니다.
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

"""
A02. 정책 원문 -> Rule 초안 추출 (온통청년 실제 API 응답 기준으로 재설계)

핵심 발견: 온통청년 API는 나이/지역/소득범위를 이미 구조화된 필드로 줍니다.
  - sprtTrgtMinAge / sprtTrgtMaxAge  -> 나이, AI 추출 불필요
  - zipCd                            -> 지역(법정동코드), AI 추출 불필요
  - earnMinAmt / earnMaxAmt          -> 소득 범위(대략), AI 추출 불필요

AI(Solar)가 실제로 필요한 곳은 자유 텍스트로만 존재하는 3개 필드뿐입니다.
  - earnEtcCn          : 소득조건 상세 텍스트 (예: "청년독립가구 기준중위소득 60%이하")
  - addAplyQlfcCndCn   : 추가 신청자격 조건 텍스트
  - ptcpPrpTrgtCn      : 참여제한 대상 텍스트 (다른 정책과의 중복수혜 제한이 여기 들어있는 경우가 많음)

주의: mrgSttsCd, earnCndSeCd 같은 `~Cd`로 끝나는 필드는 코드값이라
별도 코드표(API코드정보.xlsx)로 디코딩해야 의미를 알 수 있습니다. 이 모듈에서는 다루지 않습니다.
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

SYSTEM_PROMPT = """당신은 한국 청년 정책의 자유 서술형 조건 텍스트를 정리하는 도우미입니다.
아래 3개 텍스트만 입력으로 받습니다. 이미 숫자로 정리된 나이/지역/소득범위는 신경쓰지 마세요.

규칙:
1. 원문에 명시된 내용만 정리하세요. 없는 내용을 만들어내지 마세요.
2. 각 항목마다 summary(한 문장 요약)와 evidence(원문에서 그대로 인용한 근거 구절)를 반드시 포함하세요.
3. ptcpPrpTrgtCn(참여제한 대상)에 "다른 정책/사업 수혜자 제외" 같은 내용이 있으면
   has_exclusion_clause를 true로, 없으면 false로 표시하세요.
4. 반드시 JSON 형식으로만 답하세요. 다른 설명 문장을 붙이지 마세요.

출력 형식 예시:
{
  "income_detail": {"summary": "청년독립가구는 중위소득 60% 이하", "evidence": "..."},
  "extra_conditions": {"summary": "...", "evidence": "..."},
  "participation_limit": {"summary": "...", "evidence": "...", "has_exclusion_clause": true}
}
"""


def extract_free_text_conditions(earn_etc_cn: str, add_aply_qlfc_cnd_cn: str, ptcp_prp_trgt_cn: str) -> dict:
    """자유 텍스트 3개 필드만 Solar에게 정리를 맡깁니다."""
    user_input = f"""
[소득조건 상세] {earn_etc_cn or '(없음)'}
[추가 신청자격 조건] {add_aply_qlfc_cnd_cn or '(없음)'}
[참여제한 대상] {ptcp_prp_trgt_cn or '(없음)'}
"""
    response = client.chat.completions.create(
        model="solar-pro2",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ],
    )
    return json.loads(response.choices[0].message.content)


def process_policy(raw: dict) -> dict:
    """
    온통청년 API가 준 정책 하나(raw dict)를 받아서,
    구조화된 필드는 그대로 통과시키고 자유 텍스트만 AI로 정리한 최종 Rule 초안을 만듭니다.
    이 결과가 A03 검수 화면에 올라갑니다.
    """
    ai_result = extract_free_text_conditions(
        earn_etc_cn=raw.get("earnEtcCn", ""),
        add_aply_qlfc_cnd_cn=raw.get("addAplyQlfcCndCn", ""),
        ptcp_prp_trgt_cn=raw.get("ptcpPrpTrgtCn", ""),
    )

    return {
        "policy_id": raw.get("plcyNo"),
        "policy_name": raw.get("plcyNm"),
        "category": raw.get("lclsfNm"),
        # --- 구조화된 필드: AI 추출 없이 그대로 사용 ---
        "structured_rules": {
            "age_min": int(raw["sprtTrgtMinAge"]) if raw.get("sprtTrgtMinAge") else None,
            "age_max": int(raw["sprtTrgtMaxAge"]) if raw.get("sprtTrgtMaxAge") else None,
            "age_limit_applies": raw.get("sprtTrgtAgeLmtYn") == "Y",
            "region_codes": raw.get("zipCd", "").split(",") if raw.get("zipCd") else [],
            "income_min": int(raw["earnMinAmt"]) if raw.get("earnMinAmt") else None,
            "income_max": int(raw["earnMaxAmt"]) if raw.get("earnMaxAmt") else None,
        },
        # --- 자유 텍스트: AI가 정리한 결과, 사람 검수 필요 ---
        "ai_interpreted": ai_result,
        "policy_text": raw.get("plcySprtCn", ""),  # S07 Q&A용 원문(지원내용)
        "apply_method": raw.get("plcyAplyMthdCn", ""),
        "required_docs": raw.get("sbmsnDcmntCn", ""),
        "apply_url": raw.get("aplyUrlAddr") or raw.get("refUrlAddr1", ""),
    }


if __name__ == "__main__":
    # 방금 받아온 실제 응답 중 정책 1개로 테스트
    sample_raw = {
        "plcyNo": "20260724005400213303",
        "plcyNm": "(검단구) 인천시 청년월세 지원사업",
        "lclsfNm": "주거",
        "sprtTrgtMinAge": "35",
        "sprtTrgtMaxAge": "39",
        "sprtTrgtAgeLmtYn": "Y",
        "zipCd": "28290",
        "earnMinAmt": "0",
        "earnMaxAmt": "0",
        "earnEtcCn": "소득 : (청년독립가구) 기준 중위소득 60%이하 (원가구) 기준 중위소득 100% 이하",
        "addAplyQlfcCndCn": "◎ 소득 : (청년독립가구) 기준 중위소득 60%이하 ... ◎ 재산 : (청년독립가구) 재산 122백만원 이하",
        "ptcpPrpTrgtCn": "○ 부모와 함께 거주(원가구와 세대분리하지 않은 자)하는 경우\n○ 전국 지자체 월세사업 또는 국토부 시행 월세지원사업 수혜 중인자 등(수혜종료 후 신청가능)",
        "plcySprtCn": "지원금액 : 1인 월 20만원씩, 최대 24개월",
        "plcyAplyMthdCn": "복지로를 통한 온라인신청 및 관할 행정복지센터 방문 신청",
        "sbmsnDcmntCn": "월세지원 신청서(필수), 소득·재산 신고서(필수)",
        "aplyUrlAddr": "https://youth.incheon.go.kr/youthpolicy/youthPolicyInfoDetail.do?poly_seq=463",
    }
    result = process_policy(sample_raw)
    print(json.dumps(result, ensure_ascii=False, indent=2))
