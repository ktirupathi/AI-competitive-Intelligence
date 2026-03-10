"""Semantic search service using pgvector embeddings."""

import logging
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class SearchService:
    """Semantic search across insights, signals, and briefings."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = EmbeddingService(db)

    async def generate_embedding(self, text_content: str) -> list[float]:
        """Generate an embedding vector for the given text."""
        return await self.embedding_service.generate_embedding(text_content)

    async def semantic_search(
        self,
        query: str,
        workspace_id: uuid.UUID | None = None,
        source_type: str | None = None,
        limit: int = 20,
        similarity_threshold: float = 0.3,
    ) -> list[dict[str, Any]]:
        """Search across all embedded content using semantic similarity.

        Args:
            query: Natural language search query.
            workspace_id: Optional workspace scope filter.
            source_type: Optional filter by source type.
            limit: Max results to return.
            similarity_threshold: Minimum cosine similarity (0-1).

        Returns:
            List of search results with similarity scores.
        """
        query_embedding = await self.embedding_service.generate_embedding(query)
        if not query_embedding:
            return []

        embedding_literal = f"[{','.join(str(v) for v in query_embedding)}]"

        # Build query with optional workspace filter
        where_clauses = ["1=1"]
        params: dict[str, Any] = {
            "query_vec": embedding_literal,
            "limit": limit,
            "threshold": similarity_threshold,
        }

        if source_type:
            where_clauses.append("e.source_type = :source_type")
            params["source_type"] = source_type

        sql = text(f"""
            SELECT
                e.id,
                e.source_type,
                e.source_id,
                e.content_text,
                1 - (e.embedding <=> :query_vec::vector) AS similarity
            FROM embeddings e
            WHERE {" AND ".join(where_clauses)}
              AND 1 - (e.embedding <=> :query_vec::vector) >= :threshold
            ORDER BY e.embedding <=> :query_vec::vector
            LIMIT :limit
        """)

        result = await self.db.execute(sql, params)
        rows = result.fetchall()

        results = []
        for row in rows:
            results.append({
                "id": str(row.id),
                "source_type": row.source_type,
                "source_id": str(row.source_id),
                "content_text": row.content_text,
                "similarity": float(row.similarity),
            })

        return results

    async def search_insights(
        self,
        query: str,
        workspace_id: uuid.UUID | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search specifically within insights."""
        return await self.semantic_search(
            query=query,
            workspace_id=workspace_id,
            source_type="insight",
            limit=limit,
        )

    async def search_briefings(
        self,
        query: str,
        workspace_id: uuid.UUID | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search specifically within briefings."""
        return await self.semantic_search(
            query=query,
            workspace_id=workspace_id,
            source_type="briefing",
            limit=limit,
        )
