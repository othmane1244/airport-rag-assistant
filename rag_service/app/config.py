from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


SERVICE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    app_name: str = "AGA Airport RAG"
    environment: str = "development"
    # Preserve the existing Chroma index while keeping this service outside backend/.
    chroma_persist_dir: str = str(SERVICE_DIR.parent / "backend" / "chroma_data")
    rag_offline_test_mode: bool = False
    rag_local_files_only: bool = False
    mistral_api_key: str = ""
    # Deterministic airport-term query expansion (query.py). On by default
    # (current behaviour); set RAG_QUERY_EXPANSION=false to measure without it.
    rag_query_expansion: bool = True
    # Cross-encoder used by POST /rerank. Loaded lazily on first call.
    reranker_model: str = "BAAI/bge-reranker-v2-m3"

    @field_validator("chroma_persist_dir", mode="before")
    @classmethod
    def resolve_chroma_path(cls, value):
        path = Path(str(value))
        # Relative values historically lived beside backend/.env. Keep that
        # behavior after moving rag_service to the repository root.
        return str(
            path
            if path.is_absolute()
            else (SERVICE_DIR.parent / "backend" / path).resolve()
        )

    model_config = SettingsConfigDict(
        env_file=(
            str(SERVICE_DIR.parent / "backend" / ".env"),
            str(SERVICE_DIR / ".env"),
        ),
        extra="ignore",
    )


settings = Settings()
