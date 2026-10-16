"""Explicit, transaction-safe import of TWSE company profiles.

Only run from an authorized ingestion job/CLI; demo endpoints and
risk-propagation graph remain entirely untouched.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db_models import CompanyRecord
from app.repositories.company import CompanyRepository
from app.skills.twse_companies import CompanySnapshot


@dataclass(frozen=True)
class CompanyImportReport:
    created_versions: int
    unchanged: int
    rejected_rows: int
    source_sha256: str


def _as_utc(value: datetime) -> datetime:
    """Normalize database datetimes for comparison.

    Stored company timestamps originate from UTC-aware ingestion snapshots.
    SQLite may discard timezone metadata on read; interpret these values as UTC.
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def import_company_snapshot(session: Session, snapshot: CompanySnapshot) -> CompanyImportReport:
    """Idempotent import; all writes are in one caller-owned transaction.

    No implicit commit so callers may atomically coordinate ingestion metadata.
    Do not mix this with a session that is already processing an analysis.
    """
    if snapshot.source_url not in (\n        'https://openapi.twse.com.tw/v1/opendata/t187ap03_L',\n        'https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O',\n    ):\n        raise ValueError('Company snapshot is not from an approved source')\n    repository = CompanyRepository(session)
    created = 0
    unchanged = 0
    for item in snapshot.profiles:
        latest = session.scalar(
            select(CompanyRecord)
            .where(CompanyRecord.company_key == item.company_key)
            .order_by(CompanyRecord.version.desc())
            .limit(1)
        )
        expected_market = "listed" if snapshot.source_url.startswith("https://openapi.twse.com.tw/") else "otc"\n        expected_prefix = "twse-listed:" if expected_market == "listed" else "tpex-otc:"\n        if item.market != expected_market or not item.company_key.startswith(expected_prefix) or item.source_url != snapshot.source_url or item.dataset_url != snapshot.dataset_url:\n            raise ValueError("Snapshot contains mismatched market or source identity")\n        metadata = {
            "industry": item.industry,
            "source_url": item.source_url,
            "dataset_url": item.dataset_url,
            "source_report_date_raw": item.source_report_date_raw,
            "profile_source": "twse_open_data" if expected_market == "listed" else "tpex_open_data",
            # This hash identifies a fetched batch, not a verified source claim.
            "snapshot_sha256": snapshot.payload_sha256,
        }
        # Batch hashes change when *other* companies change, so exclude
        # snapshot_sha256 from per-company content equality.
        comparable = {k: v for k, v in metadata.items() if k != "snapshot_sha256"}
        if (latest and latest.name == item.name and latest.ticker == item.ticker
                and latest.market == item.market and not latest.is_synthetic
                and all(latest.metadata_json.get(k) == v for k, v in comparable.items())):
            unchanged += 1
            continue
        if latest and _as_utc(snapshot.retrieved_at) <= _as_utc(latest.valid_from):
            raise ValueError("Imported snapshot timestamp must be later than current company version")
        repository.create_version(
            company_key=item.company_key,
            name=item.name,
            ticker=item.ticker,
            market=item.market,
            valid_from=snapshot.retrieved_at,
            is_synthetic=False,
            metadata=metadata,
        )
        created += 1
    return CompanyImportReport(
        created_versions=created,
        unchanged=unchanged,
        rejected_rows=snapshot.rejected_rows,
        source_sha256=snapshot.payload_sha256,
    )


def import_twse_snapshot(session: Session, snapshot: CompanySnapshot) -> CompanyImportReport:
    """Backwards-compatible TWSE-only import entrypoint."""
    if snapshot.source_url != "https://openapi.twse.com.tw/v1/opendata/t187ap03_L":
        raise ValueError("Expected TWSE snapshot")
    return import_company_snapshot(session, snapshot)
