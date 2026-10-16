# Phase 4 PostgreSQL persistence

This layer stores versioned graph facts and immutable analysis response snapshots. Skills and the deterministic risk engine do not import SQLAlchemy.

## Relationships

```text
companies 1 ── 0..n graph_nodes
graph_nodes 1 ── 0..n graph_edges (source)
graph_nodes 1 ── 0..n graph_edges (target)
graph_edges n ── n evidence (through edge_evidence)
scenarios 1 ── n analyses 1 ── 1 analysis_results
data_change_log records version creation, supersession, links and snapshots
```

`companies`, `graph_nodes`, `graph_edges`, and `evidence` use stable business keys plus monotonically increasing versions. `valid_from` / `valid_to` describe when a fact is valid; `published_at` describes source publication; `retrieved_at` describes system availability; `recorded_at` describes database insertion. Temporal evidence lookup checks all relevant boundaries to prevent future-data leakage.

Graph edge kinds are `verified_direct`, `industry_inferred`, `shared_exposure`, and `unverified_candidate`. A database constraint and repository guard both prevent an unverified candidate from becoming propagation eligible. The repository additionally requires supported evidence before accepting `verified_direct`.

`analysis_results.result_payload` is the immutable Phase 3 API snapshot. `risk_index` is nullable and remains null when the Python engine did not issue a score.

## Local commands

```bash
docker compose up -d postgres
cd backend
export DATABASE_URL='postgresql+psycopg://domino:domino_dev_only@127.0.0.1:5432/domino'
.venv/bin/alembic upgrade head
PYTHONPATH=. .venv/bin/python scripts/seed_synthetic.py
.venv/bin/uvicorn app.main:app --reload
```

Running the seed again does not duplicate its analysis snapshot. It is synthetic integration data and contains no claimed public source URL.
