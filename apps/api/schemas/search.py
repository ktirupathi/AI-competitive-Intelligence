"""Pydantic schemas for search."""

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    source_type: str | None = Field(
        None,
        pattern="^(insight|briefing|news_item|snapshot|review|social_post)$",
    )
    limit: int = Field(default=20, ge=1, le=100)


class SearchResult(BaseModel):
    id: str
    source_type: str
    source_id: str
    content_text: str
    similarity: float


class SearchResponse(BaseModel):
    results: list[SearchResult]
    query: str
    total: int
