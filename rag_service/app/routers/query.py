from functools import lru_cache
import re

import chromadb
from fastapi import APIRouter

from app.config import settings
from app.rag.embeddings import get_embedder
from app.schemas import QueryRequest, QueryResponse, QueryResult

router = APIRouter(tags=["retrieval"])
COLLECTIONS = ("aga_documents",)


def _expand_domain_query(query: str) -> str:
    """Add a small English retrieval anchor for airport terms.

    BGE-M3 is multilingual, but the pilot showed that short Arabic and French
    queries for parking and the IATA code can rank unrelated airport PDFs
    above the matching source. Keep the user's wording and add only a
    deterministic domain synonym; no external translation or LLM is called.
    """
    normalized = query.casefold()
    anchors = []
    has_arabic = bool(re.search(r"[\u0600-\u06FF]", normalized))
    if has_arabic:
        if re.search(r"ركن|موقف|مواقف", normalized):
            anchors.append("Agadir airport car parking")
        if re.search(r"إياتا|اياتا", normalized):
            anchors.append("Agadir airport IATA code")
    else:
        if re.search(r"stationnement|stationner|garer|se garer", normalized):
            anchors.append("Agadir airport car parking")
    if not anchors:
        return query
    return f"{query} {' '.join(anchors)}"


@lru_cache(maxsize=1)
def get_chroma_client():
    """Reuse one persistent Chroma client for the lifetime of this process."""
    return chromadb.PersistentClient(path=settings.chroma_persist_dir)


def _collection_names(client) -> set[str]:
    return {
        item if isinstance(item, str) else item.name
        for item in client.list_collections()
    }


def _query_collection(
    client,
    available: set[str],
    name: str,
    vector: list[list[float]],
    limit: int,
    audience: str | None,
):
    if name not in available:
        return []
    collection = client.get_collection(name)

    collection_count = collection.count()
    if collection_count == 0:
        return []

    options = {"query_embeddings": vector, "n_results": min(limit, collection_count)}
    if name == "aga_documents" and audience:
        options["where"] = {"audience": audience}
    result = collection.query(**options)
    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]

    return [
        QueryResult(
            text=text,
            metadata=metadata or {},
            distance=distances[index] if index < len(distances) else None,
        )
        for index, (text, metadata) in enumerate(zip(documents, metadatas))
    ]


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    embedder = get_embedder(
        settings.rag_offline_test_mode, settings.rag_local_files_only
    )
    retrieval_query = (
        _expand_domain_query(request.query) if settings.rag_query_expansion else request.query
    )
    vector = embedder.embed([retrieval_query])
    client = get_chroma_client()
    available = _collection_names(client)

    results = []
    for name in COLLECTIONS:
        results.extend(
            _query_collection(
                client, available, name, vector, request.n_results, request.audience
            )
        )
    results.sort(key=lambda item: item.distance if item.distance is not None else float("inf"))
    return QueryResponse(results=results[: request.n_results])
