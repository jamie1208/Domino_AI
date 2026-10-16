"""Explicit TWSE disclosure ingestion: dry-run default and atomic --apply.

    python -m app.ingestion.import_twse_disclosures
    python -m app.ingestion.import_twse_disclosures --apply
"""
from __future__ import annotations

import argparse
import json

from app.database import session_factory
from app.ingestion.public_document_archive import archive_document
from app.skills.twse_disclosures import TWSEDisclosureConnector, DisclosureSnapshot


def persist_disclosures(session, snapshot: DisclosureSnapshot) -> dict[str, int]:
    """Call within one caller-owned transaction; never create graph links."""
    created = 0
    unchanged = 0
    for document in snapshot.documents:
        record = archive_document(session, document, retrieved_at=snapshot.retrieved_at)
        if record.changed:
            created += 1
        else:
            unchanged += 1
    return {"created_versions": created, "unchanged": unchanged}


def main() -> None:
    parser = argparse.ArgumentParser(description="Import TWSE official daily material disclosures")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    snapshot = TWSEDisclosureConnector().fetch()
    result = {
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
                result.update(persist_disclosures(session, snapshot))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
