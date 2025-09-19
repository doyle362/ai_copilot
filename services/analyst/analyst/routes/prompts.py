from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from uuid import UUID
from ..deps.auth import get_current_user, UserContext, require_role
from ..db import get_db, Database
from ..models.prompts import PromptVersionCreate, PromptVersionResponse, PromptVersionActivateRequest
from ..models.common import BaseResponse

router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.get("/", response_model=List[PromptVersionResponse])
async def list_prompt_versions(
    scope: Optional[str] = Query(None),
    scope_ref: Optional[UUID] = Query(None),
    active_only: bool = Query(False),
    user: UserContext = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    where_clauses = []
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

    if active_only:
        where_clauses.append("is_active = true")

    where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

    query = f"""
        SELECT id, scope, scope_ref, version, title, system_prompt,
               created_by, created_at, is_active
        FROM agent_prompt_versions
        WHERE {where_clause}
        ORDER BY scope, scope_ref, version DESC
    """

    try:
        results = await db.fetch(query, *params)
        return [PromptVersionResponse(**dict(row)) for row in results]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching prompt versions: {str(e)}")


@router.post("/", response_model=PromptVersionResponse)
async def create_prompt_version(
    prompt_data: PromptVersionCreate,
    user: UserContext = Depends(require_role("approver")),
    db: Database = Depends(get_db)
):
    # Get the next version number for this scope
    version_query = """
        SELECT COALESCE(MAX(version), 0) + 1 as next_version
        FROM agent_prompt_versions
        WHERE scope = $1 AND scope_ref IS NOT DISTINCT FROM $2
    """

    insert_query = """
        INSERT INTO agent_prompt_versions (scope, scope_ref, version, title, system_prompt, created_by)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id, scope, scope_ref, version, title, system_prompt,
                  created_by, created_at, is_active
    """

    try:
        async with db.transaction() as conn:
            next_version = await conn.fetchval(version_query, prompt_data.scope, prompt_data.scope_ref)

            result = await conn.fetchrow(
                insert_query,
                prompt_data.scope,
                prompt_data.scope_ref,
                next_version,
                prompt_data.title,
                prompt_data.system_prompt,
                UUID(user.sub) if user.sub != "dev-user" else None
            )

        return PromptVersionResponse(**dict(result))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating prompt version: {str(e)}")


@router.post("/activate", response_model=BaseResponse)
async def activate_prompt_version(
    request: PromptVersionActivateRequest,
    user: UserContext = Depends(require_role("approver")),
    db: Database = Depends(get_db)
):
    try:
        async with db.transaction() as conn:
            # Get the prompt version to activate
            version_info = await conn.fetchrow(
                "SELECT scope, scope_ref FROM agent_prompt_versions WHERE id = $1",
                request.version_id
            )

            if not version_info:
                raise HTTPException(status_code=404, detail="Prompt version not found")

            # Deactivate all other versions for this scope
            await conn.execute("""
                UPDATE agent_prompt_versions
                SET is_active = false
                WHERE scope = $1 AND scope_ref IS NOT DISTINCT FROM $2
            """, version_info['scope'], version_info['scope_ref'])

            # Activate the requested version
            result = await conn.execute(
                "UPDATE agent_prompt_versions SET is_active = true WHERE id = $1",
                request.version_id
            )

            if result == "UPDATE 0":
                raise HTTPException(status_code=404, detail="Prompt version not found")

        return BaseResponse(message="Prompt version activated")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error activating prompt: {str(e)}")


@router.get("/active", response_model=PromptVersionResponse)
async def get_active_prompt(
    scope: str = Query(...),
    scope_ref: Optional[UUID] = Query(None),
    user: UserContext = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    query = """
        SELECT id, scope, scope_ref, version, title, system_prompt,
               created_by, created_at, is_active
        FROM agent_prompt_versions
        WHERE scope = $1 AND scope_ref IS NOT DISTINCT FROM $2 AND is_active = true
    """

    try:
        result = await db.fetchrow(query, scope, scope_ref)

        if not result:
            raise HTTPException(status_code=404, detail="No active prompt version found")

        return PromptVersionResponse(**dict(result))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching active prompt: {str(e)}")