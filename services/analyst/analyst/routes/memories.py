from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from uuid import UUID
from ..deps.auth import get_current_user, UserContext
from ..db import get_db, Database
from ..models.memories import MemoryCreate, MemoryResponse, MemoryUpsertRequest
from ..models.common import BaseResponse, PaginationParams

router = APIRouter(prefix="/memories", tags=["memories"])


@router.get("/", response_model=List[MemoryResponse])
async def list_memories(
    scope: Optional[str] = Query(None),
    scope_ref: Optional[UUID] = Query(None),
    topic: Optional[str] = Query(None),
    kind: Optional[str] = Query(None),
    pagination: PaginationParams = Depends(),
    user: UserContext = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    where_clauses = ["is_active = true"]
    params = []
    param_idx = 1

    if scope:
        where_clauses.append(f"scope = ${param_idx}")
        params.append(scope)
        param_idx += 1

    if scope_ref:
        where_clauses.append(f"scope_ref = ${param_idx}")
        params.append(scope_ref)
        param_idx += 1

    if topic:
        where_clauses.append(f"topic ILIKE ${param_idx}")
        params.append(f"%{topic}%")
        param_idx += 1

    if kind:
        where_clauses.append(f"kind = ${param_idx}")
        params.append(kind)
        param_idx += 1

    where_clause = " AND ".join(where_clauses)

    query = f"""
        SELECT id, scope, scope_ref, topic, kind, content, source_thread_id,
               expires_at, created_by, created_at, is_active
        FROM feedback_memories
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """
    params.extend([pagination.limit, pagination.offset])

    try:
        results = await db.fetch(query, *params)
        return [MemoryResponse(**dict(row)) for row in results]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching memories: {str(e)}")


@router.post("/upsert", response_model=BaseResponse)
async def upsert_memories(
    request: MemoryUpsertRequest,
    user: UserContext = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    try:
        async with db.transaction() as conn:
            created_memories = []

            for memory in request.memories:
                query = """
                    INSERT INTO feedback_memories (scope, scope_ref, topic, kind, content,
                                                 source_thread_id, expires_at, created_by)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    RETURNING id, scope, scope_ref, topic, kind, content, source_thread_id,
                              expires_at, created_by, created_at, is_active
                """

                result = await conn.fetchrow(
                    query,
                    memory.scope,
                    memory.scope_ref,
                    memory.topic,
                    memory.kind,
                    memory.content,
                    memory.source_thread_id,
                    memory.expires_at,
                    UUID(user.sub) if user.sub != "dev-user" else None
                )

                created_memories.append(dict(result))

        return BaseResponse(
            message=f"Created {len(created_memories)} memories",
            data={"memories": created_memories}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error upserting memories: {str(e)}")


@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(
    memory_id: int,
    user: UserContext = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    query = """
        SELECT id, scope, scope_ref, topic, kind, content, source_thread_id,
               expires_at, created_by, created_at, is_active
        FROM feedback_memories
        WHERE id = $1 AND is_active = true
    """

    try:
        result = await db.fetchrow(query, memory_id)

        if not result:
            raise HTTPException(status_code=404, detail="Memory not found")

        return MemoryResponse(**dict(result))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching memory: {str(e)}")


@router.delete("/{memory_id}", response_model=BaseResponse)
async def deactivate_memory(
    memory_id: int,
    user: UserContext = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    query = """
        UPDATE feedback_memories
        SET is_active = false
        WHERE id = $1
        RETURNING id
    """

    try:
        result = await db.fetchrow(query, memory_id)

        if not result:
            raise HTTPException(status_code=404, detail="Memory not found")

        return BaseResponse(message="Memory deactivated")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deactivating memory: {str(e)}")