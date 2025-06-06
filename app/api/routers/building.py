from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_db_session
from app.db.models.building import Building
from typing import List
from pydantic import BaseModel

class BuildingOut(BaseModel):
    id: int
    name: str
    address: str | None = None
    lat: float | None = None
    lon: float | None = None

    class Config:
        orm_mode = True

router = APIRouter(prefix="/v1/buildings", tags=["Building"])

@router.get("/", response_model=List[BuildingOut], summary="Получить список зданий", description="Возвращает список всех зданий с координатами центра.")
async def list_buildings(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(Building))
    buildings = result.scalars().all()
    return buildings
