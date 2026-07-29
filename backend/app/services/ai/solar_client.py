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

import json
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

# 동기(sync) 컨텍스트에서 쓰는 공용 클라이언트/모델명.
# checklist_generator.py의 generate_application_checklist()(S10 실시간 화면용,
# 동기 함수)가 이걸 가져다 씁니다. 나머지(A02 파이프라인)는 아래 SolarClient(비동기)를 씁니다.
client = OpenAI(api_key=_API_KEY, base_url=_BASE_URL)
SOLAR_MODEL = os.environ.get("UPSTAGE_SOLAR_MODEL", "solar-pro2")


class SolarClientError(Exception):
    """Solar API 호출이 실패했을 때 발생. chatbot_service.py가 이걸 잡아서
    ExternalServiceError로 다시 감쌉니다."""
    pass


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
    """비동기 Solar 클라이언트. seed_policy_data.py가 `SolarClient()`로 인자 없이
    생성하고, extract_conditions()/generate_checklist()에 client=로 넘깁니다."""

    def __init__(self, config: SolarClientConfig | None = None):
        self.config = config or SolarClientConfig.from_env()
        self._client = AsyncOpenAI(api_key=self.config.api_key, base_url=self.config.base_url)

    async def complete_json(self, system_prompt: str, user_content: str) -> dict:
        """system_prompt/user_content로 Solar를 JSON 모드로 호출해서 dict로 반환."""
        try:
            response = await self._client.chat.completions.create(
                model=self.config.model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
            )
            return json.loads(response.choices[0].message.content)
        except Exception as exc:
            raise SolarClientError(f"Solar API 호출 실패: {exc}") from exc

    async def complete_text(self, system_prompt: str, user_content: str) -> str:
        """일반 텍스트 응답이 필요할 때(예: Q&A) 사용."""
        try:
            response = await self._client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
            )
            return response.choices[0].message.content
        except Exception as exc:
            raise SolarClientError(f"Solar API 호출 실패: {exc}") from exc

    async def close(self) -> None:
        await self._client.close()


# ============================================================
# S07. 정책 Q&A - chatbot_service.py가 직접 호출 (client 없이, 내부 기본 클라이언트 사용)
# ============================================================

_default_client: SolarClient | None = None


def _get_default_client() -> SolarClient:
    global _default_client
    if _default_client is None:
        _default_client = SolarClient()
    return _default_client


async def answer_policy_question(question: str, context: dict) -> str:
    """
    question: 사용자가 입력한 자유 질문
    context: chatbot_service.py가 만들어서 넘기는 dict (policies 필드 + conditions 정의).
             사용자별 충족/불충족 판정은 여기 없습니다 - 정책·조건 "정의"만 보고 설명합니다.
    반환: 답변 문자열
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
    client = _get_default_client()
    return await client.complete_text(QA_SYSTEM_PROMPT, prompt_context)