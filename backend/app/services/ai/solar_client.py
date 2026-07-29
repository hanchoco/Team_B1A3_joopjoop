"""
services/ai/solar_client.py  (구 policy_qa.py)

이 파일 두 가지 역할:
  1. Upstage(Solar) API 클라이언트를 한 곳에서 만들어서, rule_extractor.py /
     checklist_generator.py가 여기서 import해서 재사용합니다. (client 중복 생성 방지)
  2. 정책 Q&A 함수(answer_policy_question)를 담고 있습니다.

핵심 원칙: answer_policy_question()은 자격 여부/금액을 스스로 "계산"하지 않습니다.
Backend/Policy Engine이 이미 계산해서 넘겨준 matching_result의 eligibility 판정은
절대 뒤집지 않고, 그 외에는 정책 원문+일반 상식을 활용해 자유롭게 설명합니다.
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

from prompt_templates import QA_SYSTEM_PROMPT

load_dotenv()

# 다른 ai/ 모듈(rule_extractor.py, checklist_generator.py)이
# `from solar_client import client`로 그대로 가져다 씁니다.
client = OpenAI(
    api_key=os.environ["UPSTAGE_API_KEY"],
    base_url="https://api.upstage.ai/v1",
)


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
            {"role": "system", "content": QA_SYSTEM_PROMPT},
            {"role": "user", "content": context},
        ],
    )
    answer = response.choices[0].message.content

    # S05로 돌아가는 "근거 확인하기" 버튼에 쓸 수 있도록 어떤 조건을 근거로 썼는지 같이 반환
    source_fields = [r["condition_key"] for r in matching_result.get("matched_rules", [])]

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
            {"condition_key": "profile.age", "status": "충족"},
            {"condition_key": "profile.region_code", "status": "충족"},
            {"condition_key": "profile.housing_type_code", "status": "충족"},
        ],
        "benefit": {"monthly": 200000, "annual_max": 2400000},
    }
    user_profile = {"age": 25, "region": "서울특별시 마포구", "housing_type": "월세"}

    # 자격 관련 질문 -> matching_result 근거로 답해야 함
    print(answer_policy_question(policy, user_profile, matching_result, "왜 제가 받을 수 있는 거예요?"))

    # 내용 관련 질문 -> policy_text 근거로 답해야 함
    print(answer_policy_question(policy, user_profile, matching_result, "신청하려면 어떤 서류가 필요해요?"))