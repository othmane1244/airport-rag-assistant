"""HTTP client for the separate RAG service."""

from threading import local

import requests
from requests.adapters import HTTPAdapter

from app.config import settings


class RagServiceUnavailable(Exception):
    """The RAG service did not return a usable response."""


_thread_sessions = local()


def _session() -> requests.Session:
    """Keep HTTP connections reusable without sharing mutable sessions across threads."""
    session = getattr(_thread_sessions, "session", None)
    if session is None:
        session = requests.Session()
        adapter = HTTPAdapter(pool_connections=4, pool_maxsize=4)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        _thread_sessions.session = session
    return session


def query_knowledge(query: str, n_results: int = 3) -> list[dict]:
    try:
        response = _session().post(
            f"{settings.rag_service_url.rstrip('/')}/query",
            json={"query": query, "n_results": n_results, "audience": "voyageur"},
            timeout=20,
        )
        response.raise_for_status()
        return response.json().get("results", [])
    except (requests.RequestException, ValueError) as exc:
        raise RagServiceUnavailable("RAG service request failed") from exc


def rerank_passages(query: str, passages: list[str]) -> list[float]:
    """Score (query, passage) pairs with the RAG service's cross-encoder."""
    try:
        response = _session().post(
            f"{settings.rag_service_url.rstrip('/')}/rerank",
            json={"query": query, "passages": passages},
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["scores"]
    except (requests.RequestException, ValueError, KeyError) as exc:
        raise RagServiceUnavailable("RAG rerank request failed") from exc
