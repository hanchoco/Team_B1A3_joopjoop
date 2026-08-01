"""Unit tests for exclude_external_ids paging in YouthPolicyClient.collect()."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence

from app.integrations.youth_policy_api import YouthPolicyClient, normalize_policy


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


# ---------------------------------------------------------------------------
# 사업 신청기간(aply/rqut) vs 사업 운영기간(bizPrd) 우선순위 회귀 테스트
# ---------------------------------------------------------------------------


def test_application_period_prefers_recruitment_over_operation_period() -> None:
    """신청/모집기간(rqut)이 있으면 운영기간(bizPrd)보다 그걸 써야 한다."""

    record = {
        "plcyNo": "period-test-1",
        "plcyNm": "전남광주 청년 문화복지카드",
        "rqutBgngYmd": "20260201",
        "rqutEndYmd": "20260228",
        "bizPrdBgngYmd": "20260101",
        "bizPrdEndYmd": "20261201",
    }

    normalized = normalize_policy(record)

    assert normalized.application_start_date == "2026-02-01"
    assert normalized.application_end_date == "2026-02-28"


def test_application_period_falls_back_to_operation_period_when_absent() -> None:
    """신청기간 필드가 전혀 없으면 운영기간을 최후 대체값으로 쓴다."""

    record = {
        "plcyNo": "period-test-2",
        "plcyNm": "전남광주 청년 문화복지카드",
        "bizPrdBgngYmd": "20260101",
        "bizPrdEndYmd": "20261201",
    }

    normalized = normalize_policy(record)

    assert normalized.application_start_date == "2026-01-01"
    assert normalized.application_end_date == "2026-12-01"


# ---------------------------------------------------------------------------
# bizPrdEtcCn(기타 사업기간 설명) 자유텍스트에서 신청기간 파싱 - 구조화 필드가
# 전부 비어있는 정책에서 실제로 관찰된 케이스.
# ---------------------------------------------------------------------------


def test_application_period_parses_from_bizPrdEtcCn_dot_notation() -> None:
    """같은 프로그램의 다른 지역 변형(검단구)은 구조화 필드에 같은 날짜가
    있어서 대조 확인함 - 서해구는 bizPrdEtcCn 자유텍스트로만 적혀 있었다."""

    record = {
        "plcyNo": "seohae-test",
        "plcyNm": "(서해구) 인천시 청년월세 지원사업",
        "bizPrdEtcCn": "* 신청기간 : 2026. 3.30. 09시~5.29. 16시",
    }

    normalized = normalize_policy(record)

    assert normalized.application_start_date == "2026-03-30"
    assert normalized.application_end_date == "2026-05-29"


def test_application_period_parses_from_bizPrdEtcCn_korean_notation_and_ignores_unrelated_date() -> (
    None
):
    """영종구는 신청기간 뒤에 무관한 '지급기간: 2028년 12월까지'(일자 없음)가
    같은 텍스트에 있었다. 이 조각이 정규식 백트래킹으로 2028-01-02로
    잘못 파싱되던 버그의 재현 테스트."""

    record = {
        "plcyNo": "yeongjong-test",
        "plcyNm": "(영종구) 인천시 청년월세 지원사업",
        "bizPrdEtcCn": (
            "신청기간: 2026년 3월 30일(월) 09:00 ~ 5월 29일(금) 16:00\r\n"
            "지급기간: 2028년 12월까지"
        ),
    }

    normalized = normalize_policy(record)

    assert normalized.application_start_date == "2026-03-30"
    assert normalized.application_end_date == "2026-05-29"
