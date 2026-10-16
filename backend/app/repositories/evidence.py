from datetime import datetime
from hashlib import sha256

from sqlalchemy import or_, select

from app.db_models import EvidenceRecord
from app.evidence_policy import normalize_source_host
from app.repositories.base import Repository


class EvidenceRepository(Repository):
    def create_version(self, *, evidence_id: str, title: str, content: str, kind: str, verification_status: str, supports_claim: bool, retrieved_at: datetime, valid_from: datetime, source_url: str | None = None, published_at: datetime | None = None, summary: str = '', independently_verified: bool = False, publisher_key: str | None = None, original_source_key: str | None = None, independence_basis: str | None = None, metadata: dict | None = None) -> EvidenceRecord:
        content_hash = sha256(content.encode('utf-8')).hexdigest()
        latest = self.session.scalar(select(EvidenceRecord).where(EvidenceRecord.evidence_id == evidence_id).order_by(EvidenceRecord.version.desc()).limit(1))
        normalized_host = normalize_source_host(source_url)
        if latest and all((latest.content_hash == content_hash, latest.title == title, latest.kind == kind, latest.verification_status == verification_status, latest.supports_claim == supports_claim, latest.source_url == source_url, latest.independently_verified == independently_verified, latest.normalized_source_host == normalized_host, latest.publisher_key == publisher_key, latest.original_source_key == original_source_key, latest.independence_basis == independence_basis)):
            return latest
        version = 1 if latest is None else latest.version + 1
        before = None
        if latest and latest.valid_to is None:
            before = {'id': latest.id, 'content_hash': latest.content_hash, 'valid_to': None}
            latest.valid_to = valid_from
        record = EvidenceRecord(evidence_id=evidence_id, version=version, source_url=source_url, normalized_source_host=normalized_host, title=title, kind=kind, verification_status=verification_status, supports_claim=supports_claim, independently_verified=independently_verified, publisher_key=publisher_key, original_source_key=original_source_key, independence_basis=independence_basis, published_at=published_at, retrieved_at=retrieved_at, valid_from=valid_from, content_hash=content_hash, summary=summary, metadata_json=metadata or {})
        self.session.add(record)
        self.session.flush()
        self.log_change('evidence', evidence_id, 'create' if version == 1 else 'supersede', version, {'id': record.id, 'content_hash': content_hash, 'retrieved_at': retrieved_at.isoformat()}, before)
        return record

    def get_at(self, evidence_id: str, as_of: datetime) -> EvidenceRecord | None:
        return self.session.scalar(select(EvidenceRecord).where(EvidenceRecord.evidence_id == evidence_id, EvidenceRecord.valid_from <= as_of, EvidenceRecord.retrieved_at <= as_of, or_(EvidenceRecord.published_at.is_(None), EvidenceRecord.published_at <= as_of), or_(EvidenceRecord.valid_to.is_(None), EvidenceRecord.valid_to > as_of)).order_by(EvidenceRecord.version.desc()).limit(1))

    def latest(self, evidence_id: str) -> EvidenceRecord | None:
        return self.session.scalar(select(EvidenceRecord).where(EvidenceRecord.evidence_id == evidence_id).order_by(EvidenceRecord.version.desc()).limit(1))

    def history(self, evidence_id: str) -> list[EvidenceRecord]:
        return list(self.session.scalars(select(EvidenceRecord).where(EvidenceRecord.evidence_id == evidence_id).order_by(EvidenceRecord.version)))
