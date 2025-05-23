from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db_session
from app.schemas.map import POICreate, POIUpdate, POIOut
from app.services import poi as poi_service
from typing import List

router = APIRouter(prefix="/v1/pois", tags=["POI"])

@router.get(
    "/",
    response_model=List[POIOut],
    summary="Получить список POI (точек интереса)",
    description="Возвращает список всех POI (точек интереса, входы, выходы и др.). Можно фильтровать по building_id и floor."
)
async def list_pois(
    building_id: int | None = None,
    floor: int | None = None,
    db: AsyncSession = Depends(get_db_session)
):
    """Список всех POI (фильтр по зданию и этажу)"""
    pois = await poi_service.list_pois(db, building_id, floor)
    return pois

@router.get(
    "/{poi_id}",
    response_model=POIOut,
    summary="Получить POI по ID",
    description="Возвращает одну точку интереса (POI) по её уникальному идентификатору."
)
async def get_poi(
    poi_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    poi = await poi_service.get_poi(db, poi_id)
    if not poi:
        raise HTTPException(status_code=404, detail="POI not found")
    return poi

@router.post(
    "/",
    response_model=POIOut,
    status_code=201,
    summary="Создать новую точку интереса (POI)",
    description="Создаёт новую точку интереса (POI) вручную."
)
async def create_poi(
    data: POICreate,
    db: AsyncSession = Depends(get_db_session)
):
    poi = await poi_service.create_poi(db, data)
    return poi

@router.put(
    "/{poi_id}",
    response_model=POIOut,
    summary="Обновить POI",
    description="Обновляет параметры точки интереса по её ID."
)
async def update_poi(
    poi_id: int,
    data: POIUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    try:
        poi = await poi_service.update_poi(db, poi_id, data)
        return poi
    except NoResultFound:
        raise HTTPException(status_code=404, detail="POI not found")

@router.delete(
    "/{poi_id}",
    status_code=204,
    summary="Удалить POI",
    description="Удаляет точку интереса по её ID."
)
async def delete_poi(
    poi_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    try:
        await poi_service.delete_poi(db, poi_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="POI not found")
