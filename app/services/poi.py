from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models.poi import POI
from app.schemas.map import POICreate, POIUpdate
from sqlalchemy.exc import NoResultFound

async def get_poi(db: AsyncSession, poi_id: int) -> POI | None:
    result = await db.execute(select(POI).where(POI.id == poi_id))
    return result.scalars().first()

async def list_pois(db: AsyncSession, building_id: int | None = None, floor: int | None = None) -> list[POI]:
    stmt = select(POI)
    if building_id is not None:
        stmt = stmt.where(POI.building_id == building_id)
    if floor is not None:
        stmt = stmt.where(POI.floor == floor)
    result = await db.execute(stmt.order_by(POI.id))
    return result.scalars().all()

async def create_poi(db: AsyncSession, data: POICreate) -> POI:
    poi = POI(**data.dict())
    db.add(poi)
    await db.commit()
    await db.refresh(poi)
    return poi

async def update_poi(db: AsyncSession, poi_id: int, data: POIUpdate) -> POI:
    poi = await get_poi(db, poi_id)
    if not poi:
        raise NoResultFound(f"POI id={poi_id} not found")
    for k, v in data.dict(exclude_unset=True).items():
        setattr(poi, k, v)
    await db.commit()
    await db.refresh(poi)
    return poi

async def delete_poi(db: AsyncSession, poi_id: int) -> None:
    poi = await get_poi(db, poi_id)
    if not poi:
        raise NoResultFound(f"POI id={poi_id} not found")
    await db.delete(poi)
    await db.commit()
