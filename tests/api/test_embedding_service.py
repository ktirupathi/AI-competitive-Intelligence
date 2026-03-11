"""Tests for the EmbeddingService.

These tests mock the OpenAI API and database session to verify
embedding generation, storage, and search logic.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.api.services.embedding_service import (
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL,
    EmbeddingService,
)


@pytest.fixture
def mock_db() -> AsyncMock:
    """Async mock for SQLAlchemy session."""
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


@pytest.fixture
def service(mock_db: AsyncMock) -> EmbeddingService:
    return EmbeddingService(mock_db)


@pytest.fixture
def fake_embedding() -> list[float]:
    """A fake 1536-dimensional embedding vector."""
    return [0.01] * EMBEDDING_DIMENSIONS


class TestConstants:
    def test_model_name(self) -> None:
        assert EMBEDDING_MODEL == "text-embedding-3-small"

    def test_dimensions(self) -> None:
        assert EMBEDDING_DIMENSIONS == 1536


class TestGenerateEmbedding:
    @pytest.mark.asyncio
    async def test_returns_empty_without_api_key(
        self, service: EmbeddingService
    ) -> None:
        with patch("apps.api.services.embedding_service.settings") as mock_settings:
            mock_settings.openai_api_key = ""
            result = await service.generate_embedding("test text")
        assert result == []

    @pytest.mark.asyncio
    async def test_calls_openai_api(
        self, service: EmbeddingService, fake_embedding: list[float]
    ) -> None:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "data": [{"embedding": fake_embedding}]
        }

        with (
            patch("apps.api.services.embedding_service.settings") as mock_settings,
            patch("apps.api.services.embedding_service.httpx.AsyncClient") as mock_client_cls,
        ):
            mock_settings.openai_api_key = "test-key"
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await service.generate_embedding("test text")

        assert len(result) == EMBEDDING_DIMENSIONS
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_truncates_long_text(
        self, service: EmbeddingService, fake_embedding: list[float]
    ) -> None:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "data": [{"embedding": fake_embedding}]
        }

        with (
            patch("apps.api.services.embedding_service.settings") as mock_settings,
            patch("apps.api.services.embedding_service.httpx.AsyncClient") as mock_client_cls,
        ):
            mock_settings.openai_api_key = "test-key"
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            long_text = "x" * 50000
            await service.generate_embedding(long_text)

        # Verify the sent text was truncated
        call_args = mock_client.post.call_args
        sent_input = call_args.kwargs.get("json", call_args[1].get("json", {})).get("input", "")
        assert len(sent_input) <= 30000


class TestStoreEmbedding:
    @pytest.mark.asyncio
    async def test_stores_with_precomputed_embedding(
        self, service: EmbeddingService, mock_db: AsyncMock, fake_embedding: list[float]
    ) -> None:
        result = await service.store_embedding(
            source_type="snapshot",
            source_id=uuid.uuid4(),
            content_text="Test content",
            embedding=fake_embedding,
        )
        assert result is not None
        mock_db.add.assert_called_once()
        mock_db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_none_for_empty_embedding(
        self, service: EmbeddingService
    ) -> None:
        with patch.object(service, "generate_embedding", return_value=[]):
            result = await service.store_embedding(
                source_type="news_item",
                source_id=uuid.uuid4(),
                content_text="Test",
            )
        assert result is None

    @pytest.mark.asyncio
    async def test_truncates_stored_content(
        self, service: EmbeddingService, mock_db: AsyncMock, fake_embedding: list[float]
    ) -> None:
        long_content = "x" * 10000
        result = await service.store_embedding(
            source_type="review",
            source_id=uuid.uuid4(),
            content_text=long_content,
            embedding=fake_embedding,
        )
        assert result is not None
        # Check that the stored content_text was truncated to 5000
        stored_obj = mock_db.add.call_args[0][0]
        assert len(stored_obj.content_text) == 5000


class TestSemanticSearch:
    @pytest.mark.asyncio
    async def test_returns_empty_when_no_embedding(
        self, service: EmbeddingService
    ) -> None:
        with patch.object(service, "generate_embedding", return_value=[]):
            result = await service.semantic_search("query")
        assert result == []

    @pytest.mark.asyncio
    async def test_filters_by_similarity_threshold(
        self, service: EmbeddingService, mock_db: AsyncMock, fake_embedding: list[float]
    ) -> None:
        # Mock the generate_embedding and DB execute
        mock_row = MagicMock()
        mock_row.id = uuid.uuid4()
        mock_row.source_type = "snapshot"
        mock_row.source_id = uuid.uuid4()
        mock_row.content_text = "Some content"
        mock_row.similarity = 0.3  # Below threshold

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch.object(service, "generate_embedding", return_value=fake_embedding):
            results = await service.semantic_search(
                "query", similarity_threshold=0.5
            )
        # Should be filtered out since 0.3 < 0.5
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_returns_matching_results(
        self, service: EmbeddingService, mock_db: AsyncMock, fake_embedding: list[float]
    ) -> None:
        mock_row = MagicMock()
        mock_row.id = uuid.uuid4()
        mock_row.source_type = "news_item"
        mock_row.source_id = uuid.uuid4()
        mock_row.content_text = "Acme launches product"
        mock_row.similarity = 0.85

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch.object(service, "generate_embedding", return_value=fake_embedding):
            results = await service.semantic_search("Acme product launch")
        assert len(results) == 1
        assert results[0]["source_type"] == "news_item"
        assert results[0]["similarity"] == 0.85
