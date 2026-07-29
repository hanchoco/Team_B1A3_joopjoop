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

import json

from solar_client import client
from prompt_templates import CHECKLIST_SYSTEM_PROMPT


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
          {"condition_key": "profile.age", "title": "나이", "status": "충족", "user_value": 25, "expected": "19~34세"},
          {"condition_key": "profile.income_band_code", "title": "소득", "status": "불충족",
           "user_value": 3200000, "expected": "3000000 이하"}
        ]
    requirements: policy_documents 테이블 목록 그대로
    ai_interpreted: A02의 결과 (income_note 등 예외조항/추가조건 원문 포함)
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
            {"role": "system", "content": CHECKLIST_SYSTEM_PROMPT},
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
            {"condition_key": "profile.age", "title": "나이", "status": "충족", "user_value": 25, "expected": "19~34세"},
            {"condition_key": "profile.region_code", "title": "거주지역", "status": "충족", "user_value": "검단구", "expected": "검단구"},
        ],
        requirements=requirements,
        ai_interpreted=ai_interpreted,
    )
    print(json.dumps(demo1, ensure_ascii=False, indent=2))

    print("=" * 20, "시나리오 2: 불충족 + 예외조항 있음", "=" * 20)
    demo2 = generate_application_checklist(
        policy=policy,
        condition_results=[
            {"condition_key": "profile.age", "title": "나이", "status": "충족", "user_value": 25, "expected": "19~34세"},
            {"condition_key": "profile.income_band_code", "title": "소득", "status": "불충족",
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
            {"condition_key": "profile.age", "title": "나이", "status": "불충족", "user_value": 41, "expected": "19~34세"},
        ],
        requirements=requirements,
        ai_interpreted=ai_interpreted,
    )
    print(json.dumps(demo3, ensure_ascii=False, indent=2))