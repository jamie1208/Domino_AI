# PR #5 — TPEx OTC Profiles and Multi-Source Ingestion Receipts

This PR extends the company's **basic-profile** registry only. It does not infer
supplier/customer edges, business dependencies, or real risk indices.

## Source catalog

| Source key | Market | Official API | Open-data catalog |
| --- | --- | --- | --- |
| twse | listed | https://openapi.twse.com.tw/v1/opendata/t187ap03_L | https://data.gov.tw/dataset/18419 |
| tpex | otc | https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O | https://data.gov.tw/dataset/25036 |

The TPEx dataset is published by the relevant Taiwan public-data authority with
Government Open Data License v1. Attribute the provider and license when publishing
data-based output, and check the latest usage terms/rate limits before scheduling.

**Live TPEx API has not yet been confirmed from this PR's execution environment.**
The exact endpoint and English field mapping must be verified by Codex against
the actual official response before merging.

TPEx payload mapping:

- `SecuritiesCompanyCode` → `ticker`
- `CompanyName` → `name`
- `SecuritiesIndustryCode` → `industry` (code, not human-readable name)
- `Date` → `source_report_date_raw` (ROC format retained without inventing UTC instant)

Market identifiers are prefixed `twse-listed:` and `tpex-otc:`; ticker
equality alone must never be treated as company-identity equivalence across sources.

## CLI

From the `backend` directory, with requirements installed:

```bash
PYTHONPATH=. python -m app.ingestion.import_company_profiles --source tpex
PYTHONPATH=. python -m app.ingestion.import_company_profiles --source twse
```

These **dry-run** commands fetch/validate only and do not write to DB.

Apply migrations and configure DATABASE_URL before requesting writes:

```bash
.venv/bin/alembic upgrade head
PYTHONPATH=. python -m app.ingestion.import_company_profiles --source tpex --apply
```

The legacy TWSE CLI now routes through the same audited path after migration.
Each successful `--apply` transaction stores a `source_ingestion_runs` receipt,
even if zero company profiles changed. It includes source, acquisition time,
full-batch hash and row/version counts. Invalid/broken fetches do not create
success receipts; an **attempt/failure ledger and raw snapshot archival remain
future work**. Ingestion receipts aren't evidence of direct supply relationships.

## Security and bounds

- Fixed HTTPS official endpoint, no follow redirects or arbitrary URLs.
- 12-second default timeout (maximum 30); streaming response limit 8 MB.
- Refuses invalid JSON, empty feeds, duplicate ticker codes or >5000 rows.
- Company changes are versioned, unchanged records are not duplicated.
- Official company profiles never create graph edges or verified direct links.
- No browser modifications, no LLM/RAG, no automatic daily schedule.

## Review checks

1. Run full backend pytest on temporary merged worktree and disposable PostgreSQL schema.
2. Verify Alembic 0003 and repeatable `upgrade head`.
3. Verify TPEx English response fields from one controlled live request.
4. Verify existing TWSE CLI plus new multi-source CLI.
5. Verify same-code market isolation, versioned updates, unchanged receipts,
   failure rollback, body/timeouts and no graph edge creation.
6. Inspect source licensing and attribution before production deployment.
