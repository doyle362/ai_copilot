import logging
from typing import Dict, List, Optional, Any
from openai import OpenAI
import numpy as np
from ..db import Database
from ..config import settings

logger = logging.getLogger(__name__)


class MemoryDistiller:
    def __init__(self, db: Database):
        self.db = db
        self.openai_client = None
        if settings.openai_api_key:
            self.openai_client = OpenAI(api_key=settings.openai_api_key)

    async def distill_thread_to_memory(
        self,
        thread_id: int,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Extract key insights from a thread and convert to memories"""

        try:
            # Get thread messages
            messages = await self._get_thread_messages(thread_id)

            if not messages:
                return []

            # Get thread context (zone, etc.)
            thread_info = await self._get_thread_info(thread_id)

            if not thread_info:
                return []

            # Use LLM to extract memories
            memories = await self._extract_memories_with_llm(messages, thread_info)

            # Store memories
            stored_memories = []
            for memory in memories:
                stored_memory = await self._store_memory(memory, thread_id, user_id)
                if stored_memory:
                    stored_memories.append(stored_memory)

            return stored_memories

        except Exception as e:
            logger.error(f"Error distilling thread {thread_id} to memory: {str(e)}")
            return []

    async def get_relevant_memories(
        self,
        zone_id: str,
        query: str,
        scope: str = "zone",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get memories relevant to a query using semantic search"""

        try:
            # For now, use simple text matching since we don't have vector embeddings set up
            # In production, you'd use vector similarity search

            memories_query = """
                SELECT m.id, m.scope, m.scope_ref, m.topic, m.kind, m.content,
                       m.source_thread_id, m.created_at
                FROM feedback_memories m
                WHERE m.is_active = true
                    AND (m.scope = 'global' OR
                         (m.scope = 'zone' AND m.scope_ref::text LIKE $1))
                    AND (m.content ILIKE $2 OR m.topic ILIKE $2)
                ORDER BY m.created_at DESC
                LIMIT $3
            """

            results = await self.db.fetch(
                memories_query,
                f"%{zone_id}%",
                f"%{query}%",
                limit
            )

            return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Error getting relevant memories: {str(e)}")
            return []

    async def _get_thread_messages(self, thread_id: int) -> List[Dict]:
        """Get all messages for a thread"""

        query = """
            SELECT role, content, meta, created_at
            FROM thread_messages
            WHERE thread_id = $1
            ORDER BY created_at ASC
        """

        try:
            results = await self.db.fetch(query, thread_id)
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error fetching thread messages: {str(e)}")
            return []

    async def _get_thread_info(self, thread_id: int) -> Optional[Dict]:
        """Get thread context information"""

        query = """
            SELECT t.zone_id, t.insight_id, i.kind as insight_kind, i.narrative_text
            FROM insight_threads t
            LEFT JOIN insights i ON t.insight_id = i.id
            WHERE t.id = $1
        """

        try:
            result = await self.db.fetchrow(query, thread_id)
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error fetching thread info: {str(e)}")
            return None

    async def _extract_memories_with_llm(
        self,
        messages: List[Dict],
        thread_info: Dict
    ) -> List[Dict[str, Any]]:
        """Use LLM to extract key memories from thread conversation"""

        if not self.openai_client:
            logger.warning("OpenAI API key not configured, using fallback memory extraction")
            return self._extract_memories_fallback(messages, thread_info)

        try:
            # Build conversation context
            conversation = "\n".join([
                f"{msg['role']}: {msg['content']}"
                for msg in messages
            ])

            system_prompt = """
You are a memory extraction system for parking analytics. Extract key insights,
rules, exceptions, and context from conversations.

OUTPUT: JSON array of memories in this format:
[{
    "kind": "canonical|context|exception",
    "topic": "brief topic description",
    "content": "detailed memory content",
    "confidence": 0.0-1.0
}]

Focus on:
- Canonical: Universal rules or patterns
- Context: Situation-specific insights
- Exception: Notable anomalies or special cases
"""

            user_prompt = f"""
Zone: {thread_info.get('zone_id', 'unknown')}
Insight Type: {thread_info.get('insight_kind', 'general')}
Context: {thread_info.get('narrative_text', 'No context')}

Conversation:
{conversation}

Extract memories from this conversation:
"""

            response = self.openai_client.chat.completions.create(
                model=settings.openai_model_fast,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )

            content = response.choices[0].message.content

            # Parse JSON response
            import json
            try:
                memories = json.loads(content)
                if not isinstance(memories, list):
                    memories = [memories]

                # Add scope information
                for memory in memories:
                    memory['scope'] = 'zone'
                    memory['scope_ref'] = thread_info['zone_id']

                return memories

            except json.JSONDecodeError:
                logger.error(f"Failed to parse memory extraction response: {content}")
                return self._extract_memories_fallback(messages, thread_info)

        except Exception as e:
            logger.error(f"Error extracting memories with LLM: {str(e)}")
            return self._extract_memories_fallback(messages, thread_info)

    def _extract_memories_fallback(
        self,
        messages: List[Dict],
        thread_info: Dict
    ) -> List[Dict[str, Any]]:
        """Fallback memory extraction using simple heuristics"""

        memories = []

        # Look for user messages with keywords that indicate insights
        insight_keywords = ['always', 'never', 'usually', 'pattern', 'trend', 'rule', 'exception']

        for msg in messages:
            if msg['role'] == 'user':
                content_lower = msg['content'].lower()

                # Check for insight patterns
                if any(keyword in content_lower for keyword in insight_keywords):
                    memory_kind = 'canonical'
                    if 'exception' in content_lower or 'unusual' in content_lower:
                        memory_kind = 'exception'
                    elif 'when' in content_lower or 'during' in content_lower:
                        memory_kind = 'context'

                    memories.append({
                        'kind': memory_kind,
                        'topic': 'user_feedback',
                        'content': msg['content'][:500],  # Truncate long messages
                        'scope': 'zone',
                        'scope_ref': thread_info.get('zone_id')
                    })

        return memories

    async def _store_memory(
        self,
        memory_data: Dict,
        thread_id: int,
        user_id: Optional[str]
    ) -> Optional[Dict]:
        """Store a memory in the database"""

        try:
            query = """
                INSERT INTO feedback_memories
                (scope, scope_ref, topic, kind, content, source_thread_id, created_by)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id, scope, scope_ref, topic, kind, content,
                          source_thread_id, expires_at, created_by, created_at, is_active
            """

            # Convert scope_ref to UUID if it's a zone_id string
            scope_ref = None
            if memory_data.get('scope_ref'):
                try:
                    from uuid import UUID
                    scope_ref = UUID(memory_data['scope_ref'])
                except (ValueError, TypeError):
                    scope_ref = None

            # Handle UUID for dev user
            user_uuid = None
            if user_id and user_id != "dev-user":
                try:
                    from uuid import UUID
                    user_uuid = UUID(user_id)
                except (ValueError, TypeError):
                    user_uuid = None

            result = await self.db.fetchrow(
                query,
                memory_data.get('scope', 'zone'),
                scope_ref,
                memory_data.get('topic'),
                memory_data.get('kind', 'context'),
                memory_data.get('content'),
                thread_id,
                user_uuid
            )

            return dict(result) if result else None

        except Exception as e:
            logger.error(f"Error storing memory: {str(e)}")
            return None

    async def classify_memory_type(self, content: str) -> str:
        """Classify memory content into canonical, context, or exception"""

        # Simple keyword-based classification
        content_lower = content.lower()

        if any(word in content_lower for word in ['always', 'never', 'rule', 'policy']):
            return 'canonical'
        elif any(word in content_lower for word in ['exception', 'unusual', 'anomaly', 'outlier']):
            return 'exception'
        else:
            return 'context'