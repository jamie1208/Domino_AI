"""SQLAlchemy persistence models for versioned graph and analysis snapshots."""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index,
    Integer, JSON, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

JsonType = JSON().with_variant(JSONB(), 'postgresql')


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class CompanyRecord(Base):
    __tablename__ = 'companies'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    company_key: Mapped[str] = mapped_column(String(160), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    ticker: Mapped[str | None] = mapped_column(String(40))
    market: Mapped[str | None] = mapped_column(String(80))
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    metadata_json: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)
    __table_args__ = (
        UniqueConstraint('company_key', 'version', name='uq_companies_key_version'),
        CheckConstraint('version > 0', name='ck_companies_version_positive'),
        CheckConstraint('valid_to IS NULL OR valid_to > valid_from', name='ck_companies_valid_range'),
        Index('ix_companies_key_validity', 'company_key', 'valid_from', 'valid_to'),
    )


class GraphNodeRecord(Base):
    __tablename__ = 'graph_nodes'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    node_key: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    label: Mapped[str] = mapped_column(String(500), nullable=False)
    company_id: Mapped[str | None] = mapped_column(ForeignKey('companies.id', ondelete='RESTRICT'))
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    data_version: Mapped[str] = mapped_column(String(80), nullable=False)
    properties: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)
    __table_args__ = (
        UniqueConstraint('node_key', 'version', name='uq_graph_nodes_key_version'),
        CheckConstraint("kind IN ('event','region','product','industry','company')", name='ck_graph_nodes_kind'),
        CheckConstraint('version > 0', name='ck_graph_nodes_version_positive'),
        CheckConstraint('valid_to IS NULL OR valid_to > valid_from', name='ck_graph_nodes_valid_range'),
        Index('ix_graph_nodes_key_validity', 'node_key', 'valid_from', 'valid_to'),
    )


class GraphEdgeRecord(Base):
    __tablename__ = 'graph_edges'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    edge_key: Mapped[str] = mapped_column(String(240), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    source_node_id: Mapped[str] = mapped_column(ForeignKey('graph_nodes.id', ondelete='RESTRICT'), nullable=False)
    target_node_id: Mapped[str] = mapped_column(ForeignKey('graph_nodes.id', ondelete='RESTRICT'), nullable=False)
    relation_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    weight: Mapped[float | None] = mapped_column(Float)
    propagation_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    data_version: Mapped[str] = mapped_column(String(80), nullable=False)
    properties: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)
    __table_args__ = (
        UniqueConstraint('edge_key', 'version', name='uq_graph_edges_key_version'),
        CheckConstraint("relation_kind IN ('verified_direct','industry_inferred','shared_exposure','unverified_candidate')", name='ck_graph_edges_kind'),
        CheckConstraint('weight IS NULL OR (weight >= 0 AND weight <= 1)', name='ck_graph_edges_weight'),
        CheckConstraint("relation_kind != 'unverified_candidate' OR propagation_eligible = false", name='ck_unverified_not_propagated'),
        CheckConstraint('source_node_id != target_node_id', name='ck_graph_edges_no_self_loop'),
        CheckConstraint('valid_to IS NULL OR valid_to > valid_from', name='ck_graph_edges_valid_range'),
        Index('ix_graph_edges_source_target', 'source_node_id', 'target_node_id'),
        Index('ix_graph_edges_key_validity', 'edge_key', 'valid_from', 'valid_to'),
    )


class EvidenceRecord(Base):
    __tablename__ = 'evidence'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    evidence_id: Mapped[str] = mapped_column(String(160), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str] = mapped_column(String(600), nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(40), nullable=False)
    supports_claim: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    independently_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    normalized_source_host: Mapped[str | None] = mapped_column(String(253))
    publisher_key: Mapped[str | None] = mapped_column(String(240))
    original_source_key: Mapped[str | None] = mapped_column(String(240))
    independence_basis: Mapped[str | None] = mapped_column(String(60))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default='')
    metadata_json: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)
    __table_args__ = (
        UniqueConstraint('evidence_id', 'version', name='uq_evidence_stable_id_version'),
        CheckConstraint('version > 0', name='ck_evidence_version_positive'),
        CheckConstraint('length(content_hash) = 64', name='ck_evidence_sha256_length'),
        CheckConstraint("verification_status IN ('unverified','supported','rejected','superseded')", name='ck_evidence_verification_status'),
        CheckConstraint("independence_basis IS NULL OR independence_basis IN ('publisher_and_original_source','manual_review')", name='ck_evidence_independence_basis'),
        CheckConstraint('valid_to IS NULL OR valid_to > valid_from', name='ck_evidence_valid_range'),
        Index('ix_evidence_id_validity', 'evidence_id', 'valid_from', 'valid_to'),
        Index('ix_evidence_publication_retrieval', 'published_at', 'retrieved_at'),
    )


