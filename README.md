# CutCost

Find the cheapest safe place to buy anything.

CutCost scans merchants worldwide, estimates true total cost including shipping and duties, checks merchant trustworthiness, and recommends the best buying option.

## Stack

- **Frontend:** Next.js 15, React 19, Tailwind CSS 4, next-intl
- **Backend:** Python 3.12+, FastAPI, SQLAlchemy 2.0, ARQ
- **Database:** PostgreSQL 16
- **Cache/Queue:** Redis 7 (Upstash)
- **Hosting:** Vercel (frontend) + Railway (backend + DB)

## Local Development

```bash
# Start Postgres + Redis
docker compose up -d

# Backend
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows
pip install -e ".[dev]"
alembic upgrade head
python -m seeds.seed
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## Deployment

- **Frontend:** Push to `main` → auto-deploys on Vercel
- **Backend:** Push to `main` → auto-deploys on Railway

## Project Structure

```
cutcost/
├── backend/          Python API + workers + extractors
│   ├── app/
│   │   ├── api/          Route handlers
│   │   ├── models/       SQLAlchemy ORM
│   │   ├── services/     Business logic
│   │   ├── extractors/   Per-merchant data extraction
│   │   ├── workers/      Background jobs (ARQ)
│   │   └── utils/        Shared utilities
│   ├── migrations/       Alembic DB migrations
│   ├── seeds/            Seed data + loader
│   └── tests/
└── frontend/         Next.js web app
    └── src/
        ├── app/          Pages (App Router)
        ├── components/   React components
        └── lib/          API client, types, utils
```
