"""Explicit operator-controlled import of pre-acquired UTF-8 disclosure text.

No URL fetching, scraping, PDF extraction, or source-authenticity claims.
Run from backend directory:
  python -m app.ingestion.import_public_document --input /path/doc.json
  python -m app.ingestion.import_public_document --input /path/doc.json --apply
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from app.database import session_factory
from app.ingestion.public_document_archive import archive_document
from app.skills.document_archive import (
    DocumentInput, MAX_DOCUMENT_CHARS, normalize_document, split_document,
)

MAX_IMPORT_FILE_BYTES = 1_000_000


def read_import_file(path: Path) -> DocumentInput:
    if not path.is_file() or path.stat().st_size > MAX_IMPORT_FILE_BYTES:
        raise ValueError("Import must be an existing JSON file <=1 MB")
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("Document import JSON must be an object")
    expected = {
        "document_key", "company_key", "title", "source_url",
        "published_at", "text",
    }
    if not expected <= payload.keys() or payload.keys() - (expected | {"source_type"}):
        raise ValueError("Unexpected or missing document metadata keys")
    return normalize_document(DocumentInput(**payload))


def main() -> None:
    parser = argparse.ArgumentParser(description="Archive licensed, pre-acquired public text")
    parser.add_argument("--input", required=True, type=Path, help="Operator-supplied UTF-8 JSON")
    parser.add_argument("--apply", action="store_true", help="Persist a version and chunks")
    args = parser.parse_args()
    doc = read_import_file(args.input)
    chunks = split_document(doc.text)
    result = {
        "mode": "apply" if args.apply else "dry_run",
        "document_key": doc.document_key,
        "company_key": doc.company_key,
        "source_url": doc.source_url,
        "published_at": doc.published_at,
        "chunks": len(chunks),
        "source_verification": "unverified",
        "relationships_created": 0,
    }
    if args.apply:
        with session_factory()() as session:
            with session.begin():
                stored = archive_document(
                    session, doc, retrieved_at=datetime.now(timezone.utc)
                )
        result.update({"document_id": stored.document_id,
                       "version": stored.version, "changed": stored.changed})
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
