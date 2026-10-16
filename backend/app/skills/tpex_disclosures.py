"""TPEx OTC daily material disclosures from a single fixed official endpoint.

Shares TWSE's vetted ROC date, canonical full-row identity, and Asia/Taipei
timestamp parsing; uses disjoint OTC source and document identity namespaces.
No graph relations or verified claims are produced here.
"""
from __future__ import annotations

import httpx

from app.skills.twse_disclosures import (
    DisclosureSnapshot, DisclosureSourceError, MAX_BYTES, parse_disclosures,
)

TPEX_DISCLOSURE_URL = "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap04_O"
TPEX_DISCLOSURE_DATASET = "https://data.gov.tw/dataset/18418"


def parse_tpex_disclosures(payload: bytes, *, retrieved_at=None) -> DisclosureSnapshot:
    return parse_disclosures(
        payload, retrieved_at=retrieved_at, source_url=TPEX_DISCLOSURE_URL,
        dataset_url=TPEX_DISCLOSURE_DATASET,
        company_prefix="tpex-otc", document_prefix="tpex-material",
    )


class TPExDisclosureConnector:
    """MockTransport-friendly fetch with strict size, timeout and redirect limits."""

    def __init__(self, *, transport: httpx.BaseTransport | None = None, timeout: float = 12):
        if not 0 < timeout <= 30:
            raise ValueError("Invalid timeout")
        self.transport = transport
        self.timeout = timeout

    def fetch(self) -> DisclosureSnapshot:
        try:
            with httpx.Client(
                transport=self.transport, timeout=self.timeout, follow_redirects=False,
                headers={"User-Agent": "DominoAI-MVP/0.1 (official public disclosures)",
                         "Accept": "application/json"},
            ) as client:
                with client.stream("GET", TPEX_DISCLOSURE_URL) as response:
                    if response.status_code != 200:
                        raise DisclosureSourceError(f"TPEx disclosure HTTP {response.status_code}")
                    length = response.headers.get("content-length")
                    if length and length.isdecimal() and int(length) > MAX_BYTES:
                        raise DisclosureSourceError("TPEx disclosure content-length too large")
                    pieces = []
                    total = 0
                    for piece in response.iter_bytes():
                        total += len(piece)
                        if total > MAX_BYTES:
                            raise DisclosureSourceError("TPEx disclosure body too large")
                        pieces.append(piece)
            return parse_tpex_disclosures(b"".join(pieces))
        except httpx.RequestError as exc:
            raise DisclosureSourceError("TPEx disclosure source unavailable") from exc
