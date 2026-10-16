"""Bounded TPEx OTC company profiles from the official open-data endpoint.

The official dataset documents company profiles, not supplier/customer links.
TPEx API uses English field names, unlike TWSE's Chinese keys.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
import json
import re

import httpx

from app.skills.twse_companies import CompanyProfile, CompanySnapshot, CompanySourceError

TPEX_COMPANY_API = "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O"
TPEX_DATASET_PAGE = "https://data.gov.tw/dataset/25036"
MAX_RESPONSE_BYTES = 8_000_000
CODE_PATTERN = re.compile(r"^[0-9A-Za-z]{4,8}$")


def parse_tpex_profiles(payload: bytes, *, retrieved_at: datetime | None = None) -> CompanySnapshot:
    if not payload or len(payload) > MAX_RESPONSE_BYTES:
        raise CompanySourceError("TPEx payload missing or beyond 8 MB budget")
    try:
        rows = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CompanySourceError("TPEx profile payload is not valid UTF-8 JSON") from exc
    if not isinstance(rows, list) or not rows or len(rows) > 5000:
        raise CompanySourceError("TPEx profile response must be a non-empty bounded JSON array")

    records: list[CompanyProfile] = []
    seen: set[str] = set()
    rejected = 0
    for row in rows:
        if not isinstance(row, dict):
            rejected += 1
            continue
        code = row.get("SecuritiesCompanyCode")
        name = row.get("CompanyName")
        if not isinstance(code, str) or not CODE_PATTERN.fullmatch(code.strip()) or not isinstance(name, str) or not name.strip():
            rejected += 1
            continue
        code = code.strip()
        if code in seen:
            raise CompanySourceError(f"Duplicate TPEx company code: {code}")
        seen.add(code)
        industry = row.get("SecuritiesIndustryCode")
        report_date = row.get("Date")
        records.append(CompanyProfile(
            company_key=f"tpex-otc:{code}",
            ticker=code,
            name=name.strip()[:300],
            industry=industry.strip()[:100] if isinstance(industry, str) and industry.strip() else None,
            market="otc",
            source_url=TPEX_COMPANY_API,
            dataset_url=TPEX_DATASET_PAGE,
            source_report_date_raw=str(report_date).strip() if report_date is not None else None,
        ))

    if not records:
        raise CompanySourceError("TPEx feed contains no valid company profiles")
    observed = retrieved_at or datetime.now(timezone.utc)
    if observed.tzinfo is None:
        raise ValueError("retrieved_at must be timezone-aware")
    return CompanySnapshot(
        profiles=tuple(records),
        retrieved_at=observed,
        payload_sha256=sha256(payload).hexdigest(),
        source_url=TPEX_COMPANY_API,
        dataset_url=TPEX_DATASET_PAGE,
        rejected_rows=rejected,
    )


class TPExCompanyConnector:
    def __init__(self, *, transport: httpx.BaseTransport | None = None, timeout: float = 12):
        if not 0 < timeout <= 30:
            raise ValueError("timeout outside safe range")
        self.transport = transport
        self.timeout = timeout

    def fetch(self) -> CompanySnapshot:
        try:
            with httpx.Client(
                transport=self.transport,
                timeout=self.timeout,
                follow_redirects=False,
                headers={"User-Agent": "DominoAI-MVP/0.1 (official public-data research)",
                         "Accept": "application/json"},
            ) as client:
                with client.stream("GET", TPEX_COMPANY_API) as response:
                    if response.status_code != 200:
                        raise CompanySourceError(f"TPEx request returned HTTP {response.status_code}")
                    length = response.headers.get("content-length")
                    if length and length.isdecimal() and int(length) > MAX_RESPONSE_BYTES:
                        raise CompanySourceError("TPEx content-length exceeds size budget")
                    chunks: list[bytes] = []
                    total = 0
                    for chunk in response.iter_bytes():
                        total += len(chunk)
                        if total > MAX_RESPONSE_BYTES:
                            raise CompanySourceError("TPEx response exceeds size budget")
                        chunks.append(chunk)
            return parse_tpex_profiles(b"".join(chunks))
        except httpx.RequestError as exc:
            raise CompanySourceError("TPEx endpoint unavailable") from exc
