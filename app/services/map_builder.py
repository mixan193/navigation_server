import logging
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.building import Building
from app.db.models.floor_polygon import FloorPolygon
from app.db.models.access_point import AccessPoint
from app.schemas.map import MapResponse, FloorSchema
from app.exceptions import NotFoundError

logger = logging.getLogger(__name__)


class MapBuilder:
    """
    Сервис для сборки модели карты здания:
    - Загружает здание по ID.
    - Считывает все полигоны этажей.
    - Для каждого этажа достаёт точки доступа.
    - Формирует и возвращает Pydantic-ответ MapResponse.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def build(self, building_id: int) -> MapResponse:
        # 1) Получаем здание
        result = await self.db.execute(
            select(Building).where(Building.id == building_id)
        )
        building = result.scalars().first()
        if not building:
            logger.error(f"Building id={building_id} not found")
            raise NotFoundError(f"Building with id={building_id} not found")

        # 2) Загружаем все полигоны этажей
        result = await self.db.execute(
            select(FloorPolygon)
            .where(FloorPolygon.building_id == building_id)
            .order_by(FloorPolygon.floor)
        )
        polygons = result.scalars().all()

        # 3) Для каждого этажа достаём точки доступа и формируем FloorSchema
        floors: List[FloorSchema] = []
        for poly in polygons:
            aps_result = await self.db.execute(
                select(AccessPoint)
                .where(
                    AccessPoint.building_id == building_id,
                    AccessPoint.floor == poly.floor
                )
                .order_by(AccessPoint.id)
            )
            aps = aps_result.scalars().all()

            floors.append(
                FloorSchema(
                    floor=poly.floor,
                    polygon=poly.polygon,
                    access_points=aps
                )
            )

        # 4) Собираем итоговый ответ
        response = MapResponse(
            building_id=building.id,
            building_name=building.name,
            address=building.address or "",
            floors=floors
        )
        logger.info(f"Built map for building id={building_id}: {len(floors)} floors")
        return response
