from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db_session
from app.schemas.map import FloorPolygonCreate, FloorPolygonUpdate, FloorPolygonOut
from app.services import floor_polygon as fp_service
from typing import List

router = APIRouter(prefix="/v1/floor-polygons", tags=["FloorPolygon"])

@router.get(
    "/",
    response_model=List[FloorPolygonOut],
    summary="Получить список полигонов этажей",
    description="Возвращает список всех полигонов этажей. Можно фильтровать по building_id."
)
async def list_floor_polygons(
    building_id: int | None = None,
    db: AsyncSession = Depends(get_db_session)
):
    """Список всех полигонов этажей (опционально по building_id)"""
    polygons = await fp_service.list_floor_polygons(db, building_id)
    return polygons

@router.get(
    "/{polygon_id}",
    response_model=FloorPolygonOut,
    summary="Получить полигон этажа по ID",
    description="Возвращает один полигон этажа по его уникальному идентификатору."
)
async def get_floor_polygon(
    polygon_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    polygon = await fp_service.get_floor_polygon(db, polygon_id)
    if not polygon:
        raise HTTPException(status_code=404, detail="FloorPolygon not found")
    return polygon

@router.post(
    "/",
    response_model=FloorPolygonOut,
    status_code=201,
    summary="Создать новый полигон этажа",
    description="Создаёт новый полигон этажа (стены/проходы) для здания."
)
async def create_floor_polygon(
    data: FloorPolygonCreate,
    db: AsyncSession = Depends(get_db_session)
):
    polygon = await fp_service.create_floor_polygon(db, data)
    return polygon

@router.put(
    "/{polygon_id}",
    response_model=FloorPolygonOut,
    summary="Обновить полигон этажа",
    description="Обновляет координаты полигона этажа по его ID."
)
async def update_floor_polygon(
    polygon_id: int,
    data: FloorPolygonUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    try:
        polygon = await fp_service.update_floor_polygon(db, polygon_id, data)
        return polygon
    except NoResultFound:
        raise HTTPException(status_code=404, detail="FloorPolygon not found")

@router.delete(
    "/{polygon_id}",
    status_code=204,
    summary="Удалить полигон этажа",
    description="Удаляет полигон этажа по его ID."
)
async def delete_floor_polygon(
    polygon_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    try:
        await fp_service.delete_floor_polygon(db, polygon_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="FloorPolygon not found")
