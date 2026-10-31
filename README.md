# EstateAI

AI-powered property discovery, neighbourhood intelligence, and investment analysis for **Delhi NCR**.

This repo implements the EstateAI PRD as a **FastAPI modular monolith** (not Django), with a responsive web UI. The earlier LangGraph price-prediction prototype is preserved under legacy endpoints.

## Stack

- **Backend:** FastAPI, SQLAlchemy, JWT auth, Pydantic v2
- **DB:** SQLite by default (`data/estateai.db`); set `DATABASE_URL` for PostgreSQL
- **AI:** Rule-based NL search + tool-grounded chat; optional Gemini for explanations; legacy LangGraph `/predict`
- **Frontend:** Static SPA at `/app` (served by FastAPI)

## Quick start

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Optional keys in .env (prediction / LLM explanations / Maps tools)
# GOOGLE_API_KEY=
# GOOGLE_MAPS_API_KEY=
# NEWS_API_KEY=
# SECRET_KEY=change-me

./run.sh
```

Open:

- API docs: http://localhost:8000/docs
- Product UI: http://localhost:8000/app/
- Health: http://localhost:8000/

Demo users (seeded automatically on first boot):

| Email | Password | Role |
|-------|----------|------|
| buyer@estateai.example | Buyer@12345 | consumer |
| agent@estateai.example | Agent@12345 | agent |
| admin@estateai.example | Admin@12345 | admin |

Re-seed manually:

```bash
PYTHONPATH=. python -m scripts.seed_data
```

## API surface (`/api/v1`)

| Area | Endpoints |
|------|-----------|
| Auth | `POST /auth/register`, `/auth/login`, `GET /accounts/me`, `PATCH /accounts/me/preferences` |
| Search | `GET /properties`, `GET /properties/{id}` |
| Neighbourhood | `GET /properties/{id}/neighbourhood` |
| Price / yield | `GET /properties/{id}/price-analysis`, `POST /investment/calculate` |
| Leads | `POST /leads`, `GET /agent/leads`, `PATCH /agent/leads/{id}` |
| AI | `POST /ai/search`, `POST /ai/chat` |
| Legacy | `POST /predict`, `POST /llm` |

Errors follow the PRD envelope: `{ "error": { "code", "message", "fields", "request_id" } }`.

## What this MVP covers (vs PRD)

**Done (P0 foundation):** roles/auth, listings + search, locality seed for NCR, neighbourhood amenities with distance + disclosures, deterministic yield calculator, lead inbox APIs, tool-grounded AI search/chat, OpenAPI docs, sample inventory.

**Intentionally deferred:** PostGIS / live routing provider, RERA adapters, Celery, Next.js rewrite, paid subscriptions, bulk CSV import UI, full verification workflow UI.

## Product principles enforced in code

- Hard search constraints applied before ranking
- Missing market data → `insufficient_data`, never fabricated benchmarks
- Investment maths are pure Python functions (version `v1`)
- AI answers cite tool outputs and attach limitations
- Public listing browse does not require login
