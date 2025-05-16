from typing import List
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.building import Building
from app.db.models.floor_polygon import FloorPolygon
from app.db.models.access_point import AccessPoint
from app.schemas.map import MapResponse, FloorSchema
from app.exceptions import NotFoundError

logger = logging.getLogger(__name__)

# Явно объявляем публичный API модуля
__all__ = [
    "MapBuilder",
    "build_3d_map",
    "adjust_building_maps",
]

class MapBuilder:
    """
    Сервис для сборки модели карты здания:
    - build: формирует MapResponse по ID здания
    - adjust_building_maps: фоновые корректировки карты
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def build(self, building_id: int) -> MapResponse:
        # ... (ваша логика сборки карты) ...
        result = await self.db.execute(
            select(Building).where(Building.id == building_id)
        )
        building = result.scalars().first()
        if not building:
            raise NotFoundError(f"Building id={building_id} not found")

        # Получаем полигоны и AP, формируем FloorSchema…
        # Возвращаем MapResponse
        # (код опущен для краткости)
        return MapResponse(...)

    async def adjust_building_maps(self):
        # ... (ваша логика автокоррекции) ...
        logger.info("Автокорректировка карт зданий выполнена")

# ——— Публичные функции-обёртки ———

async def build_3d_map(db: AsyncSession) -> MapResponse:
    """
    Публичный вызов сборки карты без прямой работы с классом.
    """
    builder = MapBuilder(db)
    return await builder.build(db)

async def adjust_building_maps(db: AsyncSession) -> None:
    """
    Публичный вызов фоновой корректировки карт зданий.
    """
    builder = MapBuilder(db)
    return await builder.adjust_building_maps()