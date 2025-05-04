from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.db.models.access_point import AccessPoint
from app.schemas.ap import AccessPointOut

router = APIRouter()

@router.get("/{bssid}", response_model=AccessPointOut)
async def get_access_point(
    bssid: str,
    db: AsyncSession = Depends(get_db_session),
) -> AccessPointOut:
    """
    Возвращает информацию о точке доступа по BSSID (MAC-адресу).
    """
    result = await db.execute(
        select(AccessPoint).where(AccessPoint.bssid == bssid)
    )
    ap = result.scalars().first()
    if not ap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Access point not found"
        )
    return ap