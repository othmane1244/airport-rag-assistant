"""Optional cross-encoder reranking of candidate passages.

The API calls this route only when RERANKER_ENABLED=true. The model
(BAAI/bge-reranker-v2-m3 by default) is loaded on the first call, so the
service starts as before when reranking is not used.
"""
from functools import lru_cache

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.config import settings

router = APIRouter(tags=["rerank"])


class RerankRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    passages: list[str] = Field(min_length=1, max_length=50)


class RerankResponse(BaseModel):
    scores: list[float]
    model: str


@lru_cache(maxsize=1)
def get_reranker():
    import torch
    from sentence_transformers import CrossEncoder

    device = "cuda" if torch.cuda.is_available() else "cpu"
    return CrossEncoder(
        settings.reranker_model,
        device=device,
        max_length=512,
        local_files_only=settings.rag_local_files_only,
    )


@router.post("/rerank", response_model=RerankResponse)
def rerank(request: RerankRequest) -> RerankResponse:
    model = get_reranker()
    scores = model.predict([(request.query, passage) for passage in request.passages])
    return RerankResponse(scores=[float(s) for s in scores], model=settings.reranker_model)
