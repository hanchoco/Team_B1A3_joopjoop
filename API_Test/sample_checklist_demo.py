"""
체크리스트 생성 샘플 — (검단구) 인천시 청년월세 지원사업 기준

Backend가 실제로 이렇게 데이터를 만들어서 checklist_generator.generate_application_checklist()에
넘긴다고 가정한 예시입니다. condition_results 안에 일반 조건(나이/지역/소득)이랑
participation_limit(체크박스 전용 안내) 항목이 섞여 있는 걸 보여주는 게 목적입니다.

    python sample_checklist_demo.py
"""

import json

from checklist_generator import generate_application_checklist

policy = {"id": "463", "name": "(검단구) 인천시 청년월세 지원사업"}

# Policy Engine이 실제로 판정한 결과라고 가정 (일반 조건들)
# + participation_limit 항목들은 판정이 아니라 rule_extractor.py가 만든 체크박스 안내 그대로
condition_results = [
    {"condition_key": "profile.age", "title": "나이", "status": "충족",
     "user_value": 25, "expected": "19~39세"},
    {"condition_key": "profile.region_code", "title": "거주지역", "status": "충족",
     "user_value": "인천 검단구", "expected": "검단구"},
    {"condition_key": "profile.income_band_code", "title": "소득", "status": "확인필요",
     "user_value": "BETWEEN_50_75", "expected": "중위소득 60% 이하"},
    {"condition_key": "profile.housing_type_code", "title": "주거형태", "status": "충족",
     "user_value": "MONTHLY_RENT", "expected": "월세 거주자만 (자가/공공임대 제외)"},

    # ↓ 여기부터 3개가 participation_limit — 판정 없는 순수 안내 체크박스
    {"condition_key": "participation_limit", "title": "참여 제한 안내", "status": "확인필요",
     "user_value": None, "expected": None,
     "description": "직계존속, 형제, 자매 등 2촌 이내 주택을 임차한 경우 제외"},
    {"condition_key": "participation_limit", "title": "참여 제한 안내", "status": "확인필요",
     "user_value": None, "expected": None,
     "description": "전국 지자체 월세사업 또는 국토부 시행 월세지원사업 수혜 중인자 제외"},
    {"condition_key": "participation_limit", "title": "참여 제한 안내", "status": "확인필요",
     "user_value": None, "expected": None,
     "description": "과거 국토부 청년월세 한시 특별지원 24개월 수혜자 제외"},
]

requirements = [
    {"title": "월세지원 신청(변경)서", "is_required": True},
    {"title": "소득·재산 신고서", "is_required": True},
    {"title": "임대차계약서(확정일자 날인) 사본", "is_required": True},
    {"title": "신분증", "is_required": False},
]

# rule_extractor.py의 income_note 결과라고 가정
ai_interpreted = {
    "income_note": {
        "summary": "청년독립가구는 중위소득 60% 이하, 원가구는 100% 이하",
        "evidence": "원가구(부모님) 소득·재산 미고려: 30세 이상, 혼인, 미혼부·모, "
                     "30세 미만 미혼 청년의 소득이 중위 50% 이상으로 생계를 달리한다고 인정되는 경우"
    }
}

result = generate_application_checklist(
    policy=policy,
    condition_results=condition_results,
    requirements=requirements,
    ai_interpreted=ai_interpreted,
)

print(json.dumps(result, ensure_ascii=False, indent=2))

print("\n--- 확인 포인트 ---")
checklist = result.get("checklist", [])
print("전체 항목 수:", len(checklist))
for item in checklist:
    print(f" [{item.get('type')}]", item.get("title"), "|", item.get("explanation") or item.get("tip"))