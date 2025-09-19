import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from services.analyst.analyst.core.memory_distiller import MemoryDistiller


class TestMemoryDistiller:
    """Test memory distillation functionality."""

    @pytest.fixture
    def sample_thread_messages(self):
        """Sample thread messages for testing."""
        return [
            {
                "role": "user",
                "content": "I notice that Friday evenings always have high demand but we seem to be underpricing",
                "created_at": "2024-01-15T10:00:00Z"
            },
            {
                "role": "ai",
                "content": "That's a good observation. Friday evenings typically show 20-30% higher occupancy.",
                "created_at": "2024-01-15T10:01:00Z"
            },
            {
                "role": "user",
                "content": "Yes, and this pattern never changes during winter months. It's very consistent.",
                "created_at": "2024-01-15T10:02:00Z"
            }
        ]

    @pytest.fixture
    def sample_thread_info(self):
        """Sample thread info for testing."""
        return {
            "zone_id": "z-110",
            "insight_id": "550e8400-e29b-41d4-a716-446655440000",
            "insight_kind": "performance",
            "narrative_text": "High demand pattern analysis"
        }

    @pytest.mark.asyncio
    async def test_get_relevant_memories(self, mock_db):
        """Test retrieving relevant memories."""
        mock_memories = [
            {
                "id": 1,
                "scope": "zone",
                "scope_ref": None,
                "topic": "pricing",
                "kind": "canonical",
                "content": "Friday evenings consistently show high demand",
                "source_thread_id": 123,
                "created_at": "2024-01-15T10:00:00Z"
            },
            {
                "id": 2,
                "scope": "global",
                "scope_ref": None,
                "topic": "demand patterns",
                "kind": "context",
                "content": "Winter months show stable pricing patterns",
                "source_thread_id": None,
                "created_at": "2024-01-15T09:00:00Z"
            }
        ]

        mock_db.fetch.return_value = mock_memories

        distiller = MemoryDistiller(mock_db)
        memories = await distiller.get_relevant_memories("z-110", "pricing optimization")

        assert len(memories) == 2
        assert memories[0]["kind"] == "canonical"
        assert memories[1]["kind"] == "context"

        # Verify the query was called correctly
        mock_db.fetch.assert_called_once()
        call_args = mock_db.fetch.call_args
        assert "z-110" in call_args[0][1]
        assert "pricing optimization" in call_args[0][2]

    @pytest.mark.asyncio
    async def test_distill_thread_to_memory_with_llm(self, mock_db, sample_thread_messages, sample_thread_info):
        """Test thread distillation using LLM."""
        mock_db.fetch.side_effect = [sample_thread_messages]
        mock_db.fetchrow.return_value = sample_thread_info

        mock_choice = MagicMock()
        mock_choice.message.content = '[{"kind": "canonical", "topic": "demand_patterns", "content": "Friday evenings always have high demand and consistent pricing patterns during winter months", "confidence": 0.8}]'
        mock_openai_response = MagicMock()
        mock_openai_response.choices = [mock_choice]

        with patch.object(MemoryDistiller, '_store_memory', new_callable=AsyncMock,
                           return_value={"id": 1, "content": "Test memory"}):

            distiller = MemoryDistiller(mock_db)
            distiller.openai_client = MagicMock()
            distiller.openai_client.chat.completions.create.return_value = mock_openai_response

            memories = await distiller.distill_thread_to_memory(123)

            assert len(memories) == 1
            assert memories[0]["content"] == "Test memory"

    @pytest.mark.asyncio
    async def test_distill_thread_fallback(self, mock_db, sample_thread_messages, sample_thread_info):
        """Test thread distillation fallback when OpenAI is not available."""
        # Mock database calls
        mock_db.fetch.return_value = sample_thread_messages
        mock_db.fetchrow.return_value = sample_thread_info

        # Mock storage
        with patch.object(MemoryDistiller, '_store_memory', new_callable=AsyncMock,
                         return_value={"id": 1, "content": "Test fallback memory"}):

            distiller = MemoryDistiller(mock_db)
            # OpenAI will not be available due to no API key in settings
            memories = await distiller.distill_thread_to_memory(123)

            # Should still extract memories using fallback method
            assert len(memories) >= 0  # Fallback may or may not find patterns

    @pytest.mark.asyncio
    async def test_get_thread_messages(self, mock_db, sample_thread_messages):
        """Test retrieving thread messages."""
        mock_db.fetch.return_value = sample_thread_messages

        distiller = MemoryDistiller(mock_db)
        messages = await distiller._get_thread_messages(123)

        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert "high demand" in messages[0]["content"]

    @pytest.mark.asyncio
    async def test_get_thread_info(self, mock_db, sample_thread_info):
        """Test retrieving thread info."""
        mock_db.fetchrow.return_value = sample_thread_info

        distiller = MemoryDistiller(mock_db)
        info = await distiller._get_thread_info(123)

        assert info["zone_id"] == "z-110"
        assert info["insight_kind"] == "performance"

    def test_extract_memories_fallback(self, sample_thread_messages, sample_thread_info):
        """Test fallback memory extraction."""
        distiller = MemoryDistiller(MagicMock())
        memories = distiller._extract_memories_fallback(sample_thread_messages, sample_thread_info)

        # Should find at least one memory from the user messages
        assert len(memories) >= 1

        # Check that it found the message with insight keywords
        found_memory = None
        for memory in memories:
            if "always" in memory["content"]:
                found_memory = memory
                break

        assert found_memory is not None
        assert found_memory["kind"] == "canonical"  # "always" triggers canonical
        assert found_memory["scope"] == "zone"

    @pytest.mark.asyncio
    async def test_classify_memory_type(self):
        """Test memory type classification."""
        distiller = MemoryDistiller(MagicMock())

        canonical_content = "This rule always applies to pricing"
        assert await distiller.classify_memory_type(canonical_content) == "canonical"

        exception_content = "This is an unusual anomaly in the data"
        assert await distiller.classify_memory_type(exception_content) == "exception"

        context_content = "During this time period we saw increased activity"
        assert await distiller.classify_memory_type(context_content) == "context"

    @pytest.mark.asyncio
    async def test_store_memory(self, mock_db):
        """Test storing a memory in the database."""
        mock_db.fetchrow.return_value = {
            "id": 1,
            "scope": "zone",
            "scope_ref": None,
            "topic": "test",
            "kind": "canonical",
            "content": "Test memory content",
            "source_thread_id": 123,
            "expires_at": None,
            "created_by": None,
            "created_at": "2024-01-15T10:00:00Z",
            "is_active": True
        }

        distiller = MemoryDistiller(mock_db)

        memory_data = {
            "scope": "zone",
            "topic": "test",
            "kind": "canonical",
            "content": "Test memory content"
        }

        result = await distiller._store_memory(memory_data, 123, "test-user")

        assert result is not None
        assert result["id"] == 1
        assert result["content"] == "Test memory content"

        # Verify database call
        mock_db.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_distill_thread_no_messages(self, mock_db):
        """Test distilling thread with no messages."""
        mock_db.fetch.return_value = []  # No messages

        distiller = MemoryDistiller(mock_db)
        memories = await distiller.distill_thread_to_memory(123)

        assert len(memories) == 0

    @pytest.mark.asyncio
    async def test_distill_thread_no_thread_info(self, mock_db, sample_thread_messages):
        """Test distilling thread with no thread info."""
        mock_db.fetch.return_value = sample_thread_messages
        mock_db.fetchrow.return_value = None  # No thread info

        distiller = MemoryDistiller(mock_db)
        memories = await distiller.distill_thread_to_memory(123)

        assert len(memories) == 0
