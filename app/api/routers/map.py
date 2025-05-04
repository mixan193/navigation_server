from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.db.models.building import Building
from app.schemas.map import MapResponse, FloorSchema

router = APIRouter()

@router.get("/{building_id}", response_model=MapResponse)
async def get_building_map(
    building_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> MapResponse:
    """
    Возвращает полную карту здания:
    - метаданные здания,
    - для каждого этажа: 3D-полигон + список AP.
    """
    # 1) Находим здание
    result = await db.execute(
        select(Building).where(Building.id == building_id)
    )
    building = result.scalars().first()
    if not building:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Building not found"
        )

    # 2) Формируем данные по этажам
    floors: list[FloorSchema] = []
    for poly in building.floor_polygons:
        # выбираем AP на этом этаже
        aps_on_floor = [
            ap for ap in building.access_points if ap.floor == poly.floor
        ]
        floors.append(
            FloorSchema(
                floor=poly.floor,
                polygon=poly.polygon,
                access_points=aps_on_floor,
            )
        )

    # 3) Возвращаем ответ
    return MapResponse(
        building_id=building.id,
        building_name=building.name,
        address=building.address or "",
        floors=floors,
    )