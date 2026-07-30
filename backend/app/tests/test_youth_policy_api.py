"""Unit tests for exclude_external_ids paging in YouthPolicyClient.collect()."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence

from app.integrations.youth_policy_api import YouthPolicyClient


class _FakePagedClient(YouthPolicyClient):
    """Serves canned pages without any real HTTP call."""

    def __init__(self, pages: Sequence[Sequence[Mapping[str, object]]]) -> None:
        super().__init__(api_key="test-key")
        self._pages = pages

    async def fetch_page(
        self,
        *,
        page_index: int = 1,
        page_size: int = 100,
        filters: Mapping[str, str] | None = None,
    ) -> tuple[list[Mapping[str, object]], int | None]:
        del page_size, filters
        if page_index > len(self._pages):
            return [], None
        return list(self._pages[page_index - 1]), None


def _record(external_id: str) -> dict[str, object]:
    return {"plcyNo": external_id, "plcyNm": f"정책 {external_id}"}


def test_collect_skips_known_external_ids_and_pages_forward() -> None:
    """A page that's entirely already-known must not stop collection short;
    it should page forward until new, non-excluded policies fill the limit."""

    client = _FakePagedClient(
        [
            [_record("A"), _record("B")],
            [_record("C"), _record("D")],
        ]
    )

    policies = asyncio.run(
        client.collect(page_size=2, max_pages=5, limit=2, exclude_external_ids={"A", "B"})
    )

    assert [p.external_id for p in policies] == ["C", "D"]


def test_collect_without_exclusions_returns_first_page() -> None:
    client = _FakePagedClient([[_record("A"), _record("B")]])

    policies = asyncio.run(client.collect(page_size=2, max_pages=5, limit=2))

    assert [p.external_id for p in policies] == ["A", "B"]


def test_collect_stops_at_max_pages_when_everything_is_excluded() -> None:
    client = _FakePagedClient([[_record("A")], [_record("B")]])

    policies = asyncio.run(
        client.collect(
            page_size=1,
            max_pages=2,
            limit=5,
            exclude_external_ids={"A", "B"},
        )
    )

    assert policies == []
