"""
가입 준비하기 - 전체 체크리스트 생성

사용자 흐름:
  조건 불충족 -> 예외조항 확인 -> 예외 있으면 안내 / 없으면 그대로 불충족(x)
  조건 충족   -> 그래도 추가로 확인할 게 있으면 안내 (예: 부모님 소득 확인 필요 등,
                구조화 데이터엔 없지만 정책 원문엔 있는 내용)
  + 필요서류 안내
  위 전체를 "진짜 목록(체크리스트)"으로 보여주고, 동시에 AI가 쉬운 말로도 설명한다.

역할 분리:
  - Backend/Policy Engine: 각 조건이 충족/불충족/확인필요 중 무엇인지 판정. (condition_results)
  - AI: 판정을 바꾸지 않고, (1) 불충족 항목엔 예외조항이 있는지 확인해서 설명,
    (2) 충족 항목도 포함해 구조화 데이터에 없는 추가 확인사항을 안내,
    (3) 서류 체크리스트와 전체 요약을 자연어로 정리합니다.
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

SYSTEM_PROMPT = """당신은 civiclens의 신청 준비 체크리스트 도우미입니다.
Backend가 이미 판정한 조건별 상태(충족/불충족/확인필요)를 받아서, 항목마다 설명을 붙입니다.

절대 규칙: 각 조건의 status(충족/불충족/확인필요)는 이미 확정된 값입니다. 당신은 이 판정을
바꾸지 않습니다. 오직 "설명을 추가"할 뿐입니다.

상태별로 다르게 처리하세요:

1. status가 "불충족"인 항목
   -> [예외조항 정보]에 이 조건과 관련된 예외/완화 규정이 있는지 확인하세요.
   -> 있으면: possible_exception에 그 내용과 근거를 적고, explanation에 "예외에 해당하는지 확인해보세요"라고 안내
   -> 없으면: possible_exception은 null로 하고, explanation에 "관련 예외조항은 확인되지 않았습니다"라고 솔직히 안내

2. status가 "충족"인 항목
   -> 기본적으로 짧게 확인 문구만 답니다.
   -> 단, [정책 추가조건 원문]에 이 조건과 관련해서 구조화 데이터에는 없는 추가 확인사항이
      있으면(예: "부모님 소득도 함께 본다" 등) additional_note에 안내하세요. 없으면 null.

3. status가 "확인필요"인 항목
   -> 왜 확인이 필요한지, [정책 추가조건 원문]/[예외조항 정보]를 참고해서 쉽게 설명하세요.

4. 없는 내용을 지어내지 마세요. 근거가 없으면 솔직히 "확인되지 않았다"고 답하세요.
5. 서류 목록(document_checklist)은 받은 목록을 그대로 사용하고, 필요하면 준비 팁만 짧게 추가하세요.
6. 마지막에 summary로 전체를 3~4문장 자연어로 요약하세요 (충족/불충족/확인필요 개수와 핵심 액션 포함).
7. 반드시 JSON으로만 답하세요.

출력 형식:
{
  "condition_checklist": [
    {
      "attribute_key": "household_monthly_income",
      "status": "불충족",
      "explanation": "...",
      "possible_exception": "..." 또는 null,
      "additional_note": "..." 또는 null
    }
  ],
  "document_checklist": [
    {"title": "...", "is_required": true, "tip": "..."}
  ],
  "summary": "..."
}
"""


def generate_application_checklist(
    policy: dict,
    condition_results: list,
    requirements: list,
    ai_interpreted: dict,
) -> dict:
    """
    policy: {"id": str, "name": str}
    condition_results: Backend가 계산한 "전체" 조건 결과 (충족/불충족/확인필요 다 포함, 일부만 X)
        예: [
          {"attribute_key": "age", "title": "나이", "status": "충족", "user_value": 25, "expected": "19~34세"},
          {"attribute_key": "household_monthly_income", "title": "소득", "status": "불충족",
           "user_value": 3200000, "expected": "3000000 이하"}
        ]
    requirements: policy_requirements 테이블 목록 그대로
    ai_interpreted: A02의 결과 (income_note, participation_limit 등 예외조항/추가조건 원문 포함)
    """
    context = f"""
[정책명] {policy.get('name')}
[조건별 판정 결과] {condition_results}
[필요서류 원본] {requirements}
[예외조항 정보] {ai_interpreted}
"""
    response = client.chat.completions.create(
        model="solar-pro2",
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": context},
        ],
    )
    return json.loads(response.choices[0].message.content)


if __name__ == "__main__":
    policy = {"id": "463", "name": "인천시 청년월세 지원사업"}
    requirements = [
        {"title": "월세지원 신청서", "is_required": True},
        {"title": "소득·재산 신고서", "is_required": True},
        {"title": "신분증", "is_required": False},
    ]
    ai_interpreted = {
        "income_note": {
            "summary": "청년독립가구는 중위소득 60% 이하, 원가구는 100% 이하",
            "evidence": "원가구(부모님) 소득·재산 미고려: 30세 이상, 혼인, 미혼부·모, "
                         "30세 미만 미혼 청년의 소득이 중위 50% 이상으로 생계를 달리한다고 인정되는 경우"
        }
    }

    print("=" * 20, "시나리오 1: 전부 충족", "=" * 20)
    demo1 = generate_application_checklist(
        policy=policy,
        condition_results=[
            {"attribute_key": "age", "title": "나이", "status": "충족", "user_value": 25, "expected": "19~34세"},
            {"attribute_key": "region_code", "title": "거주지역", "status": "충족", "user_value": "검단구", "expected": "검단구"},
        ],
        requirements=requirements,
        ai_interpreted=ai_interpreted,
    )
    print(json.dumps(demo1, ensure_ascii=False, indent=2))

    print("=" * 20, "시나리오 2: 불충족 + 예외조항 있음", "=" * 20)
    demo2 = generate_application_checklist(
        policy=policy,
        condition_results=[
            {"attribute_key": "age", "title": "나이", "status": "충족", "user_value": 25, "expected": "19~34세"},
            {"attribute_key": "household_monthly_income", "title": "소득", "status": "불충족",
             "user_value": "30세 미만 미혼, 부모와 별도 생계", "expected": "중위소득 60% 이하"},
        ],
        requirements=requirements,
        ai_interpreted=ai_interpreted,
    )
    print(json.dumps(demo2, ensure_ascii=False, indent=2))

    print("=" * 20, "시나리오 3: 불충족 + 예외조항 없음", "=" * 20)
    demo3 = generate_application_checklist(
        policy=policy,
        condition_results=[
            {"attribute_key": "age", "title": "나이", "status": "불충족", "user_value": 41, "expected": "19~34세"},
        ],
        requirements=requirements,
        ai_interpreted=ai_interpreted,
    )
    print(json.dumps(demo3, ensure_ascii=False, indent=2))