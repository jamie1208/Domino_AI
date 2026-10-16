# Current demo API contract

GET `/api/health` → `{ "status": "ok", "mode": "synthetic_fixture" }`

POST `/api/demo/analyze` → Scenario JSON, returns `GraphAnalysisResult` JSON. The endpoint runs the existing orchestrator and deterministic Python risk engine, then a presentation adapter creates the graph contract.

Example request:
```json
{
  "description": "假設材料供應中斷30天",
  "event_type": "supply_chain",
  "region": "虛構地區",
  "product": "測試材料",
  "duration_days": 30,
  "severity": 0.8,
  "seed_nodes": ["材料產業"]
}
```

Response fields:
- `analysis_id`, `analyzed_at`, `model_version`
- normalized `scenario` and `status`
- `data_mode` (`synthetic_fixture` in the current demo endpoint)
- typed `nodes`, `edges`, and `primary_paths`
- `evidence`, `risk_results`, `findings`, `limitations`, and `explanation`

Graph edge kinds are `verified_direct`, `industry_inferred`, or `unverified_candidate`. Candidate edges always have `included_in_propagation=false`. Fixture industry dependencies remain `industry_inferred`; the adapter never promotes them to direct enterprise relationships.

`status` is `complete`, `insufficient_evidence`, or `invalid_input`.
The demo URL only uses synthetic, nonverified fixture data; use a separate production endpoint after live public-data adapters exist.

All graph `edges` have explicit `kind`, nullable `weight`, `evidence_ids`, and `included_in_propagation`.
All `risk_results` hold `risk_index` and `top_paths`. `risk_index` is a deliberately simplified 0–100 demo index calculated in Python.
Frontend should display an unmistakable "合成資料／非實際企業分析" label when `data_mode=synthetic_fixture`.
