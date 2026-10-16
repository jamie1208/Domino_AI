"""Bounded, offline indexing of externally acquired public source documents.

The caller must acquire documents lawfully, verify licenses and provenance, and
supply their text. This adapter NEVER crawls the web and NEVER converts
co-occurrence into direct supplier relationships.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlsplit

from app.schemas import Evidence, EvidenceKind, Scenario
from app.skills.researcher import ResearchBundle


@dataclass(frozen=True)
class PublicDocument:
    title: str
    source_url: str
    published_at: str
    content: str
    kind: EvidenceKind = EvidenceKind.unverified


def _validated_document(document: PublicDocument, max_chars: int) -> tuple[str, str]:
    parsed = urlsplit(document.source_url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Public document must have an HTTPS source without embedded credentials")
    try:
        date.fromisoformat(document.published_at)
    except ValueError as exc:
        raise ValueError("Public document published_at must be ISO YYYY-MM-DD") from exc
    if not document.title.strip() or not document.content.strip():
        raise ValueError("Public document title and content are required")
    if len(document.content) > max_chars:
        raise ValueError("Public document exceeds configured size budget")
    digest = hashlib.sha256(
        (document.source_url.strip() + "\n" + document.published_at + "\n" + document.content).encode("utf-8")
    ).hexdigest()
    return digest, parsed.hostname.lower()


def _terms(scenario: Scenario) -> set[str]:
    # Only explicit context terms: do not infer company links from text overlap.
    values = [scenario.region, scenario.product, *scenario.seed_nodes]
    return {x.casefold().strip() for x in values if x and x.strip()}


class CuratedPublicDocumentProvider:
    """Deterministic, trust-conservative ResearchSkill provider.

    Input documents are externally supplied. We expose them as unverified
    candidates for downstream review with stable content-addressed IDs.
    No claim-support or independent corroboration is asserted by this layer.
    """

    def __init__(self, documents: list[PublicDocument], *, max_documents: int = 100,
                 max_document_chars: int = 100_000, max_results: int = 20):
        if not (1 <= max_documents <= 1000 and 1 <= max_document_chars <= 1_000_000
                and 1 <= max_results <= max_documents):
            raise ValueError("Invalid public document processing budget")
        if len(documents) > max_documents:
            raise ValueError("Document count exceeds configured budget")
        checked = []
        seen = set()
        for doc in documents:
            digest, _ = _validated_document(doc, max_document_chars)
            if digest not in seen:
                checked.append((digest, doc))
                seen.add(digest)
        self.documents = tuple(checked)
        self.max_results = max_results

    def retrieve(self, scenario: Scenario) -> ResearchBundle:
        terms = _terms(scenario)
        matched = []
        for digest, doc in self.documents:
            haystack = (doc.title + "\n" + doc.content).casefold()
            score = sum(1 for term in terms if term in haystack)
            if terms and score == 0:
                continue
            matched.append((-score, digest, doc))
        matched.sort(key=lambda row: (row[0], row[1]))
        evidence = [
            Evidence(
                id="document-sha256:" + digest,
                title=doc.title,
                source_url=doc.source_url,
                published_at=doc.published_at,
                # Do not infer document authenticity solely from the provider metadata.
                kind=EvidenceKind.unverified,
                supports_claim=False,
                independently_verified=False,
                quote_or_summary=doc.content[:1000],
            )
            for _, digest, doc in matched[:self.max_results]
        ]
        return ResearchBundle(evidence=evidence, candidate_relations=[])
