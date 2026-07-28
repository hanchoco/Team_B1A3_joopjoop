"""
AI & Integration 서비스 진입점.
Backend(2번)나 Frontend(1번)가 이 서비스를 별도 컨테이너로 호출한다고 가정합니다.

로컬 실행:
    pip install -r requirements.txt --break-system-packages
    uvicorn main:app --reload --port 8001
"""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, Optional

from API_Test.rule_extractor import process_policy
from API_Test.policy_qa import answer_policy_question
from API_Test.application_checklist import generate_checklist_explanation

app = FastAPI(title="civiclens AI service")


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------- A02. Rule 추출 ----------
class ExtractRequest(BaseModel):
    raw_policy: dict[str, Any]  # 온통청년 API 응답의 정책 항목 하나 그대로


@app.post("/extract-rules")
def extract_rules_endpoint(req: ExtractRequest):
    return process_policy(req.raw_policy)


# ---------- S10. 가입 준비하기 체크리스트 설명 ----------
class ChecklistRequest(BaseModel):
    policy: dict[str, Any]
    mismatched_fields: list[dict[str, Any]]  # Backend가 이미 계산한 결과
    ai_interpreted: dict[str, Any]  # A02 결과 재사용


@app.post("/checklist-explain")
def checklist_explain_endpoint(req: ChecklistRequest):
    return generate_checklist_explanation(req.policy, req.mismatched_fields, req.ai_interpreted)


# ---------- S07. 정책 Q&A ----------
class QARequest(BaseModel):
    policy: dict[str, Any]
    user_profile: dict[str, Any]
    matching_result: dict[str, Any]
    question: str


@app.post("/policy-qa")
def policy_qa_endpoint(req: QARequest):
    return answer_policy_question(
        policy=req.policy,
        user_profile=req.user_profile,
        matching_result=req.matching_result,
        question=req.question,
    )
