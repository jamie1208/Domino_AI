# Domino AI — Codex + Skills MVP Starter

This is a **working backend Skills prototype**, not a finished real-data risk assessment system. All built-in evidence and graph relationships are synthetic, hosted under `/api/demo/analyze` only.

## Run backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
PYTHONPATH=. pytest -q
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000/docs

## Run frontend
```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```
The default API base URL is `http://127.0.0.1:8000`; override it with `VITE_API_BASE_URL`.

Demo request:
```bash
curl -X POST http://127.0.0.1:8000/api/demo/analyze \\
  -H 'Content-Type: application/json' \\
  -d '{"description":"假設材料供應中斷30天","event_type":"supply_chain","region":"虛構地區","product":"測試材料","duration_days":30,"severity":0.8,"seed_nodes":["材料產業"]}'
```

## Start with Codex
1. Create a repository from this folder and open it in Codex.
2. Ask Codex to read `AGENTS.md` plus the docs.
3. Paste `codex-prompts/01_frontend.md` and complete the task.
4. Then use prompts 02–06 one at a time, review every stage and run tests.

## Important
- Do not tell the public these demo scores are real data.
- AI Skills are implemented as modular Python domain services, not interchangeable with official ChatGPT/Codex installable Skills.
- Real-world source fetching, pgvector indexing, LLM API clients and calibrated economic modeling must still be implemented and validated in later milestones.
