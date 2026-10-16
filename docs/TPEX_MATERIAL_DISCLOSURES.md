# PR #8 — TPEx OTC daily material disclosures

Adds the TPEx (上櫃) company material-announcement feed to the existing
versioned public-document archive. It reuses the previously reviewed TWSE
canonical-row fingerprint, ROC-date / Asia/Taipei speech-time parsing,
provenance JSON, chunking and UTC storage logic.

## Official source

- API candidate (one **fixed** HTTPS URL):
  https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap04_O
- Taiwan government open-data catalog:
  https://data.gov.tw/dataset/18418
- Market identity: `tpex-otc:<code>`.
- Announcement identity: `tpex-material:<code>:<publication-date>:<HHMMSS>:<SHA256(full source row)>`.

The government catalog lists company, speech date/time, title, disclosure
clause, fact date and explanatory-text fields. **Exact live API keys, HTTP
behavior and record count need a one-time controlled Codex check** before
merge, because the official endpoint could not be directly read in this
authoring environment. Do not change to an unapproved mirror or silently
accept an unexpected schema.

The source is a **daily snapshot**, not an immutable item permalink or
historical archive. A full-row fingerprint cannot establish two different
rows are revisions to the same logical announcement: they are separate
observations. Identical full rows may be indistinguishable in the absence of
a publisher-issued permanent ID. The first-observed batch SHA256 is kept,
but whole HTTP response bytes and subsequent collection receipts are not
archived by this change.

## CLI

From `backend/` after installing the project requirements:

```bash
PYTHONPATH=. python -m app.ingestion.import_tpex_disclosures
```

This fetches and validates once without database changes.

To import intentionally into an **authorized, migrated** database:

```bash
PYTHONPATH=. python -m app.ingestion.import_tpex_disclosures --apply
```

No new migration: PR #7's Alembic 0005 already supplies
`public_documents.source_published_at` and `source_metadata`.

## Safety and validation

- HTTP limited to one fixed official host, no redirects, bounded 12 MB body,
  12 second default timeout (max 30), explicit MockTransport tests.
- Reject malformed JSON, ambiguous normalized duplicate keys and non-empty
  batches with zero usable disclosures.
- Use full-row fingerprint rather than title-only similarity.
- Preserve original Chinese field labels, normalized field labels,
  ROC speech date, original + padded time, disclosure clause, fact date,
  report date and batch hash; database speech time is normalized to UTC.
- Repeated observations cannot overwrite source identity or automatically
  create more company versions/edges.
- All archived disclosure texts remain `unverified`, never evidence of direct
  supplier relationships on their own. No GraphEdges or risk indices.

## Merge gates

1. Controlled live GET of the **official** TPEx endpoint and verify all
   required response fields before trusting online compatibility.
2. Run full pytest against temporary merged main and disposable PostgreSQL
   schema with Alembic upgraded through 0005.
3. Validate dry-run is read-only and --apply persists OTC-only identities.
4. Confirm TWSE parsing and previous time/provenance regressions remain green.
5. Verify same-time/subject/body but different clause/fact date do not collide,
   and an identical row in a different batch stays one document version.
6. Do not merge on the basis of tests alone if live source contract differs.
