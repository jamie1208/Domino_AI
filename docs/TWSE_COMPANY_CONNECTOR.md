# PR #4 — TWSE listed-company profile import

This milestone adds a **narrow official-data ingestion job**, not an AI web crawler or a supplier/customer relationship extractor.

## Source and permitted scope

- Taiwan government open-data listing: https://data.gov.tw/dataset/18419
- Fixed TWSE company profiles endpoint: https://openapi.twse.com.tw/v1/opendata/t187ap03_L
- Open-data listing indicates Government Open Data License v1; check the current license and provider terms before running a production ingestion schedule.
- The dataset describes company code/name/industry, not supply chains.
- Only company **code, name, industry, raw reporting date** are retained, along with source URL, dataset URL, fetched timestamp and batch SHA256.
- The report-date field is deliberately *not* interpreted as an ISO publication date; its source format may use Taiwan ROC dates.

## Run

From `backend/`, after installing requirements:

```bash
PYTHONPATH=. python -m app.ingestion.import_twse_companies
```

Dry-run fetches and validates one official HTTPS response but does not write to the database. The endpoint's accessibility has not yet been confirmed in this PR's development environment.

To save rows, first configure `DATABASE_URL`, apply existing migrations, then explicitly opt in:

```bash
PYTHONPATH=. python -m app.ingestion.import_twse_companies --apply
```

`--apply` uses one transaction; import is idempotent for unchanged company profiles and versions changed profiles. A network or schema error raises an exception rather than silently falling back to synthetic data. Run only under approved, rate-limited ingestion scheduling.

## Limits and threat model

- Fixed TWSE URL, no caller-controlled URL, no redirects, HTTPS only.
- Request timeout 12 seconds, 8 MB body limit, at most 5000 rows.
- Rejected/invalid company rows counted; zero valid rows fail the entire feed.
- Fetching the official endpoint does not establish the veracity of every field. No `verified_direct` edges or synthetic risk scores are generated.
- Company records are **not** directly injected into Orchestrator or React Flow.
- No general scraper, news crawler, RAG, LLM, or OTC data connector yet.

## Known follow-ups

1. Confirm live endpoint reachability, actual response schema and provider access policies in deployment.
2. Add a similarly scoped TPEx OTC-company connector using its separately documented fields.
3. Add retrieval status/audit table and archival snapshots for daily incremental updating.
4. Build an authorized company search API and source freshness UI.
5. Add eligible primary document connectors and passage-level claim verification before proposing real supply relationships.
