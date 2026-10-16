# Domino AI Codex working agreement

Read `docs/MVP_SCOPE.md`, `docs/DESIGN_SYSTEM.md`, `docs/API_CONTRACT.md`, and `docs/SKILLS_ARCHITECTURE.md` before editing. Use Traditional Chinese for user-facing UX.

## Working rules
1. Implement only the current milestone. Never silently expand scope.
2. Before editing, inspect the repository and report changes in 3–5 bullets. Then implement, test, and report commands/results.
3. Keep Playful Geometric CSS tokens centralized; prioritize risk graph legibility, accessibility, and reduced motion.
4. Demo fixtures must be obviously labeled synthetic. Do not invent actual company links, citations, financial impact or confidence.
5. Keep risk calculation deterministic and testable in Python. LLM may extract/interpret with citations but must never generate numerical risk scores.
6. Direct enterprise links require explicit evidence validation; inferred industry dependency is a different edge type.
7. The existing `backend/app/skills` interfaces are authoritative. Extend them rather than replacing them with generic agents.
8. No user login, no push notifications, no full queue, no baseline-model comparison, no ablation experiments in MVP.
9. No API secrets in frontend source; validate payloads and set time/cost limits on hosted integrations.
10. If data/evidence is insufficient, return `insufficient_evidence`; never force a score.
