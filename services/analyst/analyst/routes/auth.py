"""Authentication and token management routes."""

import jwt
import time
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional

from ..config import settings
from ..db import get_db

router = APIRouter(prefix="/auth", tags=["authentication"])

class TokenRequest(BaseModel):
    user_id: Optional[str] = "dev-user-001"
    org_id: Optional[str] = "org-demo"
    roles: Optional[List[str]] = ["admin", "analyst"]
    hours_valid: Optional[int] = 24

class TokenResponse(BaseModel):
    token: str
    expires_at: str
    zone_access: List[str]
    zones_with_data: int

@router.post("/generate-token", response_model=TokenResponse)
async def generate_dev_token(
    request: TokenRequest = TokenRequest(),
    db = Depends(get_db)
):
    """Generate a fresh JWT token with access to all zones that have transaction data."""


    try:
        # Get all zones with transaction data
        zones_query = """
        SELECT DISTINCT zone, COUNT(*) as transaction_count
        FROM historical_transactions
        WHERE zone IS NOT NULL
        GROUP BY zone
        HAVING COUNT(*) >= 3
        ORDER BY transaction_count DESC
        """

        zones_result = await db.fetch(zones_query)
        zone_ids = [str(row["zone"]) for row in zones_result]

        # Create JWT payload
        exp_time = int(time.time()) + (request.hours_valid * 60 * 60)
        payload = {
            "sub": request.user_id,
            "org_id": request.org_id,
            "roles": request.roles,
            "zone_ids": zone_ids,
            "iss": settings.jwt_issuer,
            "iat": int(time.time()),
            "exp": exp_time
        }

        # Generate token
        token = jwt.encode(payload, settings.dev_jwt_hs256_secret, algorithm="HS256")

        return TokenResponse(
            token=token,
            expires_at=datetime.fromtimestamp(exp_time).isoformat(),
            zone_access=zone_ids,
            zones_with_data=len(zone_ids)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token generation failed: {str(e)}")

@router.get("/zones-with-data")
async def get_zones_with_data(db = Depends(get_db)):
    """Get all zones that have transaction data."""

    try:
        zones_query = """
        SELECT DISTINCT zone, COUNT(*) as transaction_count
        FROM historical_transactions
        WHERE zone IS NOT NULL
        GROUP BY zone
        ORDER BY transaction_count DESC
        """

        zones_result = await db.fetch(zones_query)

        return {
            "zones": [
                {
                    "zone_id": row["zone"],
                    "transaction_count": row["transaction_count"]
                }
                for row in zones_result
            ],
            "total_zones": len(zones_result)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch zones: {str(e)}")