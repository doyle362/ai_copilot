from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from uuid import UUID
from ..deps.auth import get_current_user, UserContext
from ..db import get_db, Database
from ..models.threads import ThreadCreate, ThreadResponse, MessageCreate, MessageResponse, ThreadWithMessagesResponse
from ..core.memory_distiller import MemoryDistiller

router = APIRouter(prefix="/threads", tags=["threads"])


@router.post("/", response_model=ThreadResponse)
async def create_thread(
    thread_data: ThreadCreate,
    user: UserContext = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    # Validate access for insight threads
    if thread_data.thread_type == 'insight':
        if not thread_data.insight_id or not thread_data.zone_id:
            raise HTTPException(status_code=400, detail="Insight threads require insight_id and zone_id")
        if thread_data.zone_id not in user.zone_ids:
            raise HTTPException(status_code=403, detail="Access denied to zone")

    try:
        if thread_data.thread_type == 'general':
            # For general threads, check if one already exists for this user
            existing_query = """
                SELECT id, insight_id, zone_id, thread_type, status, created_at
                FROM insight_threads
                WHERE thread_type = 'general'
                ORDER BY created_at DESC
                LIMIT 1
            """

            existing_result = await db.fetchrow(existing_query)

            if existing_result:
                # Return existing general thread
                return ThreadResponse(**existing_result)

            # Create new general thread
            create_query = """
                INSERT INTO insight_threads (thread_type)
                VALUES ($1)
                RETURNING id, insight_id, zone_id, thread_type, status, created_at
            """

            result = await db.fetchrow(create_query, 'general')
            return ThreadResponse(**result)

        else:
            # Handle insight threads (existing logic)
            existing_query = """
                SELECT id, insight_id, zone_id, thread_type, status, created_at
                FROM insight_threads
                WHERE insight_id = $1 AND zone_id = $2 AND thread_type = 'insight'
                ORDER BY created_at DESC
                LIMIT 1
            """

            existing_result = await db.fetchrow(existing_query, thread_data.insight_id, thread_data.zone_id)

            if existing_result:
                # Return existing thread
                return ThreadResponse(**existing_result)

            # Create new insight thread
            create_query = """
                INSERT INTO insight_threads (insight_id, zone_id, thread_type)
                VALUES ($1, $2, $3)
                RETURNING id, insight_id, zone_id, thread_type, status, created_at
            """

            result = await db.fetchrow(create_query, thread_data.insight_id, thread_data.zone_id, 'insight')
            return ThreadResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating thread: {str(e)}")


@router.get("/{thread_id}", response_model=ThreadWithMessagesResponse)
async def get_thread_with_messages(
    thread_id: int,
    user: UserContext = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    thread_query = """
        SELECT id, insight_id, zone_id, thread_type, status, created_at
        FROM insight_threads
        WHERE id = $1
    """

    messages_query = """
        SELECT id, thread_id, role, content, meta, created_by, created_at
        FROM thread_messages
        WHERE thread_id = $1
        ORDER BY created_at ASC
    """

    try:
        thread_result = await db.fetchrow(thread_query, thread_id)
        if not thread_result:
            raise HTTPException(status_code=404, detail="Thread not found")

        messages_result = await db.fetch(messages_query, thread_id)

        thread = ThreadResponse(**thread_result)
        messages = [MessageResponse(**dict(row)) for row in messages_result]

        return ThreadWithMessagesResponse(thread=thread, messages=messages)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching thread: {str(e)}")


@router.post("/{thread_id}/messages", response_model=MessageResponse)
async def add_message_to_thread(
    thread_id: int,
    message_data: MessageCreate,
    background_tasks: BackgroundTasks,
    user: UserContext = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    query = """
        INSERT INTO thread_messages (thread_id, role, content, meta, created_by)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, thread_id, role, content, meta, created_by, created_at
    """

    try:
        # First verify thread access through RLS
        thread_check = await db.fetchrow(
            "SELECT id FROM insight_threads WHERE id = $1",
            thread_id
        )
        if not thread_check:
            raise HTTPException(status_code=404, detail="Thread not found or access denied")

        result = await db.fetchrow(
            query,
            thread_id,
            message_data.role,
            message_data.content,
            message_data.meta,
            UUID(user.sub) if user.sub != "dev-user" else None
        )

        # Extract and store context from user messages in background
        if message_data.role == "user":
            background_tasks.add_task(
                _extract_thread_context,
                thread_id,
                user.sub,
                db
            )

        return MessageResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding message: {str(e)}")


@router.patch("/{thread_id}/status")
async def update_thread_status(
    thread_id: int,
    status: str,
    user: UserContext = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    if status not in ["open", "closed", "archived"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    query = """
        UPDATE insight_threads
        SET status = $2
        WHERE id = $1
        RETURNING id, insight_id, zone_id, status, created_at
    """

    try:
        result = await db.fetchrow(query, thread_id, status)

        if not result:
            raise HTTPException(status_code=404, detail="Thread not found or access denied")

        return ThreadResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating thread: {str(e)}")


async def _extract_thread_context(thread_id: int, user_id: str, db: Database):
    """Background task to extract context from thread conversations"""
    try:
        distiller = MemoryDistiller(db)
        memories = await distiller.distill_thread_to_memory(thread_id, user_id)

        if memories:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Extracted {len(memories)} memories from thread {thread_id}")

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error extracting context from thread {thread_id}: {str(e)}")