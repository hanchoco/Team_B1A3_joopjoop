"""
로컬 실행:
    pip install -r requirements.txt --break-system-packages
    uvicorn main:app --reload --port 8001
"""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, Optional

from rule_extractor import process_policy
from policy_qa import answer_policy_question
from application_checklist import generate_application_checklist

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


# ---------- S10. 가입 준비하기 전체 체크리스트 ----------
class ChecklistRequest(BaseModel):
    policy: dict[str, Any]
    condition_results: list[dict[str, Any]]  # Backend가 계산한 전체 조건 결과 (일부만 X)
    requirements: list[dict[str, Any]]
    ai_interpreted: dict[str, Any]


@app.post("/checklist-explain")
def checklist_explain_endpoint(req: ChecklistRequest):
    return generate_application_checklist(
        req.policy, req.condition_results, req.requirements, req.ai_interpreted
    )


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