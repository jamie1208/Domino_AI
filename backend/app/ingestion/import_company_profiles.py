"""Manual source ingestion: dry-run by default, transactional --apply.

    python -m app.ingestion.import_company_profiles --source tpex
    python -m app.ingestion.import_company_profiles --source twse --apply
"""
from __future__ import annotations

import argparse
import json

from app.database import session_factory
from app.db_models import SourceIngestionRunRecord
from app.ingestion.twse_companies import import_company_snapshot
from app.skills.twse_companies import TWSECompanyConnector
from app.skills.tpex_companies import TPExCompanyConnector


def persist_snapshot(session, *, source_key, snapshot):
    """Write profiles + immutable successful fetch receipt in one transaction.

    Caller owns commit/rollback; the method must not silently commit.
    """
    result = import_company_snapshot(session, snapshot)
    session.add(SourceIngestionRunRecord(
        source_key=source_key,
        source_url=snapshot.source_url,
        dataset_url=snapshot.dataset_url,
        retrieved_at=snapshot.retrieved_at,
        payload_sha256=snapshot.payload_sha256,
        accepted_rows=len(snapshot.profiles),
        rejected_rows=snapshot.rejected_rows,
        created_versions=result.created_versions,
        unchanged_rows=result.unchanged,
        status="success",
    ))
    session.flush()
    return result


def main():
    parser = argparse.ArgumentParser(description="Import official Taiwan company profiles")
    parser.add_argument("--source", choices=("twse", "tpex"), required=True)
    parser.add_argument("--apply", action="store_true", help="Explicitly persist profiles and receipt")
    args = parser.parse_args()
    connector = TWSECompanyConnector() if args.source == "twse" else TPExCompanyConnector()
    snapshot = connector.fetch()
    output = {
        "source": args.source,
        "mode": "apply" if args.apply else "dry_run",
        "source_url": snapshot.source_url,
        "dataset_url": snapshot.dataset_url,
        "retrieved_at": snapshot.retrieved_at.isoformat(),
        "batch_sha256": snapshot.payload_sha256,
        "accepted_companies": len(snapshot.profiles),
        "rejected_rows": snapshot.rejected_rows,
    }
    if args.apply:
        with session_factory()() as session:
            with session.begin():
                report = persist_snapshot(session, source_key=args.source, snapshot=snapshot)
            output["created_versions"] = report.created_versions
            output["unchanged"] = report.unchanged
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
