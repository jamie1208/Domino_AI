# Current demo API contract

GET `/api/health` → `{ "status": "ok", "mode": "synthetic_fixture" }`

POST `/api/demo/analyze` → Scenario JSON, returns AnalysisResult JSON.

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

`status` is `complete`, `insufficient_evidence`, or `invalid_input`.
The demo URL only uses synthetic, nonverified fixture data; use a separate production endpoint after live public-data adapters exist.

All `relations` have explicit `kind`, `weight`, and `evidence_ids`.
All `companies` hold `risk_index` and `top_paths`. `risk_index` is a deliberately simplified 0–100 demo index.
Frontend should display an unmistakable "合成資料／非實際企業分析" label when `data_mode=fixture`.
