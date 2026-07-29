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
from dataclasses import dataclass, asdict

try:
    from .solar_client import SolarClient, client as _default_sync_client, SOLAR_MODEL as _DEFAULT_MODEL
    from .prompt_templates import DOCUMENT_SYSTEM_PROMPT, CHECKLIST_SYSTEM_PROMPT
except ImportError:
    from solar_client import SolarClient
    from prompt_templates import DOCUMENT_SYSTEM_PROMPT, CHECKLIST_SYSTEM_PROMPT


# ============================================================
# 타입
# ============================================================

@dataclass
class GeneratedDocument:
    """policy_documents 한 행을 담는 타입."""
    document_code: str
    document_name: str
    required_reason: str = None
    issuing_organization: str = None
    issuing_method: str = None
    issuing_url: str = None
    submission_format: str = None
    is_required: bool = True
    display_order: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


# ============================================================
# 1. A02 파이프라인용 - 서류 목록만 생성 (실제 seed_policy_data.py가 호출)
# ============================================================

async def generate_checklist(policy_payload: dict, *, client: SolarClient) -> list[GeneratedDocument]:
    """
    policy_payload: youth_policy_api.py가 만든 정규화된 정책 dict.
    client: SolarClient 인스턴스 (seed_policy_data.py가 생성해서 넘겨줌)
    반환: GeneratedDocument 리스트 (제출서류 초안)
    """
    raw = policy_payload.get("raw_payload") or policy_payload
    user_input = f"""
[정책명] {raw.get('plcyNm') or policy_payload.get('title')}
[제출서류] {raw.get('sbmsnDcmntCn', '') or '(없음)'}
"""
    ai_result = await client.complete_json(DOCUMENT_SYSTEM_PROMPT, user_input)

    return [
        GeneratedDocument(
            document_code=f"DOC-{i + 1:02d}",
            document_name=d.get("document_name"),
            required_reason=d.get("required_reason"),
            issuing_organization=d.get("issuing_organization"),
            issuing_method=d.get("issuing_method"),
            issuing_url=d.get("issuing_url"),
            submission_format=d.get("submission_format"),
            is_required=d.get("is_required", True),
            display_order=i + 1,
        )
        for i, d in enumerate(ai_result.get("documents", []))
    ]


def create_checklist_draft(document: GeneratedDocument) -> dict:
    """GeneratedDocument -> DB INSERT용 dict."""
    return document.to_dict()


def validate_checklist_payload(payload: dict) -> list[GeneratedDocument]:
    """저장된 초안 JSON에서 다시 읽어들인 서류 목록을 검증하고
    GeneratedDocument 객체 리스트로 복원합니다.
    payload: {"documents": [{...dict...}, ...]}
    """
    items = payload.get("documents")
    if not isinstance(items, list):
        raise ValueError("documents must be a list")

    valid_fields = GeneratedDocument.__dataclass_fields__.keys()
    result = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("each document must be an object")
        if not item.get("document_name"):
            raise ValueError("document missing document_name")
        result.append(GeneratedDocument(**{k: v for k, v in item.items() if k in valid_fields}))
    return result


# ============================================================
# 2. S10 실시간 화면용 - 조건+예외+참여제한+서류 통합 체크리스트
#    (seed 파이프라인과 무관, 별도 API 엔드포인트에서 사용될 함수)
# ============================================================

def generate_application_checklist(
    policy: dict,
    condition_results: list,
    requirements: list,
    ai_interpreted: dict,
) -> dict:
    """
    policy: {"id": str, "name": str}
    condition_results: Backend가 계산한 "전체" 조건 결과 (충족/불충족/확인필요 다 포함)
    requirements: policy_documents 테이블 목록 그대로
    ai_interpreted: income_note 등 예외조항/추가조건 원문 포함

    반환: {"checklist": [ {"type": "condition|exception|participation_limit|document", ...}, ... ]}

    주의: 이 함수는 동기(sync) 함수이고 기존 전역 client를 씁니다.
    generate_checklist()(위 1번)와는 별개의 함수이니 혼동하지 마세요.
    """
    context = f"""
[정책명] {policy.get('name')}
[조건별 판정 결과] {condition_results}
[필요서류 원본] {requirements}
[예외조항 정보] {ai_interpreted}
"""
    response = _default_sync_client.chat.completions.create(
        model=_DEFAULT_MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": CHECKLIST_SYSTEM_PROMPT},
            {"role": "user", "content": context},
        ],
    )
    result = json.loads(response.choices[0].message.content)

    real_keys = {c.get("condition_key") for c in condition_results}
    result["checklist"] = [
        item for item in result.get("checklist", [])
        if item.get("type") != "exception" or item.get("condition_key") in real_keys
    ]
    return result