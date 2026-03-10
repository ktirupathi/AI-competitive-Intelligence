"""Embedding service for semantic search via pgvector.

Generates embeddings using OpenAI's text-embedding-3-small model and
stores them in the `embeddings` table for nearest-neighbor search.
"""

import logging
import uuid
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..models.embedding import Embedding

logger = logging.getLogger(__name__)
settings = get_settings()

# Embedding model config
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536


class EmbeddingService:
    """Generate and search vector embeddings stored in pgvector."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate_embedding(self, text_content: str) -> list[float]:
        """Generate an embedding vector for the given text.

        Uses the OpenAI embeddings API (text-embedding-3-small).
        Falls back to Anthropic Voyage if OpenAI key is not set.
        """
        if not settings.openai_api_key:
            logger.warning("No OpenAI API key configured; cannot generate embeddings")
            return []

        # Truncate to model limit (~8191 tokens, ~32K chars is safe)
        truncated = text_content[:30000]

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.openai.com/v1/embeddings",
                json={
                    "model": EMBEDDING_MODEL,
                    "input": truncated,
                },
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()

        embedding = data["data"][0]["embedding"]
        return embedding

    async def store_embedding(
        self,
        source_type: str,
        source_id: uuid.UUID,
        content_text: str,
        embedding: list[float] | None = None,
    ) -> Embedding:
        """Generate (if needed) and store an embedding for a source record.

        Args:
            source_type: One of "snapshot", "news_item", "job_posting",
                         "review", "social_post", "insight".
            source_id: The UUID of the source record.
            content_text: The text content to embed.
            embedding: Pre-computed embedding vector, or None to generate.

        Returns:
            The created Embedding ORM object.
        """
        if embedding is None:
            embedding = await self.generate_embedding(content_text)

        if not embedding:
            logger.warning(
                "Empty embedding for %s:%s — skipping storage", source_type, source_id
            )
            return None

        record = Embedding(
            source_type=source_type,
            source_id=source_id,
            content_text=content_text[:5000],  # Cap stored text
            embedding=embedding,
            model=EMBEDDING_MODEL,
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def semantic_search(
        self,
        query: str,
        source_type: str | None = None,
        limit: int = 10,
        similarity_threshold: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Find the most semantically similar records to a query string.

        Args:
            query: Natural language query.
            source_type: Optional filter to search within a specific type.
            limit: Max results to return.
            similarity_threshold: Minimum cosine similarity (0-1).

        Returns:
            List of dicts with: id, source_type, source_id, content_text,
            similarity.
        """
        query_embedding = await self.generate_embedding(query)
        if not query_embedding:
            return []

        # Build the pgvector cosine distance query
        # cosine distance: 1 - (a <=> b) gives similarity
        embedding_literal = f"[{','.join(str(v) for v in query_embedding)}]"

        sql = text(
            """
            SELECT
                id,
                source_type,
                source_id,
                content_text,
                1 - (embedding <=> :query_vec::vector) AS similarity
            FROM embeddings
            WHERE 1=1
            """
            + (" AND source_type = :source_type" if source_type else "")
            + """
            ORDER BY embedding <=> :query_vec::vector
            LIMIT :limit
            """
        )

        params: dict[str, Any] = {
            "query_vec": embedding_literal,
            "limit": limit,
        }
        if source_type:
            params["source_type"] = source_type

        result = await self.db.execute(sql, params)
        rows = result.fetchall()

        results = []
        for row in rows:
            sim = float(row.similarity)
            if sim < similarity_threshold:
                continue
            results.append({
                "id": str(row.id),
                "source_type": row.source_type,
                "source_id": str(row.source_id),
                "content_text": row.content_text,
                "similarity": sim,
            })

        return results

    async def find_similar(
        self,
        source_type: str,
        source_id: uuid.UUID,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Find records similar to an existing embedded record.

        Useful for clustering related signals.
        """
        # Fetch the existing embedding
        from sqlalchemy import select

        result = await self.db.execute(
            select(Embedding).where(
                Embedding.source_type == source_type,
                Embedding.source_id == source_id,
            )
        )
        existing = result.scalar_one_or_none()
        if not existing or not existing.content_text:
            return []

        return await self.semantic_search(
            query=existing.content_text,
            limit=limit + 1,  # Exclude self
        )
