"""Persistence-layer evidence provenance and conservative admission policy."""
from urllib.parse import urlsplit

from app.db_models import EvidenceRecord
from app.domain_errors import EvidenceAdmissionError


def normalize_source_host(url: str | None) -> str | None:
    if not url:
        return None
    try:
        parsed = urlsplit(url)
    except ValueError:
        return None
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        return None
    return parsed.hostname.lower().removeprefix('www.')


def admit_verified_direct(records: list[EvidenceRecord]) -> None:
    """Require official evidence or two explicitly independent third parties.

    Distinct hosts are required for preliminary corroboration, but are not by
    themselves proof of publisher or original-source independence.
    """
    unique_records = {}
    for record in sorted(records, key=lambda item: item.version):
        unique_records[record.evidence_id] = record
    supported = [record for record in unique_records.values() if record.verification_status == 'supported' and record.supports_claim]
    official = any(record.kind == 'official' and record.normalized_source_host for record in supported)
    if official:
        return
    eligible = [
        record for record in supported
        if record.kind == 'third_party'
        and record.independently_verified
        and record.normalized_source_host
        and record.publisher_key
        and record.original_source_key
        and record.independence_basis in ('publisher_and_original_source', 'manual_review')
    ]
    if len(eligible) < 2:
        raise EvidenceAdmissionError('DIRECT_EVIDENCE_INDEPENDENCE_METADATA_MISSING', '第三方證據缺少明確的獨立驗證、出版者、原始來源或驗證依據 metadata。')
    if len({record.normalized_source_host for record in eligible}) < 2:
        raise EvidenceAdmissionError('DIRECT_EVIDENCE_HOSTS_NOT_INDEPENDENT', 'verified_direct 的第三方證據必須來自至少兩個不同來源 Host。')
    if len({record.publisher_key for record in eligible}) < 2 or len({record.original_source_key for record in eligible}) < 2:
        raise EvidenceAdmissionError('DIRECT_EVIDENCE_PROVENANCE_NOT_INDEPENDENT', '不同 Host 不足以證明獨立性；必須確認不同出版者與原始資訊來源。')
