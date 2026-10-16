"""Operator-controlled TPEx OTC disclosure ingestion. Dry-run by default.

From backend: python -m app.ingestion.import_tpex_disclosures [--apply]
"""
from __future__ import annotations

import argparse
import json

from app.database import session_factory
from app.ingestion.import_twse_disclosures import persist_disclosures
from app.skills.tpex_disclosures import TPExDisclosureConnector


def main() -> None:
    parser = argparse.ArgumentParser(description="Official TPEx OTC daily disclosures")
    parser.add_argument("--apply", action="store_true", help="Archive in database")
    args = parser.parse_args()
    snapshot = TPExDisclosureConnector().fetch()
    report = {
        "mode": "apply" if args.apply else "dry_run",
        "source_url": snapshot.source_url,
        "dataset_url": snapshot.dataset_url,
        "retrieved_at": snapshot.retrieved_at.isoformat(),
        "snapshot_sha256": snapshot.payload_sha256,
        "accepted_documents": len(snapshot.documents),
        "rejected_rows": snapshot.rejected_rows,
        "relationship_count": 0,
    }
    if args.apply:
        with session_factory()() as session:
            with session.begin():
                report.update(persist_disclosures(session, snapshot))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
