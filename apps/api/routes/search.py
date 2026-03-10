"""Search routes: semantic search across signals and insights."""

from fastapi import APIRouter, status

from ..deps import CurrentUser, DbSession
from ..schemas.search import SearchRequest, SearchResponse, SearchResult
from ..services.search_service import SearchService

router = APIRouter()


@router.post("", response_model=SearchResponse)
async def search(
    data: SearchRequest,
    db: DbSession,
    user: CurrentUser,
) -> SearchResponse:
    """Perform semantic search across all content."""
    service = SearchService(db)
    results = await service.semantic_search(
        query=data.query,
        source_type=data.source_type,
        limit=data.limit,
    )
    return SearchResponse(
        results=[SearchResult(**r) for r in results],
        query=data.query,
        total=len(results),
    )
