# PR #6: Versioned public-document archive and passage preparation

This milestone makes public enterprise disclosures usable by the later Hybrid RAG
pipeline **without inventing company relationships**.

## Implemented

- Operator-supplied, previously lawfully obtained **UTF-8 text** with
  `document_key`, market-qualified `company_key`, source HTTPS URL, ISO
  publication date, title and original text.
- Strict document size budget (300,000 characters), bounded character chunks
  with offsets into the **stored normalized original text**, deterministic
  SHA-256 chunk fingerprints.
- Versioned `public_documents` text and `public_document_chunks` records.
  Unchanged documents do not create new document versions; genuine updates
  preserve history and source provenance.
- Alembic revision `20261016_0004` supports both fresh
  `0001 -> 0002 -> 0003 -> 0004` and existing `0003 -> 0004` paths.
  It checks for tables already created by legacy dynamic 0001 metadata.
- Optional keyword-only `ArchivedDocumentResearchProvider` preserving
  existing `ResearchSkill.run` contract, output always unverified and no
  direct relationship candidates.
- New explicit dry-run and `--apply` CLI.

## Run (inside backend)

Given an **authorized** local JSON file:

```json
{
  "document_key": "twse-report:your-source-document-id",
  "company_key": "twse-listed:2330",
  "title": "公司公開揭露測試文件",
  "source_url": "https://example.org/official-disclosure",
  "published_at": "2026-10-10",
  "source_type": "company_disclosure",
  "text": "依法取得並允許處理的公開原文..."
}
```

The URL above is only a format illustration, **not an actual official source**.
Do not label uploaded content official without independent source confirmation.

```bash
PYTHONPATH=. python -m app.ingestion.import_public_document --input /path/doc.json
.venv/bin/alembic upgrade head
PYTHONPATH=. python -m app.ingestion.import_public_document --input /path/doc.json --apply
```

Dry-run is read-only. Apply requires `DATABASE_URL`, a migrated database and an
authorized dataset; writer owns a single database transaction.

## Intentional exclusions

- This PR **does not fetch TWSE/MOPS annual reports, PDF documents, financial
  disclosures, HTML pages, or news from the Internet**; official document
  retrieval requires verified endpoint contracts, licensing, rate limits and
  legal access. Those connectors follow separately.
- It **does not** validate publisher authenticity or the truth of any claim.
- It **does not** run an embedding model, vector DB, Hybrid RAG, or LLM.
- It **does not** create supply-chain GraphEdges, propagation paths or risk
  scores. A mention of a company in a document is not evidence of direct supply.
- Source attribution is retained via URL and publication date; a future
  document-fetch receipt ledger should additionally track successful/failed
  acquisitions even when content does not change.

## Required local review

1. Test migration from empty PostgreSQL schema and from preexisting 0003,
   and repeat `alembic upgrade head`.
2. Run the full PostgreSQL pytest suite, including archive versioning and
   inherited Risk Engine/Evidence Verifier/API Contract tests.
3. Confirm exact text offsets, chunk content hashes, duplicate import behavior,
   and non-overwrite of older versions.
4. Ensure dry-run never touches the DB and illegal/non-HTTPS source metadata
   fails closed.
5. Confirm no automatic GraphEdge creation or false evidence verification.
