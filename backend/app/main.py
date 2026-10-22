import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from neurosonic_ml.constants import BANDS, CHANNELS, DIMENSIONS
from neurosonic_ml.music.catalog import CATALOG

from . import __version__
from .api import auth, eeg, emotion, guide, music, user
from .core.config import get_settings
from .db import models  # noqa: F401  (register tables)
from .db.session import Base, engine as db_engine
from .schemas import HealthOut
from .services import engine as svc

log = logging.getLogger("neurosonic")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.app_env != "production" and settings.secret_key.startswith("dev-insecure"):
        log.warning("Using the insecure development SECRET_KEY. Set SECRET_KEY in .env for any real deployment.")
    if settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(db_engine)  # zero-setup local dev; Postgres uses Alembic migrations
    svc.emotion_model()  # warm up (loads or trains the baseline)
    svc.guide()
    yield


app = FastAPI(title="NeuroSonic AI API", version=__version__, lifespan=lifespan,
              description="EEG -> emotion -> music. AI-estimated states are research prototypes, not medical diagnoses.")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_list, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

api = APIRouter(prefix="/api")
for r in (auth.router, eeg.router, emotion.router, music.router, user.router, guide.router):
    api.include_router(r)


@api.get("/health", response_model=HealthOut, tags=["meta"])
def health():
    try:
        with db_engine.connect() as c:
            c.execute(text("SELECT 1"))
        dbs = db_engine.dialect.name
    except Exception:  # noqa: BLE001
        dbs = "unavailable"
    g = svc.guide()
    return HealthOut(status="ok" if dbs != "unavailable" else "degraded", version=__version__, database=dbs,
                     emotion_model=svc.emotion_model().info(), llm=svc.llm().name, embedder=g.store.embedder.name,
                     music_providers=["local-synth"] + (["huggingface-musicgen"] if settings.hf_api_token else []))


@api.get("/meta", tags=["meta"])
def meta():
    n = sum(len(ops) for p, ops in app.openapi()["paths"].items() if p.startswith("/api"))
    return {"version": __version__, "name": "NeuroSonic AI",
            "counts": {"endpoints": n, "presets": len(CATALOG), "channels": len(CHANNELS), "bands": len(BANDS), "dimensions": len(DIMENSIONS)},
            "bands": {k: list(v) for k, v in BANDS.items()}, "channels": CHANNELS, "dimensions": DIMENSIONS}


app.include_router(api)


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError):
    errs = [{"field": ".".join(str(x) for x in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": "Invalid request", "errors": errs})


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception):
    log.exception("Unhandled error: %s", exc)  # details stay in logs, never in the response
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
