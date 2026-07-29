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

try:
    from .prompt_templates import QA_SYSTEM_PROMPT
except ImportError:
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