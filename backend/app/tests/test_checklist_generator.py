"""Tests for source-grounded policy document generation."""

import asyncio

from app.services.ai.checklist_generator import generate_checklist


class FakeSolarClient:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response
        self.calls = 0

    async def complete_json(self, _system_prompt: str, _user_input: str) -> dict[str, object]:
        self.calls += 1
        return self.response


def test_empty_document_source_does_not_call_ai() -> None:
    client = FakeSolarClient({"documents": [{"document_name": "임의 서류"}]})

    documents = asyncio.run(
        generate_checklist(
            {"title": "정책", "raw_payload": {"sbmsnDcmntCn": ""}},
            client=client,
        )
    )

    assert documents == []
    assert client.calls == 0


def test_generic_guidance_is_not_treated_as_required_document() -> None:
    client = FakeSolarClient({"documents": [{"document_name": "붙임파일"}]})

    documents = asyncio.run(
        generate_checklist(
            {
                "title": "정책",
                "raw_payload": {"sbmsnDcmntCn": "자세한 내용은 붙임파일을 확인하세요"},
            },
            client=client,
        )
    )

    assert documents == []
    assert client.calls == 0


def test_concrete_document_names_are_generated_from_alias_field() -> None:
    client = FakeSolarClient(
        {
            "documents": [
                {
                    "document_name": "주민등록초본",
                    "issuing_organization": None,
                    "issuing_method": None,
                }
            ]
        }
    )

    documents = asyncio.run(
        generate_checklist(
            {
                "title": "정책",
                "raw_payload": {"pstnPaprCn": "주민등록초본"},
            },
            client=client,
        )
    )

    assert [document.document_name for document in documents] == ["주민등록초본"]
    assert documents[0].issuing_organization is None
    assert client.calls == 1


def test_inferred_document_metadata_is_removed_when_absent_from_source() -> None:
    client = FakeSolarClient(
        {
            "documents": [
                {
                    "document_name": "주민등록초본",
                    "required_reason": "주소 확인",
                    "issuing_organization": "정부24",
                    "issuing_method": "온라인 발급",
                    "issuing_url": "https://www.gov.kr",
                    "submission_format": "원본",
                    "is_required": True,
                }
            ]
        }
    )

    documents = asyncio.run(
        generate_checklist(
            {
                "title": "정책",
                "raw_payload": {"sbmsnDcmntCn": "주민등록초본"},
            },
            client=client,
        )
    )

    assert documents[0].document_name == "주민등록초본"
    assert documents[0].required_reason is None
    assert documents[0].issuing_organization is None
    assert documents[0].issuing_method is None
    assert documents[0].issuing_url is None
    assert documents[0].submission_format is None
