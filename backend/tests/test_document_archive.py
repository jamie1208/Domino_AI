"""Offline regression tests for public-document archive and citation offsets."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import os
import subprocess
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.db_models import Base, PublicDocumentRecord, DocumentChunkRecord, GraphEdgeRecord
from app.ingestion.public_document_archive import archive_document, load_document_chunks
from app.schemas import Scenario, EvidenceKind
from app.skills.document_archive import (
    DocumentInput, normalize_document, split_document, ArchivedDocumentResearchProvider,
)
from app.skills.researcher import ResearchSkill

NOW = datetime(2026, 10, 16, tzinfo=timezone.utc)


def sample(**changes):
    base = DocumentInput(
        document_key="twse-report:synthetic-1",
        company_key="twse-listed:2330",
        title="合成測試營運報告",
        source_url="https://disclosure.example/filing/123",
        published_at="2026-10-10",
        text=("測試半導體供應鏈與營運風險。\n" * 80),
    )
    return replace(base, **changes)


def test_normalize_rejects_unsafe_inputs():
    for wrong in (
        {"source_url": "http://disclosure.example/"},
        {"source_url": "https://name:pw@disclosure.example/"},
        {"published_at": "1151016"},
        {"company_key": "2330"},
        {"source_type": "unapproved"},
        {"text": ""},
    ):
        with pytest.raises(ValueError):
            normalize_document(sample(**wrong))


def test_chunks_preserve_exact_offsets_and_hash():
    doc = normalize_document(sample(text="測試段落一\n" * 100))
    chunks = split_document(doc.text, chunk_size=120, overlap=20)
    assert len(chunks) > 1
    for chunk in chunks:
        assert doc.text[chunk.start:chunk.end] == chunk.content
        assert sha256(chunk.content.encode()).hexdigest() == chunk.content_sha256
    assert chunks[-1].end == len(doc.text)
    assert chunks[0].start == 0


def test_version_archive_deduplication_and_history():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        first = archive_document(session, sample(), retrieved_at=NOW)
        assert first.changed and first.version == 1
        assert not archive_document(session, sample(), retrieved_at=NOW + timedelta(days=1)).changed
        newer = archive_document(
            session, sample(text=sample().text + "\n新版本內容"),
            retrieved_at=NOW + timedelta(days=2),
        )
        assert newer.version == 2 and newer.changed
        versions = list(session.scalars(select(PublicDocumentRecord).order_by(PublicDocumentRecord.version)))
        assert len(versions) == 2 and versions[0].valid_to is not None
        assert versions[0].verification_status == "unverified"
        archived = load_document_chunks(session, newer.document_id)
        assert archived is not None and len(archived[1]) == newer.chunks
        assert list(session.scalars(select(GraphEdgeRecord))) == []


def test_document_key_provenance_is_immutable():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        archive_document(session, sample(), retrieved_at=NOW)
        with pytest.raises(ValueError, match="provenance"):
            archive_document(
                session,
                sample(source_url="https://other.example/report"),
                retrieved_at=NOW + timedelta(days=1),
            )


def test_keyword_retrieval_does_not_certify_supply_relationship():
    doc = normalize_document(sample(text="合成文件：甲公司向乙公司提供半導體材料。"))
    chunks = split_document(doc.text)
    bundle = ResearchSkill(
        ArchivedDocumentResearchProvider([(doc, chunks)])
    ).run(Scenario(description="假設材料供應中斷", product="半導體材料"))
    assert len(bundle.evidence) == 1
    assert bundle.evidence[0].kind == EvidenceKind.unverified
    assert bundle.evidence[0].supports_claim is False
    assert bundle.evidence[0].independently_verified is False
    assert bundle.candidate_relations == []


def test_keyword_retrieval_excludes_unrelated_text():
    doc = normalize_document(sample(text="合成文件：食品零售業營運情況"))
    bundle = ArchivedDocumentResearchProvider([(doc, split_document(doc.text))]).retrieve(
        Scenario(description="測試情境", product="半導體")
    )
    assert bundle.evidence == []


@pytest.fixture
def migrated_postgres_archive_url():
    """Prepare the explicitly configured disposable test schema before archive checks.

    Never use DATABASE_URL here; a dedicated TEST_DATABASE_URL must be supplied
    and should point to the isolated PostgreSQL schema managed by the test runner.
    """
    raw = os.getenv("TEST_DATABASE_URL")
    if not raw:
        pytest.skip("isolated TEST_DATABASE_URL PostgreSQL schema required")
    if not make_url(raw).drivername.startswith("postgresql"):
        pytest.skip("PostgreSQL required")
    env = {**os.environ, "DATABASE_URL": raw}
    subprocess.run(
        [".venv/bin/alembic", "upgrade", "head"],
        env=env, check=True, capture_output=True, text=True,
    )
    return raw


def test_postgres_document_archive_version_and_no_edges(migrated_postgres_archive_url):
    engine = create_engine(migrated_postgres_archive_url)
    key = "twse-report:synthetic-" + uuid4().hex[:12]
    with Session(engine) as session:
        doc = sample(document_key=key)
        first = archive_document(session, doc, retrieved_at=NOW)
        assert archive_document(session, doc, retrieved_at=NOW + timedelta(days=1)).changed is False
        second = archive_document(
            session, replace(doc, text=doc.text + "\nnew"), retrieved_at=NOW + timedelta(days=2)
        )
        assert second.version == 2
        assert load_document_chunks(session, first.document_id)
        assert load_document_chunks(session, second.document_id)
        with pytest.raises(ValueError, match="later"):
            archive_document(
                session, replace(doc, text=doc.text + "\nolder"),
                retrieved_at=NOW + timedelta(hours=1),
            )
        session.rollback()
