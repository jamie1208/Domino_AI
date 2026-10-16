"""Explicit one-shot TWSE listed-company ingestion command.

Run with: python -m app.ingestion.import_twse_companies [--apply]

Default dry-run fetches and validates without writing to the DB.
--apply requires configured DATABASE_URL and Alembic migrations through 0003.
"""
from __future__ import annotations

import argparse
import json

from app.database import session_factory
from app.ingestion.import_company_profiles import persist_snapshot
from app.skills.twse_companies import TWSECompanyConnector


def main() -> None:
    parser = argparse.ArgumentParser(description="TWSE official listed-company profile import")
    parser.add_argument("--apply", action="store_true", help="Persist verified-format profiles in DB")
    args = parser.parse_args()

    snapshot = TWSECompanyConnector().fetch()
    report = {
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
                result = persist_snapshot(session, source_key='twse', snapshot=snapshot)
            report["created_versions"] = result.created_versions
            report["unchanged"] = result.unchanged
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
