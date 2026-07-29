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
from dataclasses import dataclass
from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv

try:
    from .prompt_templates import QA_SYSTEM_PROMPT
except ImportError:
    from prompt_templates import QA_SYSTEM_PROMPT

load_dotenv()

_API_KEY = os.environ["UPSTAGE_API_KEY"]
_BASE_URL = os.environ.get("UPSTAGE_BASE_URL", "https://api.upstage.ai/v1")

# 다른 ai/ 모듈(rule_extractor.py, checklist_generator.py)이
# `from solar_client import client, SOLAR_MODEL`로 그대로 가져다 씁니다. (동기 호출용)
client = OpenAI(api_key=_API_KEY, base_url=_BASE_URL)

# chatbot_service.py가 await로 부르므로 비동기 호출은 별도 클라이언트 사용.
_async_client = AsyncOpenAI(api_key=_API_KEY, base_url=_BASE_URL)

# .env의 UPSTAGE_SOLAR_MODEL을 읽음. 값이 없으면 solar-pro2로 안전하게 fallback.
SOLAR_MODEL = os.environ.get("UPSTAGE_SOLAR_MODEL", "solar-pro2")


class SolarClientError(Exception):
    """Solar API 호출이 실패했을 때 발생. chatbot_service.py가 이걸 잡아서
    ExternalServiceError로 다시 감쌉니다."""
    pass


async def answer_policy_question(question: str, context: dict) -> str:
    """
    question: 사용자가 입력한 자유 질문
    context: chatbot_service.py가 만들어서 넘기는 dict. 예:
        {
          "title": "청년 월세 지원", "summary": "...", "description": "...",
          "support_target_text": "...", "support_content_text": "...",
          "application_method": "...", "application_start_date": "2026-03-30",
          "application_end_date": "2026-05-29", "is_ongoing": False,
          "provider_name": "...", "application_url": "...", "contact": "...",
          "original_text": "...",
          "conditions": [
            {"condition_key": "profile.age", "operator": "BETWEEN",
             "expected_value_json": {"min":19,"max":34}, "check_mode": "AUTO",
             "description": "만 19세~34세"}, ...
          ]
        }
        주의: 사용자별 충족/불충족 판정(matching_result)은 여기 없습니다.
        이 함수는 정책·조건 "정의"만 보고 설명합니다.

    반환: 답변 문자열 (dict 아님)
    """
    prompt_context = f"""
[정책명] {context.get('title')}
[요약] {context.get('summary')}
[상세 설명] {context.get('description')}
[지원 대상] {context.get('support_target_text')}
[지원 내용] {context.get('support_content_text')}
[신청 방법] {context.get('application_method')}
[신청 기간] {context.get('application_start_date')} ~ {context.get('application_end_date')}
[상시 모집 여부] {context.get('is_ongoing')}
[주관 기관] {context.get('provider_name')}
[신청 URL] {context.get('application_url')}
[문의처] {context.get('contact')}
[정책 원문] {context.get('original_text')}
[자격 조건 정의] {context.get('conditions')}
[질문] {question}
"""
    try:
        response = await _async_client.chat.completions.create(
            model=SOLAR_MODEL,
            messages=[
                {"role": "system", "content": QA_SYSTEM_PROMPT},
                {"role": "user", "content": prompt_context},
            ],
        )
        return response.choices[0].message.content
    except Exception as exc:
        raise SolarClientError(f"Solar API 호출 실패: {exc}") from exc


# ============================================================
# 호환 레이어
# ============================================================

@dataclass
class SolarClientConfig:
    """Solar API 연결 설정값. .env에서 읽어온 값을 그대로 담습니다."""
    api_key: str
    base_url: str = "https://api.upstage.ai/v1"
    model: str = "solar-pro2"

    @classmethod
    def from_env(cls) -> "SolarClientConfig":
        return cls(
            api_key=os.environ["UPSTAGE_API_KEY"],
            base_url=os.environ.get("UPSTAGE_BASE_URL", "https://api.upstage.ai/v1"),
            model=os.environ.get("UPSTAGE_SOLAR_MODEL", "solar-pro2"),
        )


class SolarClient:
    """OpenAI 클라이언트를 감싸는 얇은 래퍼. 클래스 형태가 필요한 호출부용."""

    def __init__(self, config: SolarClientConfig | None = None):
        self.config = config or SolarClientConfig.from_env()
        self._client = OpenAI(api_key=self.config.api_key, base_url=self.config.base_url)

    def chat(self, messages: list, **kwargs) -> str:
        kwargs.setdefault("model", self.config.model)
        try:
            response = self._client.chat.completions.create(messages=messages, **kwargs)
            return response.choices[0].message.content
        except Exception as exc:
            raise SolarClientError(f"Solar API 호출 실패: {exc}") from exc