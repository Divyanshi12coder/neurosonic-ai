# Deployment

## Docker Compose
```bash
cp .env.example .env        # set SECRET_KEY; optionally LLM_API_KEY / HF_API_TOKEN
docker compose up --build
```
| Service | Image | Port | Notes |
|---|---|---|---|
| db | postgres:16-alpine | internal | volume `pgdata`; healthcheck gates backend start |
| backend | docker/backend.Dockerfile | 8000 | runs `alembic upgrade head` then uvicorn; non-root; volume `appdata` for generated audio |
| frontend | frontend/Dockerfile | 8080 | nginx serves the SPA and proxies `/api` to the backend |

> The Docker files were written but **not executed** in the development environment (no Docker available there). Treat the first
> `docker compose up --build` as the real test and report problems.

## Local (no Docker, SQLite)
```bash
pip install -r backend/requirements-dev.txt
PYTHONPATH=ml python -m uvicorn app.main:app --app-dir backend --reload     # PowerShell: $env:PYTHONPATH="ml"
cd frontend && npm install && npm run dev                                    # http://localhost:5173
```
PostgreSQL locally: set `DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/neurosonic`, then `cd backend && alembic upgrade head`.
Migrations were verified (upgrade/downgrade/upgrade) on SQLite only.

## Production checklist
- Strong `SECRET_KEY`, `APP_ENV=production`, restricted `CORS_ORIGINS`, TLS in front of nginx.
- Object storage for audio if running more than one backend replica.
- Rate limiting at the proxy (none built in); clean up guest accounts from `/api/auth/demo` if publicly exposed.
- `models/emotion_rf.joblib` is pinned to scikit-learn 1.8.0 (`backend/requirements.txt`); if it cannot load, the synthetic baseline is retrained at startup (can take minutes).

Hosted demo: _not deployed yet_ - add your URL here.
