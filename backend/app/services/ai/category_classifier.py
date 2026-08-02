"""
정책 원문 -> policy_categories(8대 카테고리) AI 분류

rule_extractor.py(자격조건), benefit_extractor.py(혜택)와 동일한 구조를 따릅니다.

배경:
  온통청년 API의 대/중분류(lclsfNm/mclsfNm)는 세금/교통/금융/복지처럼 우리 서비스가 쓰는
  카테고리와 다르게 묶여 있어(예: 금융·복지·문화가 하나의 값으로 뭉뚱그려짐) 키워드 매칭만
  으로는 정확히 구분할 수 없다. 그래서 정책 원문(제목/지원대상/지원내용)을 AI가 직접 읽고
  분류한다.

원칙:
  - AI가 만든 결과는 전부 초안입니다(리뷰 초안 JSON에만 기록, 사람 승인 후 DB 반영).
"""

try:
    from .prompt_templates import CATEGORY_SYSTEM_PROMPT
    from .solar_client import SolarClient
except ImportError:
    from prompt_templates import CATEGORY_SYSTEM_PROMPT
    from solar_client import SolarClient


# ============================================================
# 코드 레지스트리 (models/user_category_profile.py의 CategoryCode와 동일한 값)
# ============================================================

ALLOWED_CATEGORY_CODES = {
    "HOUSING",
    "TRANSPORT",
    "FINANCE",
    "TAX",
    "EMPLOYMENT",
    "WELFARE",
    "PARTICIPATION",
    "ETC",
}


# ============================================================
# 메인 함수 (실제 프로덕션 진입점)
# ============================================================


async def classify_policy_category(policy_payload: dict, *, client: SolarClient) -> list[str]:
    """
    policy_payload: youth_policy_api.py가 만든 정규화된 정책 dict.
    client: SolarClient 인스턴스 (seed_policy_data.py가 생성해서 넘겨줌)
    반환: category_codes 리스트 (첫 번째가 대표 카테고리 - crud.policies가 is_primary로 사용)
    """
    raw = policy_payload.get("raw_payload") or policy_payload

    support_target = raw.get("sprtTrgtCn") or policy_payload.get("support_target_text") or "(없음)"
    support_content = (
        raw.get("plcySprtCn") or policy_payload.get("support_content_text") or "(없음)"
    )
    user_input = f"""
[정책명] {raw.get('plcyNm') or policy_payload.get('title')}
[지원대상] {support_target}
[지원내용] {support_content}
[원본 분류(참고용, 부정확할 수 있음)] {raw.get('lclsfNm', '')} / {raw.get('mclsfNm', '')}
"""
    ai_result = await client.complete_json(CATEGORY_SYSTEM_PROMPT, user_input)

    seen: set[str] = set()
    codes: list[str] = []
    for code in ai_result.get("category_codes", []):
        if isinstance(code, str) and code in ALLOWED_CATEGORY_CODES and code not in seen:
            seen.add(code)
            codes.append(code)
    return codes or ["ETC"]