class EdgeEvidenceRecord(Base):
    __tablename__ = 'edge_evidence'
    edge_id: Mapped[str] = mapped_column(ForeignKey('graph_edges.id', ondelete='CASCADE'), primary_key=True)
    evidence_record_id: Mapped[str] = mapped_column(ForeignKey('evidence.id', ondelete='RESTRICT'), primary_key=True)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class ScenarioRecord(Base):
    __tablename__ = 'scenarios'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    input_snapshot: Mapped[dict] = mapped_column(JsonType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class AnalysisRecord(Base):
    __tablename__ = 'analyses'
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(ForeignKey('scenarios.id', ondelete='RESTRICT'), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    data_mode: Mapped[str] = mapped_column(String(40), nullable=False)
    model_version: Mapped[str] = mapped_column(String(80), nullable=False)
    data_version: Mapped[str] = mapped_column(String(80), nullable=False)
    parameters_snapshot: Mapped[dict] = mapped_column(JsonType, nullable=False)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (
        CheckConstraint("status IN ('complete','insufficient_evidence','invalid_input')", name='ck_analyses_status'),
        Index('ix_analyses_scenario_created', 'scenario_id', 'created_at'),
    )


class AnalysisResultRecord(Base):
    __tablename__ = 'analysis_results'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    analysis_id: Mapped[str] = mapped_column(ForeignKey('analyses.id', ondelete='CASCADE'), nullable=False, unique=True)
    result_payload: Mapped[dict] = mapped_column(JsonType, nullable=False)
    risk_index: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (CheckConstraint('risk_index IS NULL OR (risk_index >= 0 AND risk_index <= 100)', name='ck_analysis_results_risk_index'),)


class DataChangeLogRecord(Base):
    __tablename__ = 'data_change_log'
    id: Mapped[int] = mapped_column(Integer().with_variant(BigInteger, 'postgresql'), primary_key=True, autoincrement=True)
    table_name: Mapped[str] = mapped_column(String(80), nullable=False)
    record_key: Mapped[str] = mapped_column(String(240), nullable=False)
    change_type: Mapped[str] = mapped_column(String(30), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    before_snapshot: Mapped[dict | None] = mapped_column(JsonType)
    after_snapshot: Mapped[dict] = mapped_column(JsonType, nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (
        CheckConstraint("change_type IN ('create','supersede','link','snapshot')", name='ck_change_log_type'),
        Index('ix_change_log_record', 'table_name', 'record_key', 'version'),
    )


class SourceIngestionRunRecord(Base):
    """Immutable record of a successful source fetch/import attempt."""
    __tablename__ = 'source_ingestion_runs'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_key: Mapped[str] = mapped_column(String(80), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    dataset_url: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    accepted_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    rejected_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    created_versions: Mapped[int] = mapped_column(Integer, nullable=False)
    unchanged_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default='success')
    __table_args__ = (
        CheckConstraint("status = 'success'", name='ck_source_runs_status'),
        CheckConstraint('length(payload_sha256) = 64', name='ck_source_runs_hash'),
        CheckConstraint('accepted_rows >= 0 AND rejected_rows >= 0 AND created_versions >= 0 AND unchanged_rows >= 0', name='ck_source_runs_counts'),
        Index('ix_source_runs_key_retrieved', 'source_key', 'retrieved_at'),
    )


class PublicDocumentRecord(Base):
    """Versioned full text; unverified until explicit independent review."""
    __tablename__ = "public_documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    document_key: Mapped[str] = mapped_column(String(160), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    company_key: Mapped[str] = mapped_column(String(160), nullable=False)
    title: Mapped[str] = mapped_column(String(600), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False, default="unverified")
    __table_args__ = (
        UniqueConstraint("document_key", "version", name="uq_public_document_version"),
        CheckConstraint("version > 0", name="ck_public_document_version"),
        CheckConstraint("length(content_sha256) = 64", name="ck_public_document_hash"),
        CheckConstraint("verification_status = 'unverified'", name="ck_public_document_unverified"),
        CheckConstraint("valid_to IS NULL OR valid_to > valid_from", name="ck_public_document_validity"),
        Index("ix_public_documents_key_time", "document_key", "valid_from", "valid_to"),
    )


class DocumentChunkRecord(Base):
    """Immutable character offset range into one specific document version."""
    __tablename__ = "public_document_chunks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    document_record_id: Mapped[str] = mapped_column(ForeignKey("public_documents.id", ondelete="CASCADE"), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    start_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    end_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (
        UniqueConstraint("document_record_id", "ordinal", name="uq_document_chunk_ordinal"),
        CheckConstraint("start_offset >= 0 AND end_offset > start_offset", name="ck_document_chunk_offsets"),
        CheckConstraint("length(content_sha256) = 64", name="ck_document_chunk_hash"),
        Index("ix_document_chunks_document", "document_record_id", "ordinal"),
    )
