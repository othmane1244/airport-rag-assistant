from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests

from app.config import settings
from app.routers import chat, documents

is_development = settings.environment.lower() == "development"

app = FastAPI(
    title=settings.app_name,
    description="Public API for the Agadir Al Massira Airport assistant.",
    version="1.0.0",
    docs_url="/docs" if is_development else None,
    redoc_url="/redoc" if is_development else None,
    openapi_url="/openapi.json" if is_development else None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(chat.router)
app.include_router(documents.router)


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
    response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


@app.get("/ready", tags=["health"])
def readiness():
    """Report ready only when the API can reach the private RAG service."""
    try:
        response = requests.get(f"{settings.rag_service_url.rstrip('/')}/health", timeout=3)
        response.raise_for_status()
        if response.json().get("status") != "ok":
            raise ValueError("RAG service is not healthy")
    except (requests.RequestException, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Assistant services are not ready") from exc
    return {"status": "ready"}
