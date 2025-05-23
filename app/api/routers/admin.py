from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db_session
from app.services.geo_solver import update_access_point_positions
from app.services.security import get_current_active_user
from app.db.models.user import User

router = APIRouter(prefix="/v1/admin", tags=["admin"])

@router.post("/recalculate-aps", status_code=status.HTTP_202_ACCEPTED)
async def recalculate_all_aps(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user),
):
    if not getattr(current_user, "is_superuser", False):
        raise HTTPException(status_code=403, detail="Требуются права администратора")
    await update_access_point_positions(db)
    return {"detail": "Массовый пересчёт координат AP запущен"}
