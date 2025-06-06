from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db_session
from app.schemas.map import RouteResponse
from app.services import poi as poi_service
from app.services import map_builder

router = APIRouter(prefix="/v1/route", tags=["Route"])

@router.get("/", response_model=RouteResponse, summary="Построить маршрут между POI", description="Возвращает маршрут между двумя POI в здании.")
async def get_route(
    building_id: int,
    start_poi_id: int,
    end_poi_id: int,
    db: AsyncSession = Depends(get_db_session),
):
    # Получаем POI
    start_poi = await poi_service.get_poi(db, start_poi_id)
    end_poi = await poi_service.get_poi(db, end_poi_id)
    if not start_poi or not end_poi:
        raise HTTPException(status_code=404, detail="POI not found")
    # Здесь должна быть логика поиска маршрута (например, через map_builder)
    # Для примера: просто возвращаем start и end как маршрут
    route_points = [
        {"x": start_poi.x, "y": start_poi.y, "z": start_poi.z or 0, "floor": start_poi.floor},
        {"x": end_poi.x, "y": end_poi.y, "z": end_poi.z or 0, "floor": end_poi.floor},
    ]
    return RouteResponse(
        points=route_points,
        length=0.0,
        floor_from=start_poi.floor,
        floor_to=end_poi.floor,
        id=f"route_{start_poi_id}_{end_poi_id}"
    )
