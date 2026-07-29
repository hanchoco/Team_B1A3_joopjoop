"""Upstage Solar HTTP client and policy-scoped Q&A.

This is the only module that sends requests to the Solar chat-completions API.
No API key is required at import time; configuration is checked immediately
before the first network request.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import httpx

from .prompt_templates import build_policy_qa_messages

DEFAULT_UPSTAGE_BASE_URL = "https://api.upstage.ai/v1"
DEFAULT_SOLAR_MODEL = "solar-pro3"


class SolarClientError(RuntimeError):
    """Raised when Solar configuration, transport, or response data is invalid."""


@dataclass(frozen=True, slots=True)
class SolarClientConfig:
    """Runtime configuration for the Solar API."""

    api_key: str | None = None
    base_url: str = DEFAULT_UPSTAGE_BASE_URL
    model: str = DEFAULT_SOLAR_MODEL
    timeout_seconds: float = 30.0

    @classmethod
    def from_env(cls) -> "SolarClientConfig":
        timeout_text = os.getenv("UPSTAGE_TIMEOUT_SECONDS", "30")
        try:
            timeout_seconds = float(timeout_text)
        except ValueError as exc:
            raise SolarClientError("UPSTAGE_TIMEOUT_SECONDS must be a number") from exc
        if timeout_seconds <= 0:
            raise SolarClientError("UPSTAGE_TIMEOUT_SECONDS must be positive")
        return cls(
            api_key=(os.getenv("UPSTAGE_API_KEY") or os.getenv("SOLAR_API_KEY") or None),
            base_url=os.getenv("UPSTAGE_BASE_URL", DEFAULT_UPSTAGE_BASE_URL),
            model=(
                os.getenv("UPSTAGE_SOLAR_MODEL") or os.getenv("SOLAR_MODEL") or DEFAULT_SOLAR_MODEL
            ),
            timeout_seconds=timeout_seconds,
        )


class SolarClient:
    """Small async client for Solar's OpenAI-compatible chat endpoint."""

    def __init__(
        self,
        config: SolarClientConfig | None = None,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = config or SolarClientConfig.from_env()
        self._http_client = http_client
        self._owns_http_client = http_client is None

    @property
    def model(self) -> str:
        return self._config.model

    def _endpoint(self) -> str:
        base_url = self._config.base_url.rstrip("/")
        if base_url.endswith("/chat/completions"):
            return base_url
        return f"{base_url}/chat/completions"

    def _authorization_headers(self) -> dict[str, str]:
        api_key = (self._config.api_key or "").strip()
        if not api_key:
            raise SolarClientError("UPSTAGE_API_KEY is required when calling the Solar API")
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def _client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=self._config.timeout_seconds)
        return self._http_client

    async def complete(
        self,
        messages: Sequence[Mapping[str, str]],
        *,
        temperature: float = 0.1,
        max_tokens: int = 2_048,
    ) -> str:
        """Return one Solar response for explicitly supplied messages."""

        if not messages:
            raise ValueError("messages must not be empty")
        if not 0 <= temperature <= 2:
            raise ValueError("temperature must be between 0 and 2")
        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")

        normalized_messages: list[dict[str, str]] = []
        for message in messages:
            role = message.get("role", "").strip()
            content = message.get("content", "").strip()
            if role not in {"system", "user", "assistant"}:
                raise ValueError(f"unsupported message role: {role!r}")
            if not content:
                raise ValueError("message content must not be empty")
            normalized_messages.append({"role": role, "content": content})

        payload: dict[str, object] = {
            "model": self._config.model,
            "messages": normalized_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        try:
            response = await self._client().post(
                self._endpoint(),
                headers=self._authorization_headers(),
                json=payload,
            )
        except httpx.TimeoutException as exc:
            raise SolarClientError("Solar API request timed out") from exc
        except httpx.HTTPError as exc:
            raise SolarClientError("Solar API transport failed") from exc

        if response.status_code < 200 or response.status_code >= 300:
            raise SolarClientError(f"Solar API returned HTTP {response.status_code}")
        try:
            response_payload = response.json()
        except ValueError as exc:
            raise SolarClientError("Solar API returned invalid JSON") from exc
        if not isinstance(response_payload, Mapping):
            raise SolarClientError("Solar API response must be a JSON object")

        choices = response_payload.get("choices")
        if (
            not isinstance(choices, Sequence)
            or isinstance(choices, (str, bytes, bytearray))
            or not choices
        ):
            raise SolarClientError("Solar API response has no choices")
        first_choice = choices[0]
        if not isinstance(first_choice, Mapping):
            raise SolarClientError("Solar API choice must be an object")
        message = first_choice.get("message")
        if not isinstance(message, Mapping):
            raise SolarClientError("Solar API choice has no message")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise SolarClientError("Solar API returned empty content")
        return content.strip()

    async def close(self) -> None:
        """Close an internally-created transport."""

        if self._owns_http_client and self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def __aenter__(self) -> "SolarClient":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object | None,
    ) -> None:
        del exc_type, exc_value, traceback
        await self.close()


async def answer_policy_question(
    question: str,
    policy: Mapping[str, object],
    *,
    client: SolarClient | None = None,
) -> str:
    """Answer one question without accepting or storing chat history."""

    messages = build_policy_qa_messages(question, policy)
    if client is not None:
        return await client.complete(messages, temperature=0.2)
    async with SolarClient() as solar_client:
        return await solar_client.complete(messages, temperature=0.2)
