# docker/

`backend.Dockerfile` builds the FastAPI service (build context = repo root so it can copy `ml/` and `models/`).
The frontend image is built from `frontend/Dockerfile` (multi-stage: Vite build -> nginx with `/api` proxy).
Everything is wired together by `../docker-compose.yml`.
