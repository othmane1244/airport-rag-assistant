from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    n_results: int = Field(default=3, ge=1, le=20)
    audience: str | None = Field(default=None, max_length=80)


class QueryResult(BaseModel):
    text: str
    metadata: dict = Field(default_factory=dict)
    distance: float | None = None


class QueryResponse(BaseModel):
    results: list[QueryResult]
