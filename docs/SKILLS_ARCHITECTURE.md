# Skills built in starter

This project uses business-domain AI Skills, **not** the Codex/ChatGPT product's installable skill packages. They are Python modules with stable, typed interfaces and a controlled orchestrator.

Fixed stages:
1. EventParserSkill — rule-based starter, later optional LLM for structured event extraction; unknown severity remains unknown.
2. ResearchSkill — public source retrieval provider and later hybrid RAG. Default refuses to hallucinate sources and returns empty results.
3. EvidenceVerifierSkill — evidence/relationship gates based on actual support, source type, and independent corroboration.
4. KnowledgeGraphSkill — builds NetworkX directed graph from accepted edges.
5. Deterministic risk engine — max-product bounded propagation used as a **demo**; not a calibrated production risk or actual I-O model.
6. ExplainerSkill — explains results without inventing financial impact or citations.

Production TODO:
- Genuine public source connectors with lawful fetching; source hashes, publication/collection timestamps, immutable evidence IDs, conflict tracking.
- PDF document parsing and hybrid retrieval (Postgres FTS + pgvector) with page references.
- LLM gateway with cheap/strong model tiers, retry/cost/token/time budgets.
- Source independence and citation-span verification; a single `independently_verified` flag from a source is insufficient for production evidence admission.
- Explicit edge semantics: propagation direction may differ from supplier/customer wording.
- Sector input-output matrices, edge calibration, shared exposure de-duplication, historical event holdout tests.
- Task persistence, concurrency cap, auth-safe task access, versioned evidence and model state.

Do not label fixture scores as legitimate risk assessments. The synthetic fixture only tests integration wiring.
