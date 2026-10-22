from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]  # repository root


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(ROOT / ".env", ROOT / "backend" / ".env"), extra="ignore")

    app_env: str = "development"
    # SQLite keeps `uvicorn` runnable with zero setup; docker-compose points this at PostgreSQL.
    database_url: str = f"sqlite:///{(ROOT / 'data' / 'neurosonic.db').as_posix()}"
    secret_key: str = "dev-insecure-secret-change-me"
    access_token_expire_minutes: int = 60 * 24
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # LLM (optional, any OpenAI-compatible endpoint)
    llm_api_key: str | None = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    # Music + embeddings (optional)
    hf_api_token: str | None = None
    embedding_provider: str = "local-tfidf"

    max_upload_mb: int = 5
    data_dir: Path = ROOT / "data"
    notch_hz: float = 50.0

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def generated_dir(self) -> Path:
        d = self.data_dir / "generated"
        d.mkdir(parents=True, exist_ok=True)
        return d


@lru_cache
def get_settings() -> Settings:
    return Settings()
