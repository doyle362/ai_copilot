from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel
from typing import List, Optional
import json
from ..config import settings
from ..db import get_db, Database


class UserContext(BaseModel):
    sub: str
    org_id: str
    roles: List[str]
    zone_ids: List[str]
    iss: str
    exp: int


security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserContext:
    token = credentials.credentials

    try:
        if settings.jwt_public_key_base64:
            # RS256 production mode
            raise NotImplementedError("RS256 JWT validation not implemented yet")
        else:
            # HS256 development mode
            payload = jwt.decode(
                token,
                settings.dev_jwt_hs256_secret,
                algorithms=["HS256"],
                issuer=settings.jwt_issuer
            )

        user_context = UserContext(
            sub=payload.get("sub", ""),
            org_id=payload.get("org_id", ""),
            roles=payload.get("roles", []),
            zone_ids=payload.get("zone_ids", []),
            iss=payload.get("iss", ""),
            exp=payload.get("exp", 0)
        )

        # Note: JWT claims for RLS would be set here in production mode with database

        return user_context

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_zone_access(zone_id: str):
    def _check_zone_access(user: UserContext = Depends(get_current_user)):
        if zone_id not in user.zone_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to zone {zone_id}"
            )
        return user
    return _check_zone_access


def require_role(required_role: str):
    def _check_role(user: UserContext = Depends(get_current_user)):
        if required_role not in user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {required_role} required"
            )
        return user
    return _check_role