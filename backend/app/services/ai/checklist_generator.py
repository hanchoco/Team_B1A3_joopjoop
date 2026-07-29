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

try:
    from .solar_client import client
    from .prompt_templates import CHECKLIST_SYSTEM_PROMPT
except ImportError:
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