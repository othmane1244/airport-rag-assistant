from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

SERVICE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    app_name: str = "AGA Airport API"
    environment: str = "development"
    rag_service_url: str = "http://127.0.0.1:8002"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    aerodatabox_api_key: str = ""
    gemini_api_key: str = ""
    groq_api_key: str = ""
    redis_url: str = "redis://localhost:6379/0"
    keycloak_issuer_url: str = "http://localhost:8081/realms/aga-airport"
    keycloak_jwks_url: str = "http://localhost:8081/realms/aga-airport/protocol/openid-connect/certs"
    keycloak_audience: str = "aga-api"
    auth_disabled: bool = False
    # Retrieval pipeline switches. Defaults = current behaviour.
    topic_filter_enabled: bool = True
    reranker_enabled: bool = False
    # Retrieval-distance gate applied BEFORE any LLM call: if the closest
    # candidate passage is farther than this, /chat answers "no information".
    # Value set on the 150-question benchmark only. 0 disables the gate.
    router_distance_threshold: float = 1.18

    model_config = SettingsConfigDict(
        env_file=(str(SERVICE_DIR.parent / ".env"), str(SERVICE_DIR / ".env")),
        extra="ignore",
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
