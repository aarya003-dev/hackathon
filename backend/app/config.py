"""Application configuration.

All runtime settings are loaded from environment variables / `.env` through
Pydantic settings. Never call ``os.getenv`` elsewhere in the application.
"""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "Code Review Agent"
    cors_origins: str = "http://localhost:5173"

    # Ingestion source: which adapter is the active intake path.
    #   local_git -> watch/push a local repo (no deployment, no port forwarding)
    #   webhook   -> GitHub webhook adapter (requires inbound reachability)
    ingestion_source: str = "local_git"
    ingest_secret: str = "dev-secret"

    # Local-git ingestion
    git_repo_path: str | None = None
    git_poll_seconds: int = 10

    # GenAI gateway (https://genailab.tcs.in) - model names per PLAN.md
    genai_gateway_url: str = "https://genailab.tcs.in"
    genai_api_key: str = ""
    #   demo   -> deterministic offline gateway (tests/local dev, no credentials)
    #   http   -> real GenAI Lab gateway via the HTTPX client
    #   gemini -> Google Gemini via the google-genai SDK (GEMINI_API_KEY)
    llm_backend: str = "demo"
    llm_timeout_seconds: float = 60.0
    llm_max_retries: int = 2
    model_triage: str = "azure/genailab-maas-gpt-4o-mini"
    model_core_review: str = "genailab-maas-gpt-5.3-codex"
    model_security: str = "azure_ai/genailab-maas-DeepSeek-R1"
    model_summarizer: str = "gemini-2.5-pro"
    model_embeddings: str = "azure/genailab-maas-text-embedding-3-large"

    # Gemini backend (LLM_BACKEND=gemini): google-genai SDK credentials/model.
    gemini_api_key: str = ""
    model_gemini: str = "gemini-3.6-flash"

    # RAG pipeline
    embedding_dim: int = 256
    rag_guidelines_dir: str = "data/guidelines"

    # Review-output publication: dry_run (default) | none
    publish_mode: str = "dry_run"

    @field_validator("llm_backend")
    @classmethod
    def _validate_llm_backend(cls, value: str) -> str:
        if value not in ("demo", "http", "gemini"):
            raise ValueError("LLM_BACKEND must be 'demo', 'http', or 'gemini'")
        return value

    @field_validator("embedding_dim")
    @classmethod
    def _validate_embedding_dim(cls, value: int) -> int:
        if value < 8:
            raise ValueError("EMBEDDING_DIM must be >= 8")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
