"""Versioned public-document text archive and deterministic paragraph chunker.

This module accepts *already lawfully acquired* text and explicit metadata.
It does not crawl, authenticate a source, parse PDFs or assert supply links.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from hashlib import sha256
from urllib.parse import urlsplit
import re

from app.schemas import Evidence, EvidenceKind, Scenario
from app.skills.researcher import ResearchBundle

MAX_DOCUMENT_CHARS = 300_000
MAX_CHUNKS = 800


@dataclass(frozen=True)
class DocumentInput:
    document_key: str
    company_key: str
    title: str
    source_url: str
    published_at: str
    text: str
    source_type: str = "company_disclosure"


@dataclass(frozen=True)
class DocumentChunk:
    ordinal: int
    start: int
    end: int
    content: str
    content_sha256: str


def normalize_document(raw: DocumentInput) -> DocumentInput:
    parsed = urlsplit(raw.source_url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Document source must be an HTTPS URL without embedded credentials")
    if not raw.document_key.strip() or len(raw.document_key) > 160:
        raise ValueError("Invalid document key")
    if not raw.company_key.startswith(("twse-listed:", "tpex-otc:")) or len(raw.company_key) > 160:
        raise ValueError("A market-scoped company key is required")
    if not raw.title.strip() or len(raw.title) > 600:
        raise ValueError("Invalid document title")
    if not raw.text.strip() or len(raw.text) > MAX_DOCUMENT_CHARS:
        raise ValueError("Document text missing or exceeds size budget")
    if raw.source_type not in ("company_disclosure", "annual_report", "material_announcement"):
        raise ValueError("Unsupported source type")
    try:
        parsed_date = date.fromisoformat(raw.published_at)
    except ValueError as exc:
        raise ValueError("published_at must be ISO YYYY-MM-DD") from exc
    if parsed_date.isoformat() != raw.published_at:
        raise ValueError("published_at must be canonical ISO YYYY-MM-DD")
    text = raw.text.replace("\r\n", "\n").replace("\r", "\n")
    return DocumentInput(
        document_key=raw.document_key.strip(),
        company_key=raw.company_key.strip(),
        title=raw.title.strip(),
        source_url=raw.source_url.strip(),
        published_at=raw.published_at,
        text=text,
        source_type=raw.source_type,
    )


def split_document(text: str, *, chunk_size: int = 800, overlap: int = 100) -> tuple[DocumentChunk, ...]:
    """Stable character offsets into stored normalized original text."""
    if not (100 <= chunk_size <= 4000 and 0 <= overlap < chunk_size):
        raise ValueError("Invalid chunk parameters")
    if not text or len(text) > MAX_DOCUMENT_CHARS:
        raise ValueError("Invalid document length")
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            # Prefer newline break near the end without losing position.
            newline = text.rfind("\n", start + chunk_size // 2, end)
            if newline != -1:
                end = newline + 1
        if end <= start:
            raise ValueError("Chunking made no progress")
        part = text[start:end]
        chunks.append(DocumentChunk(len(chunks), start, end, part, sha256(part.encode()).hexdigest()))
        if len(chunks) > MAX_CHUNKS:
            raise ValueError("Document exceeds chunk budget")
        if end == len(text):
            break
        start = max(start + 1, end - overlap)
    return tuple(chunks)


class ArchivedDocumentResearchProvider:
    """Keyword-only retrieval from vetted archive rows; unverified evidence output."""

    def __init__(self, records: list[tuple[DocumentInput, tuple[DocumentChunk, ...]]], max_results: int = 20):
        if not 1 <= max_results <= 100:
            raise ValueError("Invalid result budget")
        self.records = records
        self.max_results = max_results

    def retrieve(self, scenario: Scenario) -> ResearchBundle:
        terms = {
            value.strip().casefold()
            for value in (scenario.region, scenario.product, *scenario.seed_nodes)
            if value and value.strip()
        }
        hits = []
        for doc, chunks in self.records:
            for chunk in chunks:
                searchable = (doc.title + "\n" + chunk.content).casefold()
                count = sum(term in searchable for term in terms)
                if terms and count == 0:
                    continue
                hits.append((-count, doc.document_key, chunk.ordinal, doc, chunk))
        hits.sort(key=lambda x: (x[0], x[1], x[2]))
        evidence = []
        for _, _, _, doc, chunk in hits[:self.max_results]:
            evidence.append(Evidence(
                id="archived-chunk:" + sha256((doc.document_key + ":" + str(chunk.ordinal) + ":" + chunk.content_sha256).encode()).hexdigest(),
                title=doc.title,
                source_url=doc.source_url,
                published_at=doc.published_at,
                kind=EvidenceKind.unverified,
                supports_claim=False,
                independently_verified=False,
                quote_or_summary=chunk.content[:1000],
            ))
        return ResearchBundle(evidence=evidence, candidate_relations=[])
