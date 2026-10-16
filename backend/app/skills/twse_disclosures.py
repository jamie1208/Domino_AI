"""Fixed-endpoint TWSE listed-company material disclosures (daily snapshot).

Retrieve issuer announcements only from official HTTPS TWSE OpenAPI. Raw
announcement text is *not* independently verified evidence of a business link.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from hashlib import sha256
import json
import re
import httpx

from app.skills.document_archive import DocumentInput

URL = "https://openapi.twse.com.tw/v1/opendata/t187ap04_L"
DATASET = "https://data.gov.tw/dataset/18415"
MAX_BYTES = 12_000_000
MAX_ROWS = 10000
CODE = re.compile(r"^[0-9A-Za-z]{4,8}$")
ROC = re.compile(r"^(\d{3})(\d{2})(\d{2})$")
TIME = re.compile(r"^\d{1,6}$")


class DisclosureSourceError(ValueError):
    pass


@dataclass(frozen=True)
class DisclosureSnapshot:
    documents: tuple[DocumentInput, ...]
    retrieved_at: datetime
    source_url: str
    dataset_url: str
    payload_sha256: str
    rejected_rows: int


def _roc_date(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("Missing ROC date")
    match = ROC.fullmatch(value.strip().replace("/", ""))
    if not match:
        raise ValueError("Expected ROC date YYYMMDD")
    year, month, day = (int(v) for v in match.groups())
    return date(year + 1911, month, day).isoformat()


def parse_disclosures(payload: bytes, *, retrieved_at: datetime | None = None) -> DisclosureSnapshot:
    if not payload or len(payload) > MAX_BYTES:
        raise DisclosureSourceError("Announcement payload exceeds size budget or is empty")
    try:
        rows = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise DisclosureSourceError("TWSE announcements are not UTF-8 JSON") from exc
    if not isinstance(rows, list) or len(rows) > MAX_ROWS:
        raise DisclosureSourceError("Expected a bounded JSON array")
    observed = retrieved_at or datetime.now(timezone.utc)
    if observed.tzinfo is None:
        raise ValueError("retrieved_at requires timezone")
    accepted: list[DocumentInput] = []
    seen: set[str] = set()
    rejected = 0
    for row in rows:
        if not isinstance(row, dict):
            rejected += 1
            continue
        # Official schema versions may include trailing spaces in 主旨 key.
        normalized = {k.strip(): v for k, v in row.items() if isinstance(k, str)}
        code = normalized.get("公司代號")
        title = normalized.get("主旨")
        body = normalized.get("說明")
        speech_date = normalized.get("發言日期")
        speech_time = normalized.get("發言時間")
        if not (isinstance(code, str) and CODE.fullmatch(code.strip())
                and isinstance(title, str) and title.strip()
                and isinstance(body, str) and body.strip()
                and isinstance(speech_time, str) and TIME.fullmatch(speech_time.strip())):
            rejected += 1
            continue
        try:
            published = _roc_date(speech_date)
        except ValueError:
            rejected += 1
            continue
        code = code.strip()
        clock = speech_time.strip().zfill(6)
        if int(clock[:2]) > 23 or int(clock[2:4]) > 59 or int(clock[4:]) > 59:
            rejected += 1
            continue
        # Stable within issuer/date/time; if one issuer issues multiple messages
        # in a single second, don't silently collapse their distinct disclosures.
        identity = f"{code}:{published}:{clock}"
        suffix = sha256((title.strip() + "\n" + body.strip()).encode()).hexdigest()[:16]
        document_key = f"twse-material:{identity}:{suffix}"
        if document_key in seen:
            continue
        seen.add(document_key)
        # The live endpoint exposes a daily batch, not a permanent item URL.
        # Store the honest batch URL and identify the document by stable key.
        accepted.append(DocumentInput(
            document_key=document_key,
            company_key=f"twse-listed:{code}",
            title=title.strip(),
            source_url=URL,
            published_at=published,
            text=body.strip(),
            source_type="material_announcement",
        ))
    if rows and not accepted:
        raise DisclosureSourceError("TWSE disclosure schema yielded zero valid rows")
    return DisclosureSnapshot(tuple(accepted), observed, URL, DATASET,
                              sha256(payload).hexdigest(), rejected)


class TWSEDisclosureConnector:
    def __init__(self, *, transport: httpx.BaseTransport | None = None, timeout: float = 12):
        if not 0 < timeout <= 30:
            raise ValueError("Invalid timeout")
        self.transport = transport
        self.timeout = timeout

    def fetch(self) -> DisclosureSnapshot:
        try:
            with httpx.Client(
                transport=self.transport, timeout=self.timeout, follow_redirects=False,
                headers={"User-Agent": "DominoAI-MVP/0.1 (public disclosures)",
                         "Accept": "application/json"},
            ) as client:
                with client.stream("GET", URL) as response:
                    if response.status_code != 200:
                        raise DisclosureSourceError(f"TWSE disclosure HTTP {response.status_code}")
                    declared = response.headers.get("content-length")
                    if declared and declared.isdecimal() and int(declared) > MAX_BYTES:
                        raise DisclosureSourceError("TWSE disclosure content-length too large")
                    chunks = []
                    total = 0
                    for chunk in response.iter_bytes():
                        total += len(chunk)
                        if total > MAX_BYTES:
                            raise DisclosureSourceError("TWSE disclosure body too large")
                        chunks.append(chunk)
            return parse_disclosures(b"".join(chunks))
        except httpx.RequestError as exc:
            raise DisclosureSourceError("TWSE disclosure source unavailable") from exc
