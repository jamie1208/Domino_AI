# Domino AI — MVP scope (confirmed requirements F01–F63)

## Goal
End-to-end demonstrable flow: scenario input → editable parameters → verified evidence-backed entity graph → deterministic cascading exposure → risk explanation + cited edge detail. Taiwan listed/OTC companies are planned targets; initial prototype can use ~10–20 selected companies and one supply-chain scenario. Only public, lawfully obtained information.

## MVP includes
- React + TypeScript + Vite frontend, Playful Geometric tokens, 4 pages: Dashboard, Scenario, Analysis, Company.
- React Flow graph with different styles and labels for verified-direct / industry-inferred / unverified candidates (unverified NOT included in deterministic propagation).
- FastAPI backend, PostgreSQL schema, NetworkX risk engine.
- Skill roles: parsing, retrieval, evidence verification, KG building, explanation; fixed stage orchestration.
- Start with synthetic demo fixture, then replace with cited real public documents; never merge the two modes in UI.
- First historical case validation with a date cut-off and data-quality caveats.
- Lightweight sync analyses and independently controlled accepted async deep analyses.
- Basic concurrency cap with immediate busy responses, no waiting queue.

## Deferred (do not delete from long-term specification)
- Complete 4-dimension resilience scoring, full company comparison, multi-event joint overlap model, PDF, 7/30/90 trends, broad 50–100 company deep coverage, full historical backtest UX, three-case validation as mature release milestone, scenario sensitivity UI.

## Hard constraints
- Risk score = relative model exposure, not observed damage, event likelihood, forecast or financial advice.
- Never mark non-disclosure as evidence of relationship absence.
- No credentials pushed to browser, no login, no unsolicited notifications.
- F61: no baseline-model comparisons or ablations.
