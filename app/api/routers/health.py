# app/api/routers/health.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.api.deps import get_db_session

router = APIRouter()

@router.get("/", summary="Health check")
async def health_check(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(text("SELECT 1"))
    return {"db_ok": bool(result.scalar())}
