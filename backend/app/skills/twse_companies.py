"""TWSE listed-company profile connector (government open data dataset 18419).

Only profile facts are imported. Company profiles do not establish
supplier/customer links, dependencies, or risk propagation eligibility.
No network work occurs on module import.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from typing import Callable

import httpx

TWSE_COMPANY_API = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
TWSE_DATASET_PAGE = "https://data.gov.tw/dataset/18419"
_MAX_RESPONSE_BYTES = 8_000_000
_TICKER = re.compile(r"^[0-9A-Za-z]{4,8}$")


class CompanySourceError(ValueError):
    """Remote feed was unavailable or incompatible with the expected schema."""


@dataclass(frozen=True)
class CompanyProfile:
    company_key: str
    ticker: str
    name: str
    industry: str | None
    market: str
    source_url: str
    dataset_url: str
    source_report_date_raw: str | None


@dataclass(frozen=True)
class CompanySnapshot:
    profiles: tuple[CompanyProfile, ...]
    retrieved_at: datetime
    payload_sha256: str
    source_url: str
    dataset_url: str
    rejected_rows: int


def parse_twse_profiles(payload: bytes, *, retrieved_at: datetime | None = None) -> CompanySnapshot:
    """Validate an already acquired JSON snapshot, without asserting freshness."""
    if not payload or len(payload) > _MAX_RESPONSE_BYTES:
        raise CompanySourceError("TWSE payload missing or beyond 8 MB budget")
    try:
        rows = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CompanySourceError("TWSE profile payload is not valid UTF-8 JSON") from exc
    if not isinstance(rows, list) or not rows:
        raise CompanySourceError("TWSE profile response must be a non-empty JSON array")
    if len(rows) > 5000:
        raise CompanySourceError("TWSE profile row count exceeds safety cap")

    profiles = []
    seen = set()
    rejected = 0
    for row in rows:
        if not isinstance(row, dict):
            rejected += 1
            continue
        ticker = row.get("公司代號")
        name = row.get("公司名稱")
        if not isinstance(ticker, str) or not _TICKER.fullmatch(ticker.strip()) or not isinstance(name, str) or not name.strip():
            rejected += 1
            continue
        ticker = ticker.strip()
        if ticker in seen:
            raise CompanySourceError(f"Duplicate TWSE company code: {ticker}")
        seen.add(ticker)
        industry = row.get("產業別")
        report_date = row.get("出表日期")
        profiles.append(CompanyProfile(
            company_key=f"twse-listed:{ticker}",
            ticker=ticker,
            name=name.strip()[:300],
            industry=industry.strip()[:100] if isinstance(industry, str) and industry.strip() else None,
            market="listed",
            source_url=TWSE_COMPANY_API,
            dataset_url=TWSE_DATASET_PAGE,
            # TWSE sometimes uses ROC dates. Keep as raw source field rather
            # than silently interpreting it as an ISO publication timestamp.
            source_report_date_raw=str(report_date).strip() if report_date is not None else None,
        ))
    if not profiles:
        raise CompanySourceError("TWSE feed contains no valid company profiles")
    observed = retrieved_at or datetime.now(timezone.utc)
    if observed.tzinfo is None:
        raise ValueError("retrieved_at must be timezone-aware")
    return CompanySnapshot(
        profiles=tuple(profiles),
        retrieved_at=observed,
        payload_sha256=sha256(payload).hexdigest(),
        source_url=TWSE_COMPANY_API,
        dataset_url=TWSE_DATASET_PAGE,
        rejected_rows=rejected,
    )


class TWSECompanyConnector:
    """Bounded fetch of a FIXED official HTTPS endpoint.

    Inject httpx transport for deterministic tests; no arbitrary URL input or
    cross-host redirects. Live use must respect the publisher's usage limits.
    """

    def __init__(self, *, transport: httpx.BaseTransport | None = None, timeout: float = 12):
        if not 0 < timeout <= 30:
            raise ValueError("timeout outside safe range")
        self.transport = transport
        self.timeout = timeout

    def fetch(self) -> CompanySnapshot:
        try:
            with httpx.Client(transport=self.transport, timeout=self.timeout,
                              follow_redirects=False,
                              headers={"User-Agent": "DominoAI-MVP/0.1 (public-data research)",
                                       "Accept": "application/json"}) as client:
                with client.stream("GET", TWSE_COMPANY_API) as response:
                    if response.status_code != 200:
                        raise CompanySourceError(f"TWSE request returned HTTP {response.status_code}")
                    length = response.headers.get("content-length")
                    if length and length.isdecimal() and int(length) > _MAX_RESPONSE_BYTES:
                        raise CompanySourceError("TWSE content-length exceeds size budget")
                    chunks = []
                    total = 0
                    for chunk in response.iter_bytes():
                        total += len(chunk)
                        if total > _MAX_RESPONSE_BYTES:
                            raise CompanySourceError("TWSE response exceeds size budget")
                        chunks.append(chunk)
                return parse_twse_profiles(b"".join(chunks))
        except httpx.RequestError as exc:
            raise CompanySourceError("TWSE endpoint unavailable") from exc
