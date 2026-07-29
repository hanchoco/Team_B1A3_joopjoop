"""
services/ai/checklist_generator.py  (구 application_checklist.py)

S10. 가입 준비하기 - 전체 체크리스트 생성

화면(joopjoop 실제 UI)과 동일하게, 조건/서류 구분 없이 "하나의 리스트"로 반환합니다.
각 항목의 "type" 필드로 구분: condition / exception / participation_limit / document
summary는 만들지 않습니다 (화면에 없음, 진행률은 Backend/Frontend가 체크 개수로 계산).

역할 분리는 유지합니다:
  - Backend/Policy Engine: 각 조건이 충족/불충족/확인필요 중 무엇인지 "판정"합니다. (condition_results)
  - 이 모듈(AI): 판정을 바꾸지 않고, 하나의 리스트로 재정리 + 설명을 붙일 뿐입니다.
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

    반환: {"checklist": [ {"type": "condition|exception|participation_limit|document", ...}, ... ]}
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
    result = json.loads(response.choices[0].message.content)

    # 안전장치: type="exception"인데 condition_results에 실제로 없던 condition_key가
    # 들어있으면(=AI가 ai_interpreted만 보고 없는 조건을 지어낸 것) 강제로 제거.
    real_keys = {c.get("condition_key") for c in condition_results}
    result["checklist"] = [
        item for item in result.get("checklist", [])
        if item.get("type") != "exception" or item.get("condition_key") in real_keys
    ]

    return result


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