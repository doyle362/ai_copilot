from fastapi import APIRouter, Depends
from ..db import get_db, Database
from ..models.common import BaseResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/", response_model=BaseResponse)
async def health_check():
    return BaseResponse(message="Level Analyst API is running")


@router.get("/db", response_model=BaseResponse)
async def health_db(db: Database = Depends(get_db)):
    try:
        result = await db.fetchval("SELECT 1")
        if result == 1:
            return BaseResponse(message="Database connection healthy")
        else:
            return BaseResponse(success=False, message="Database connection failed")
    except Exception as e:
        return BaseResponse(success=False, message=f"Database error: {str(e)}")


@router.get("/ready", response_model=BaseResponse)
async def readiness_check(db: Database = Depends(get_db)):
    try:
        await db.fetchval("SELECT 1")
        return BaseResponse(message="Service ready")
    except Exception as e:
        return BaseResponse(success=False, message=f"Service not ready: {str(e)}")