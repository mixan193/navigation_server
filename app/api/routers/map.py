from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.db.models.building import Building
from app.db.models.floor_polygon import FloorPolygon
from app.db.models.access_point import AccessPoint
from app.schemas.map import MapResponse, FloorSchema

router = APIRouter(
    prefix="/v1",
)


@router.get("/map/{building_id}", response_model=MapResponse)
async def get_building_map(
    building_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> MapResponse:
    """
    1) Ищем здание по ID, иначе 404.
    2) Загружаем все полигоны этажей из floor_polygons.
    3) Для каждого этажа достаём все точки доступа (access_points) по building_id и floor.
    4) Формируем список FloorSchema и возвращаем MapResponse.
    """
    # 1) Получаем здание
    result = await db.execute(
        select(Building).where(Building.id == building_id)
    )
    building = result.scalars().first()
    if not building:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Building with id={building_id} not found"
        )

    # 2) Получаем полигоны этажей, упорядоченные по номеру этажа
    result = await db.execute(
        select(FloorPolygon)
        .where(FloorPolygon.building_id == building_id)
        .order_by(FloorPolygon.floor)
    )
    polygons = result.scalars().all()

    floors: list[FloorSchema] = []
    for poly in polygons:
        # 3) Получаем все точки доступа на этом этаже
        aps_result = await db.execute(
            select(AccessPoint)
            .where(
                AccessPoint.building_id == building_id,
                AccessPoint.floor == poly.floor
            )
            .order_by(AccessPoint.id)
        )
        aps_on_floor = aps_result.scalars().all()

        # 4) Формируем FloorSchema
        floors.append(
            FloorSchema(
                floor=poly.floor,
                polygon=poly.polygon,
                access_points=aps_on_floor,
            )
        )

    # 5) Возвращаем готовый ответ
    return MapResponse(
        building_id=building.id,
        building_name=building.name,
        address=building.address or "",
        lat=building.lat,
        lon=building.lon,
        floors=floors,
    )