"""Versioned public document archive with atomic text/chunk persistence."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db_models import PublicDocumentRecord, DocumentChunkRecord
from app.skills.document_archive import DocumentInput, normalize_document, split_document


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class ArchiveWriteResult:
    document_id: str
    version: int
    changed: bool
    chunks: int


def archive_document(
    session: Session, document: DocumentInput, *, retrieved_at: datetime,
    chunk_size: int = 800, overlap: int = 100,
) -> ArchiveWriteResult:
    """Requires caller-owned transaction; no implicit commit or external fetch.

    No archive entry can certify source authenticity or direct business links.
    """
    if retrieved_at.tzinfo is None:
        raise ValueError("retrieved_at requires timezone")
    doc = normalize_document(document)
    parts = split_document(doc.text, chunk_size=chunk_size, overlap=overlap)
    digest = sha256(doc.text.encode("utf-8")).hexdigest()
    latest = session.scalar(
        select(PublicDocumentRecord)
        .where(PublicDocumentRecord.document_key == doc.document_key)
        .order_by(PublicDocumentRecord.version.desc())
        .limit(1)
    )
    if latest is not None and (
        latest.company_key != doc.company_key or latest.source_url != doc.source_url
    ):
        raise ValueError("Document key cannot change its company or provenance source")
    same = latest is not None and all((
        latest.content_sha256 == digest,
        latest.title == doc.title,
        latest.source_type == doc.source_type,
        latest.published_at.date() == __import__("datetime").date.fromisoformat(doc.published_at),
    ))
    if same:
        existing_count = session.query(DocumentChunkRecord).filter(
            DocumentChunkRecord.document_record_id == latest.id
        ).count()
        return ArchiveWriteResult(latest.id, latest.version, False, existing_count)
    if latest and _utc(retrieved_at) <= _utc(latest.valid_from):
        raise ValueError("Updated snapshot must have later retrieval timestamp")
    if latest and latest.valid_to is None:
        latest.valid_to = retrieved_at
    record = PublicDocumentRecord(
        document_key=doc.document_key, version=(latest.version + 1 if latest else 1),
        company_key=doc.company_key, title=doc.title, source_url=doc.source_url,
        source_type=doc.source_type,
        published_at=datetime.combine(__import__("datetime").date.fromisoformat(doc.published_at),
                                      datetime.min.time(), tzinfo=timezone.utc),
        retrieved_at=retrieved_at, valid_from=retrieved_at,
        content_sha256=digest, original_text=doc.text, verification_status="unverified",
    )
    session.add(record)
    session.flush()
    for part in parts:
        session.add(DocumentChunkRecord(
            document_record_id=record.id, ordinal=part.ordinal,
            start_offset=part.start, end_offset=part.end,
            content_sha256=part.content_sha256, content=part.content,
        ))
    session.flush()
    return ArchiveWriteResult(record.id, record.version, True, len(parts))


def load_document_chunks(session: Session, document_id: str):
    """Return matching text and chunks for source-verifiable passage retrieval."""
    record = session.get(PublicDocumentRecord, document_id)
    if record is None:
        return None
    chunks = list(session.scalars(
        select(DocumentChunkRecord)
        .where(DocumentChunkRecord.document_record_id == document_id)
        .order_by(DocumentChunkRecord.ordinal)
    ))
    for chunk in chunks:
        if record.original_text[chunk.start_offset:chunk.end_offset] != chunk.content:
            raise ValueError("Archived passage offsets are inconsistent")
        if sha256(chunk.content.encode("utf-8")).hexdigest() != chunk.content_sha256:
            raise ValueError("Archived passage content hash is inconsistent")
    return record, chunks
