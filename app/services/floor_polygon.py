from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from app.db.models.floor_polygon import FloorPolygon
from app.schemas.map import FloorPolygonCreate, FloorPolygonUpdate
from sqlalchemy.exc import NoResultFound

async def get_floor_polygon(db: AsyncSession, polygon_id: int) -> FloorPolygon | None:
    result = await db.execute(select(FloorPolygon).where(FloorPolygon.id == polygon_id))
    return result.scalars().first()

async def list_floor_polygons(db: AsyncSession, building_id: int | None = None) -> list[FloorPolygon]:
    stmt = select(FloorPolygon)
    if building_id is not None:
        stmt = stmt.where(FloorPolygon.building_id == building_id)
    result = await db.execute(stmt.order_by(FloorPolygon.floor))
    return result.scalars().all()

async def create_floor_polygon(db: AsyncSession, data: FloorPolygonCreate) -> FloorPolygon:
    polygon = FloorPolygon(**data.dict())
    db.add(polygon)
    await db.commit()
    await db.refresh(polygon)
    return polygon

async def update_floor_polygon(db: AsyncSession, polygon_id: int, data: FloorPolygonUpdate) -> FloorPolygon:
    polygon = await get_floor_polygon(db, polygon_id)
    if not polygon:
        raise NoResultFound(f"FloorPolygon id={polygon_id} not found")
    for k, v in data.dict(exclude_unset=True).items():
        setattr(polygon, k, v)
    await db.commit()
    await db.refresh(polygon)
    return polygon

async def delete_floor_polygon(db: AsyncSession, polygon_id: int) -> None:
    polygon = await get_floor_polygon(db, polygon_id)
    if not polygon:
        raise NoResultFound(f"FloorPolygon id={polygon_id} not found")
    await db.delete(polygon)
    await db.commit()
