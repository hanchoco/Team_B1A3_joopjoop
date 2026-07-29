"""
정책 Q&A (AI 정책 도우미)

핵심 원칙: 이 모듈은 자격 여부/금액을 스스로 "계산"하지 않습니다.
Backend/Policy Engine이 이미 계산해서 넘겨준 matching_result를
"쉬운 말로 설명"만 합니다. (기획 문서 9장: AI가 하지 않는 것 / 하는 것 참고) -> 확인 필요
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.environ["UPSTAGE_API_KEY"],
    base_url="https://api.upstage.ai/v1",
)

SYSTEM_PROMPT = """당신은 civiclens의 정책 도우미입니다.
지금 사용자가 보고 있는 정책 하나에 대해서만 답변합니다.

질문은 크게 두 종류입니다. 어떤 데이터를 근거로 답해야 하는지 구분하세요.
1. 자격 관련 질문("왜 제가 대상인가요?", "저도 받을 수 있나요?")
   → 반드시 [매칭 결과]에 있는 값만 사용해서 설명하세요. 지원 가능 여부나 금액을 새로 계산하지 마세요.
2. 내용 관련 질문("서류가 뭐예요?", "신청 기한이 언제예요?", "어떻게 신청해요?")
   → [정책 원문]에서 관련 내용을 찾아 쉬운 말로 풀어서 설명하세요.

공통 규칙:
- [매칭 결과]와 [정책 원문] 어디에도 없는 내용은 절대 만들어내지 마세요.
  이 경우 "정확한 내용은 신청 페이지 또는 담당 기관에서 확인이 필요하다"고 솔직하게 안내하세요.
- 행정 용어를 쉬운 말로 풀어서 설명하세요.
- 답변은 3~4문장 이내로 짧게 하세요.
"""


def answer_policy_question(policy: dict, user_profile: dict, matching_result: dict, question: str) -> dict:
    """
    policy: {"id": str, "name": str, "policy_text": str}
             policy_text는 A03에서 검수·승인된 정책 원문 (서류, 기한, 신청방법 등 포함)
    user_profile: {"age": int, "region": str, "housing_type": str, ...}
    matching_result: {"eligibility": "high|needs_review|low", "matched_rules": [...], "benefit": {...}}
    question: 사용자가 입력한 자유 질문
    """
    context = f"""
[정책명] {policy.get('name')}
[정책 원문] {policy.get('policy_text', '(등록된 원문 없음)')}
[사용자 정보] {user_profile}
[매칭 결과] {matching_result}
[질문] {question}
"""
    response = client.chat.completions.create(
        model="solar-pro2",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": context},
        ],
    )
    answer = response.choices[0].message.content

    # S05로 돌아가는 "근거 확인하기" 버튼에 쓸 수 있도록 어떤 필드를 근거로 썼는지 같이 반환
    source_fields = [r["field"] for r in matching_result.get("matched_rules", [])]

    return {"answer": answer, "source_fields": source_fields}


if __name__ == "__main__":
    policy = {
        "id": "482",
        "name": "청년 월세 지원",
        "policy_text": (
            "지원대상: 서울시에 거주하는 만 19세 이상 34세 이하의 무주택 월세 거주 청년. "
            "제출서류: 임대차계약서 사본, 소득증빙서류, 주민등록등본. "
            "신청기한: 매년 3월, 9월 (연 2회 접수). 신청방법: 온통청년 홈페이지에서 온라인 접수."
        ),
    }
    matching_result = {
        "eligibility": "high",
        "matched_rules": [
            {"field": "AGE", "status": "충족"},
            {"field": "REGION", "status": "충족"},
            {"field": "HOUSING_TYPE", "status": "충족"},
        ],
        "benefit": {"monthly": 200000, "annual_max": 2400000},
    }
    user_profile = {"age": 25, "region": "서울특별시 마포구", "housing_type": "월세"}

    # 자격 관련 질문 -> matching_result 근거로 답해야 함
    print(answer_policy_question(policy, user_profile, matching_result, "왜 제가 받을 수 있는 거예요?"))

    # 내용 관련 질문 -> policy_text 근거로 답해야 함
    print(answer_policy_question(policy, user_profile, matching_result, "신청하려면 어떤 서류가 필요해요?"))