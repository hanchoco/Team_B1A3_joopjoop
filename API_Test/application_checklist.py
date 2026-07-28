"""
S10. 가입 준비하기 - 체크리스트 설명 생성

역할 분리가 핵심입니다:
  - Backend/Policy Engine: user_profile과 structured_rules(나이/지역/소득 등 숫자)를 비교해서
    mismatched_fields(어떤 항목이 왜 어긋났는지)를 계산합니다. <- AI 아님, 순수 로직
  - 이 모듈(AI): mismatched_fields를 받아서, A02에서 이미 뽑아둔 예외조항(ai_interpreted)에
    해당 사항이 있는지 확인하고, 사용자에게 쉬운 말로 설명만 붙입니다. <- 판정은 안 함

즉 이 모듈은 "확인필요"라는 판정 자체를 내리지 않습니다. 판정은 이미 끝난 상태로 들어오고,
"왜 그런지" + "예외조항으로 빠져나갈 구멍이 있는지"만 설명합니다.
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.environ["UPSTAGE_API_KEY"],
    base_url="https://api.upstage.ai/v1",
)

SYSTEM_PROMPT = """당신은 civiclens의 신청 준비 체크리스트 도우미입니다.
Backend가 이미 계산한 "어긋난 항목(mismatched_fields)"을 받아서, 각 항목마다 설명을 답니다.

규칙:
1. 이미 "확인 필요"로 판정된 항목의 판정 자체를 바꾸지 마세요. 당신은 판정하지 않습니다.
2. [예외조항 정보]에 이 항목과 관련된 예외/완화 조건이 있으면, 그 내용을 근거와 함께 안내하세요.
   없으면 "관련 예외조항은 확인되지 않았습니다"라고 솔직히 답하세요.
3. 각 항목마다 status(그대로 유지), explanation(왜 확인 필요인지 쉬운 설명),
   possible_exception(해당되는 예외조항 요약, 없으면 null)을 포함하세요.
4. 반드시 JSON으로만 답하세요.

출력 형식 예시:
{
  "checklist": [
    {
      "field": "소득",
      "status": "확인 필요",
      "explanation": "입력하신 소득이 기준보다 다소 높아 확인이 필요합니다.",
      "possible_exception": "30세 미만 미혼 청년이 생계를 달리하는 경우 부모님 소득은 보지 않는다는 예외가 있습니다. 해당되는지 확인해보세요."
    }
  ]
}
"""


def generate_checklist_explanation(policy: dict, mismatched_fields: list, ai_interpreted: dict) -> dict:
    """
    policy: {"id": str, "name": str}
    mismatched_fields: Backend가 계산한 결과. 예:
        [{"field": "소득", "user_value": 3200000, "required": "3000000 이하", "status": "확인 필요"}]
    ai_interpreted: A02에서 이미 만들어둔 결과 (rule_extractor.process_policy의 ai_interpreted 그대로)
        예외조항은 보통 ai_interpreted["income_detail"] 또는 ["extra_conditions"]에 들어있음
    """
    if not mismatched_fields:
        return {"checklist": []}

    context = f"""
[정책명] {policy.get('name')}
[어긋난 항목들] {mismatched_fields}
[예외조항 정보] {ai_interpreted}
"""
    response = client.chat.completions.create(
        model="solar-pro2",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": context},
        ],
    )
    import json
    return json.loads(response.choices[0].message.content)


if __name__ == "__main__":
    demo = generate_checklist_explanation(
        policy={"id": "463", "name": "인천시 청년월세 지원사업"},
        mismatched_fields=[
            {"field": "소득", "user_value": "청년독립가구 중위소득 65%", "required": "60% 이하", "status": "확인 필요"}
        ],
        ai_interpreted={
            "income_detail": {
                "summary": "청년독립가구는 중위소득 60% 이하, 원가구는 100% 이하",
                "evidence": "원가구(부모님) 소득·재산 미고려: 30세 이상, 혼인, 미혼부·모, "
                             "30세 미만 미혼 청년의 소득이 중위 50% 이상으로 생계를 달리한다고 인정되는 경우"
            }
        },
    )
    print(demo)
