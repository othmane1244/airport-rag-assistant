from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.rag.embeddings import get_embedder
from app.routers.query import get_chroma_client, _collection_names, router as query_router
from app.routers.documents import router as documents_router
from app.routers.rerank import router as rerank_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Warm the embedder before health checks pass. Otherwise the first chat
    # request can exceed the API's HTTP timeout while the model loads/downloads.
    if not settings.rag_offline_test_mode:
        get_embedder(settings.rag_offline_test_mode, settings.rag_local_files_only)
    get_chroma_client()
    yield


app = FastAPI(
    title=settings.app_name,
    description="Private service for airport knowledge retrieval and RAG indexing.",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(query_router)
app.include_router(documents_router)
app.include_router(rerank_router)


@app.get("/health", tags=["health"])
def health():
    client = get_chroma_client()
    counts = {}
    available = _collection_names(client)
    for name in ("aga_documents",):
        if name in available:
            counts[name] = client.get_collection(name).count()
        else:
            counts[name] = 0
    return {
        "status": "ok",
        "service": settings.app_name,
        "collections": counts,
        "query_expansion": settings.rag_query_expansion,
    }
