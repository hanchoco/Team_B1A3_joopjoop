"""온통청년 policy collection and normalization.

All access to the external youth-policy API is centralized here. Configuration
is lazy so importing the backend does not require an API key.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone

import httpx

DEFAULT_YOUTH_POLICY_API_URL = "https://www.youthcenter.go.kr/go/ythip/getPlcy"
DEFAULT_PAGE_SIZE = 100
_DATE_PATTERN = re.compile(
    r"(?P<year>\d{4})[.\-/년]?\s*(?P<month>\d{1,2})[.\-/월]?\s*" r"(?P<day>\d{1,2})일?"
)
# "2026.3.30 ~ 5.29"처럼 종료일 표기에 연도가 생략되는 경우가 있어서, 연도 없는
# 월.일만도 매칭할 수 있어야 한다 (시작일과 같은 해로 채워 넣는다).
_PARTIAL_DATE_PATTERN = re.compile(r"(?P<month>\d{1,2})[.\-/월]\s*(?P<day>\d{1,2})일?")


class YouthPolicyAPIError(RuntimeError):
    """Raised for invalid API configuration, transport, or response data."""


class PolicyNormalizationError(ValueError):
    """Raised when a source record cannot form a valid policy."""


@dataclass(frozen=True, slots=True)
class NormalizedPolicy:
    """External policy represented with the database-facing field names."""

    source: str
    external_id: str
    title: str
    summary: str
    description: str
    support_target_text: str
    support_content_text: str
    application_method: str
    provider_name: str
    application_url: str
    application_start_date: str | None
    application_end_date: str | None
    is_ongoing: bool
    published_date: str | None
    status: str
    raw_payload: dict[str, object]
    source_updated_at: str
    subcategory: str
    region_scope: str
    region_code: str
    contact: str
    original_text: str
    is_active: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _json_safe(value: object) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_json_safe(item) for item in value]
    return str(value)


def _raw_payload(record: Mapping[str, object]) -> dict[str, object]:
    safe = _json_safe(record)
    if not isinstance(safe, dict):
        raise PolicyNormalizationError("raw policy must be a JSON object")
    return safe


def _first_value(record: Mapping[str, object], *keys: str) -> object | None:
    for key in keys:
        value = record.get(key)
        if value is not None and value != "":
            return value
    return None


def _first_text(record: Mapping[str, object], *keys: str) -> str:
    value = _first_value(record, *keys)
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return ", ".join(str(item).strip() for item in value if str(item).strip())
    return str(value).strip()


def _limited_text(value: str, max_length: int) -> str:
    """Fit display text to the model column while raw_payload keeps the source."""

    if len(value) <= max_length:
        return value
    if max_length == 1:
        return value[:1]
    return f"{value[: max_length - 1]}…"


def _is_truncated_month(text: str, match: re.Match[str]) -> bool:
    """Reject a match that mis-splits an incomplete "YYYY년 MM월" fragment.

    _DATE_PATTERN's month/day groups are optional-length, so on a day-less
    fragment like "2028년 12월까지" the mandatory day group backtracks into
    the month digits (month="1", day="2") instead of failing outright -
    misreading it as 2028-01-02. A genuine day is never immediately followed
    by "월" in the source text, so that's a reliable tell that the day group
    actually stole digits meant for the month.
    """
    return text[match.end() : match.end() + 1] == "월"


def _parse_date_text(value: object | None) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    match = _DATE_PATTERN.search(text)
    if match is None:
        return None
    try:
        parsed = date(
            int(match.group("year")),
            int(match.group("month")),
            int(match.group("day")),
        )
    except ValueError:
        return None
    return parsed.isoformat()


def _application_dates(
    record: Mapping[str, object],
) -> tuple[str | None, str | None, bool]:
    period_text = _first_text(
        record,
        "applicationPeriod",
        "application_period",
        "aplyYmd",
        "rqutPrdCn",
        # 위 필드가 전부 비어있을 때만 쓰는 최후 대체값. bizPrdEtcCn(기타 사업기간 설명)에
        # 신청기간이 자유텍스트로만 적혀 있고 구조화 필드(bizPrdBgngYmd 등)도 비어있는
        # 정책이 실제로 있었다(동일 프로그램의 다른 지역 변형 정책은 구조화 필드에 같은
        # 날짜가 들어있어서 비교로 확인함).
        "bizPrdEtcCn",
    )
    is_ongoing = any(keyword in period_text for keyword in ("상시", "수시", "예산 소진"))
    # aplyYmd/rqutYmd(신청·모집기간)가 실제 마감 기준이다. bizPrdYmd(사업 운영기간)는
    # 신청기간이 아예 없는 정책에서만 최후 대체값으로 쓴다 - 운영기간을 신청기간보다
    # 먼저 채택하면 신청 마감/알림 스케줄이 실제 마감일과 어긋난다.
    start = _parse_date_text(
        _first_value(
            record,
            "applicationStartDate",
            "application_start_date",
            "aplyBgngYmd",
            "rqutBgngYmd",
            "bizPrdBgngYmd",
        )
    )
    end = _parse_date_text(
        _first_value(
            record,
            "applicationEndDate",
            "application_end_date",
            "aplyEndYmd",
            "rqutEndYmd",
            "bizPrdEndYmd",
        )
    )
    period_matches = [
        m for m in _DATE_PATTERN.finditer(period_text) if not _is_truncated_month(period_text, m)
    ]
    if start is None and period_matches:
        start = _parse_date_text(period_matches[0].group(0))
    if end is None and len(period_matches) >= 2:
        end = _parse_date_text(period_matches[1].group(0))
    if end is None and start is not None:
        search_from = period_matches[0].end() if period_matches else 0
        partial = _PARTIAL_DATE_PATTERN.search(period_text, search_from)
        if partial:
            start_year = date.fromisoformat(start).year
            end = _parse_date_text(f"{start_year}.{partial.group('month')}.{partial.group('day')}")
    if is_ongoing:
        end = None
    return start, end, is_ongoing


def _support_target(record: Mapping[str, object]) -> str:
    explicit = _first_text(
        record,
        "supportTarget",
        "support_target_text",
        "sprtTrgtCn",
        "sporTrgtCn",
    )
    if explicit:
        return explicit
    parts: list[str] = []
    for label, keys in (
        ("연령", ("ageInfo", "sprtTrgtAgeCn")),
        ("취업상태", ("empmSttsCn", "jobStatus")),
        ("학력", ("accrRqisCn", "education")),
        ("전공", ("majrRqisCn", "major")),
        ("특화분야", ("splzRlmRqisCn", "specialRequirement")),
        ("참여제한", ("prcpCn", "restriction")),
    ):
        value = _first_text(record, *keys)
        if value:
            parts.append(f"{label}: {value}")
    return "\n".join(parts)


def _original_text(record: Mapping[str, object]) -> str:
    fields = (
        ("정책명", ("plcyNm", "polyBizSjnm", "title", "policyName")),
        ("정책설명", ("plcyExplnCn", "polyItcnCn", "description")),
        ("지원대상", ("sprtTrgtCn", "sporTrgtCn", "supportTarget")),
        ("지원내용", ("plcySprtCn", "sporCn", "supportContent")),
        ("신청기간", ("aplyYmd", "rqutPrdCn", "applicationPeriod")),
        ("신청방법", ("plcyAplyMthdCn", "rqutProcCn", "applicationMethod")),
        ("제출서류", ("pstnPaprCn", "requiredDocuments")),
        ("문의처", ("cherCtpcCn", "cnsgNmor", "contact")),
    )
    lines: list[str] = []
    seen: set[str] = set()
    for label, keys in fields:
        value = _first_text(record, *keys)
        if value and value not in seen:
            lines.append(f"{label}: {value}")
            seen.add(value)
    return "\n".join(lines)


def _active_status(record: Mapping[str, object]) -> tuple[str, bool]:
    raw_status = _first_text(
        record,
        "status",
        "policyStatus",
        "plcySttsNm",
        "bizSttsNm",
    )
    upper_status = raw_status.upper()
    active_flag = _first_text(record, "isActive", "is_active", "useYn")
    if any(marker in upper_status for marker in ("폐지", "보관", "ARCHIVED")):
        status = "ARCHIVED"
    elif any(marker in upper_status for marker in ("종료", "중단", "INACTIVE", "CLOSED")):
        status = "CLOSED"
    elif any(marker in upper_status for marker in ("초안", "검토", "DRAFT")):
        status = "DRAFT"
    else:
        status = "ACTIVE"
    is_active = status == "ACTIVE"
    if active_flag.upper() in {"N", "NO", "FALSE", "0"}:
        is_active = False
        if status == "ACTIVE":
            status = "CLOSED"
    return status, is_active


def normalize_policy(
    record: Mapping[str, object],
    *,
    fetched_at: datetime | None = None,
) -> NormalizedPolicy:
    """Normalize one 온통청년 response row without discarding the raw payload."""

    external_id = _first_text(
        record,
        "plcyNo",
        "bizId",
        "policyId",
        "policy_id",
        "id",
    )
    title = _first_text(
        record,
        "plcyNm",
        "polyBizSjnm",
        "policyName",
        "title",
    )
    if not external_id:
        raise PolicyNormalizationError("policy external_id is missing")
    if len(external_id) > 100:
        raise PolicyNormalizationError("policy external_id exceeds 100 characters")
    if not title:
        raise PolicyNormalizationError(f"policy title is missing for external_id={external_id}")

    start_date, end_date, is_ongoing = _application_dates(record)
    status, is_active = _active_status(record)
    observed_at = fetched_at or datetime.now(timezone.utc)
    source_updated = _first_value(
        record,
        "lastMdfcnDt",
        "updatedAt",
        "sourceUpdatedAt",
        "modDt",
    )
    if isinstance(source_updated, datetime):
        source_updated_at = source_updated.astimezone(timezone.utc).isoformat()
    else:
        parsed_source_date = _parse_date_text(source_updated)
        source_updated_at = parsed_source_date or observed_at.isoformat()

    description = _first_text(
        record,
        "plcyExplnCn",
        "polyItcnCn",
        "description",
        "policyDescription",
    )
    support_content = _first_text(
        record,
        "plcySprtCn",
        "sporCn",
        "supportContent",
        "support_content_text",
    )
    summary = _first_text(record, "summary", "policySummary") or description
    return NormalizedPolicy(
        source="ONTONG_YOUTH",
        external_id=external_id,
        title=_limited_text(title, 255),
        summary=_limited_text(summary, 500),
        description=description,
        support_target_text=_support_target(record),
        support_content_text=support_content,
        application_method=_first_text(
            record,
            "plcyAplyMthdCn",
            "rqutProcCn",
            "applicationMethod",
            "application_method",
        ),
        provider_name=_limited_text(
            _first_text(
                record,
                "operInstCdNm",
                "sprvsnInstCdNm",
                "mngtMson",
                "providerName",
                "provider_name",
            ),
            255,
        ),
        application_url=_limited_text(
            _first_text(
                record,
                "aplyUrlAddr",
                "rqutUrla",
                "rqutSuptRlte",
                "applicationUrl",
                "application_url",
            ),
            1_000,
        ),
        application_start_date=start_date,
        application_end_date=end_date,
        is_ongoing=is_ongoing,
        published_date=_parse_date_text(
            _first_value(
                record,
                "frstRegDt",
                "publishedDate",
                "published_date",
                "regDt",
            )
        ),
        status=status,
        raw_payload=_raw_payload(record),
        source_updated_at=source_updated_at,
        subcategory=_limited_text(
            _first_text(
                record,
                "mclsfNm",
                "lclsfNm",
                "bizTycdSel",
                "subcategory",
            ),
            100,
        ),
        region_scope=_limited_text(
            _first_text(
                record,
                "regionScope",
                "region_scope",
                "rgtrHghrkInstCdNm",
                "polyBizSecdNm",
                "regionName",
            ),
            20,
        ),
        region_code=_limited_text(
            _first_text(
                record,
                "regionCode",
                "region_code",
                "rgtrHghrkInstCd",
                "polyBizSecd",
                "zipCd",
            ),
            20,
        ),
        contact=_limited_text(
            _first_text(
                record,
                "cherCtpcCn",
                "cnsgNmor",
                "contact",
                "contactInfo",
            ),
            255,
        ),
        original_text=_original_text(record),
        is_active=is_active,
    )


def _mapping_list(value: object) -> list[Mapping[str, object]] | None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return None
    if not value:
        return []
    if all(isinstance(item, Mapping) for item in value):
        return [item for item in value if isinstance(item, Mapping)]
    return None


def _find_records(payload: object) -> list[Mapping[str, object]]:
    direct = _mapping_list(payload)
    if direct is not None:
        return direct
    if not isinstance(payload, Mapping):
        raise YouthPolicyAPIError("youth policy response has no item array")

    preferred_keys = (
        "youthPolicyList",
        "youthPlcyList",
        "policies",
        "items",
        "data",
        "result",
        "list",
    )
    for key in preferred_keys:
        if key not in payload:
            continue
        candidate = _mapping_list(payload[key])
        if candidate is not None:
            return candidate
    for key in preferred_keys:
        nested = payload.get(key)
        if isinstance(nested, Mapping):
            try:
                return _find_records(nested)
            except YouthPolicyAPIError:
                continue
    for nested in payload.values():
        if isinstance(nested, Mapping):
            try:
                return _find_records(nested)
            except YouthPolicyAPIError:
                continue
    raise YouthPolicyAPIError("youth policy response has no item array")


def _find_total(payload: object) -> int | None:
    if not isinstance(payload, Mapping):
        return None
    for key in ("totalCount", "total", "totCnt", "totalElements"):
        value = payload.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    for value in payload.values():
        if isinstance(value, Mapping):
            total = _find_total(value)
            if total is not None:
                return total
    return None


class YouthPolicyClient:
    """Async 온통청년 API client with bounded pagination."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key or os.getenv("YOUTH_POLICY_API_KEY") or None
        self._base_url = (
            base_url or os.getenv("YOUTH_POLICY_API_URL") or DEFAULT_YOUTH_POLICY_API_URL
        )
        timeout = timeout_seconds
        if timeout is None:
            timeout_text = os.getenv("YOUTH_POLICY_TIMEOUT_SECONDS", "30")
            try:
                timeout = float(timeout_text)
            except ValueError as exc:
                raise YouthPolicyAPIError("YOUTH_POLICY_TIMEOUT_SECONDS must be a number") from exc
        if timeout <= 0:
            raise YouthPolicyAPIError("timeout_seconds must be positive")
        self._timeout_seconds = timeout
        self._http_client = http_client
        self._owns_http_client = http_client is None

    def _client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=self._timeout_seconds,follow_redirects=True)
        return self._http_client

    def _request_key(self) -> str:
        api_key = (self._api_key or "").strip()
        if not api_key:
            raise YouthPolicyAPIError("YOUTH_POLICY_API_KEY is required when collecting policies")
        return api_key

    async def fetch_page(
        self,
        *,
        page_index: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        filters: Mapping[str, str] | None = None,
    ) -> tuple[list[Mapping[str, object]], int | None]:
        """Fetch one unmodified response page."""

        if page_index < 1:
            raise ValueError("page_index must be at least 1")
        if page_size < 1 or page_size > 1_000:
            raise ValueError("page_size must be between 1 and 1000")
        params: dict[str, str | int] = {
            "apiKeyNm": self._request_key(),
            "pageNum": page_index,
            "pageSize": page_size,
            "rtnType": "json",
            }
        if filters is not None:
            params.update(
                {str(key): str(value) for key, value in filters.items() if str(value).strip()}
            )
        try:
            response = await self._client().get(
                self._base_url,
                params=params,
                headers={"Accept": "application/json"},
            )
        except httpx.TimeoutException as exc:
            raise YouthPolicyAPIError("youth policy API request timed out") from exc
        except httpx.HTTPError as exc:
            raise YouthPolicyAPIError("youth policy API transport failed") from exc
        if response.status_code < 200 or response.status_code >= 300:
            raise YouthPolicyAPIError(f"youth policy API returned HTTP {response.status_code}")
        try:
            payload = response.json()
        except (json.JSONDecodeError, ValueError) as exc:
            raise YouthPolicyAPIError("youth policy API returned invalid JSON") from exc
        return _find_records(payload), _find_total(payload)

    async def collect(
        self,
        *,
        page_size: int = DEFAULT_PAGE_SIZE,
        max_pages: int = 100,
        limit: int | None = None,
        filters: Mapping[str, str] | None = None,
        exclude_external_ids: Sequence[str] | None = None,
    ) -> list[NormalizedPolicy]:
        """Collect and normalize policy pages with explicit safety bounds.

        ``exclude_external_ids`` skips records already known to the caller
        (e.g. policies already persisted), so a repeated collection run
        pages past prior results instead of returning the same first page
        every time.
        """

        if max_pages < 1:
            raise ValueError("max_pages must be positive")
        if limit is not None and limit < 1:
            raise ValueError("limit must be positive")
        excluded = set(exclude_external_ids) if exclude_external_ids else set()
        collected: list[NormalizedPolicy] = []
        records_seen = 0
        observed_at = datetime.now(timezone.utc)
        for page_index in range(1, max_pages + 1):
            records, total = await self.fetch_page(
                page_index=page_index,
                page_size=page_size,
                filters=filters,
            )
            records_seen += len(records)
            for record in records:
                normalized = normalize_policy(record, fetched_at=observed_at)
                if normalized.external_id in excluded:
                    continue
                collected.append(normalized)
                if limit is not None and len(collected) >= limit:
                    return collected
            if not records or len(records) < page_size:
                break
            if total is not None and records_seen >= total:
                break
        return collected

    async def close(self) -> None:
        if self._owns_http_client and self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def __aenter__(self) -> "YouthPolicyClient":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object | None,
    ) -> None:
        del exc_type, exc_value, traceback
        await self.close()
