# PR #7 — TWSE daily material disclosures

This is the first **official real-disclosure text** acquisition connector.
It does not scrape MOPS HTML, fetch annual-report PDFs, or use LLM/RAG.

## Source contract

- TWSE official daily material disclosure OpenAPI:
  https://openapi.twse.com.tw/v1/opendata/t187ap04_L
- Government open-data catalog:
  https://data.gov.tw/dataset/18415
- The live schema must be checked once in Codex's authorized test environment
  before accepting this PR; code was built from published documentation.
- Relevant keys: `發言日期`, `發言時間`, `公司代號`, `主旨`
  (may include trailing whitespace in the source key), `說明`.
- `發言日期` is used for the public `published_at` date;
  `事實發生日` is **not** a publication date. Both may differ from
  `出表日期`. Dates are interpreted as ROC calendar only when parseable.
- Source URL is a **daily batch endpoint**, not an immutable permalink
  to one announcement. Record IDs are derived from company, publication day/time and a SHA-256
  fingerprint of the **complete canonical source row**, not merely title/body.
  This prevents silent merging when clause/fact date/report date differ.
  Exact duplicate rows remain indistinguishable without a publisher item ID.
  Batch-level archived raw fetch bytes and permanent item URLs remain follow-up work.
- Identical rows within a response are deduplicated. Any source-row field changes produce a different item key; the connector
  **cannot reliably correlate corrections to the same logical announcement**
  until a stable official item identifier becomes available. This may create
  separate archived observations rather than a version of the original one.

## Safe operator workflow

In the `backend/` directory, with dependencies installed:

```bash
PYTHONPATH=. python -m app.ingestion.import_twse_disclosures
```

Dry-run makes one bounded HTTPS request and parses the snapshot but does not
change the database.

After configuring `DATABASE_URL` and applying Alembic to head
(revision 0004):

```bash
PYTHONPATH=. python -m app.ingestion.import_twse_disclosures --apply
```

The entire batch is stored in **one caller-owned database transaction**.
Unexpected HTTP errors, oversized data or an invalid schema fail closed
instead of fabricating successful imports.

## Non-fabrication and current limits

- Only `material_announcement` unverified documents are added to the
  existing public document archive and chunk table.
- Alembic 0005 adds `source_published_at` (timezone-aware original speech
  timestamp) and `source_metadata` (complete normalized source row, source
  row digest, raw speech/date/clause fields and first observed batch SHA-256).
  The speech instant is interpreted in `Asia/Taipei` from the official ROC
  speech date and zero-padded 6-digit time; the existing `published_at`
  remains a date-level field for API compatibility.
- Importing an identical announcement from a later batch does not duplicate
  the document version. The first batch hash is retained; later fetches do
  **not** yet receive their own immutable retrieval receipts.
- No supplier/customer Graph Edge, company relation, verified claim,
  risk propagation path, or real risk score is generated.
- Initial version does not link announcement documents to an existing Company
  via database foreign key; a market-scoped `company_key` is stored.
- The code does not run a source polling service or retain the complete raw
  HTTP response permanently; a future retrieval ledger is necessary to
  preserve deleted announcements and proof of batch acquisition.
- Rate limits and attribution must follow current provider terms; daily
  snapshots must not be treated as a historical full-text corpus.

## Acceptance checks

1. Confirm live API HTTP and actual Chinese field names in one controlled GET.
2. Dry-run no-write, then controlled --apply to a **disposable PostgreSQL schema**.
3. Same snapshot twice yields one document, no new version; different
   announcements at the same second remain distinct even if title and body
   match but fact date, disclosure clause or report date differ.
4. Confirm explicit `Asia/Taipei` speech timestamp and complete canonical
   source-row metadata are stored in PostgreSQL; verify migration 0004->0005
   and fresh 0001->0005 paths.
4. ROC dates and difference between disclosure and event dates.
5. Network timeout, redirects, invalid UTF-8/JSON, empty and oversized bodies.
6. Full pytest with migrations through 0004, existing Analysis API and
   Evidence/Risk Engine regressions.
