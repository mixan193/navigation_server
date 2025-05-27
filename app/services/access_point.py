from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.models.access_point import AccessPoint
from app.schemas.ap import AccessPointCreate, AccessPointUpdate
from sqlalchemy.exc import NoResultFound, IntegrityError

async def get_access_point(db: AsyncSession, ap_id: int) -> AccessPoint | None:
    result = await db.execute(select(AccessPoint).where(AccessPoint.id == ap_id))
    return result.scalars().first()

async def list_access_points(
    db: AsyncSession,
    building_id: int | None = None,
    floor: int | None = None,
    bssid: str | None = None,
    ssid: str | None = None,
    is_mobile: bool | None = None,
    accuracy_min: float | None = None,
    accuracy_max: float | None = None,
    limit: int = 100,
    offset: int = 0,
    order_by: str = "id",
    order_dir: str = "asc"
) -> tuple[list[AccessPoint], int]:
    stmt = select(AccessPoint)
    if building_id is not None:
        stmt = stmt.where(AccessPoint.building_id == building_id)
    if floor is not None:
        stmt = stmt.where(AccessPoint.floor == floor)
    if bssid is not None:
        stmt = stmt.where(AccessPoint.bssid == bssid)
    if ssid is not None:
        stmt = stmt.where(AccessPoint.ssid == ssid)
    if is_mobile is not None:
        stmt = stmt.where(AccessPoint.is_mobile == is_mobile)
    if accuracy_min is not None:
        stmt = stmt.where(AccessPoint.accuracy >= accuracy_min)
    if accuracy_max is not None:
        stmt = stmt.where(AccessPoint.accuracy <= accuracy_max)
    # Сортировка
    order_fields = {
        "id": AccessPoint.id,
        "bssid": AccessPoint.bssid,
        "accuracy": AccessPoint.accuracy,
        "created_at": AccessPoint.created_at,
        "last_update": AccessPoint.last_update
    }
    order_col = order_fields.get(order_by, AccessPoint.id)
    if order_dir == "desc":
        order_col = order_col.desc()
    else:
        order_col = order_col.asc()
    stmt = stmt.order_by(order_col).limit(limit).offset(offset)
    result = await db.execute(stmt)
    items = result.scalars().all()
    # Total count
    count_query = select(func.count()).select_from(AccessPoint)
    if building_id is not None:
        count_query = count_query.where(AccessPoint.building_id == building_id)
    if floor is not None:
        count_query = count_query.where(AccessPoint.floor == floor)
    if bssid is not None:
        count_query = count_query.where(AccessPoint.bssid == bssid)
    if ssid is not None:
        count_query = count_query.where(AccessPoint.ssid == ssid)
    if is_mobile is not None:
        count_query = count_query.where(AccessPoint.is_mobile == is_mobile)
    if accuracy_min is not None:
        count_query = count_query.where(AccessPoint.accuracy >= accuracy_min)
    if accuracy_max is not None:
        count_query = count_query.where(AccessPoint.accuracy <= accuracy_max)
    total = (await db.execute(count_query)).scalar_one()

    # Преобразование к Pydantic-схеме (гарантировано красиво и надёжно)
    from app.schemas.ap import AccessPointAdminOut
    items_out = [AccessPointAdminOut.model_validate(item, from_attributes=True) for item in items]
    return items_out, total

async def create_access_point(db: AsyncSession, data: AccessPointCreate) -> AccessPoint:
    ap = AccessPoint(**data.dict())
    db.add(ap)
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        if "unique constraint" in str(e).lower() or "bssid" in str(e).lower():
            raise ValueError("AccessPoint with this BSSID already exists")
        raise
    await db.refresh(ap)
    return ap

async def update_access_point(db: AsyncSession, ap_id: int, data: AccessPointUpdate) -> AccessPoint:
    ap = await get_access_point(db, ap_id)
    if not ap:
        raise NoResultFound(f"AccessPoint id={ap_id} not found")
    # Проверка уникальности BSSID при изменении
    if data.bssid is not None and data.bssid != ap.bssid:
        exists = await db.execute(select(AccessPoint).where(AccessPoint.bssid == data.bssid))
        if exists.scalars().first():
            raise ValueError("AccessPoint with this BSSID already exists")
    for k, v in data.dict(exclude_unset=True).items():
        setattr(ap, k, v)
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        if "unique constraint" in str(e).lower() or "bssid" in str(e).lower():
            raise ValueError("AccessPoint with this BSSID already exists")
        raise
    await db.refresh(ap)
    return ap

async def delete_access_point(db: AsyncSession, ap_id: int) -> None:
    ap = await get_access_point(db, ap_id)
    if not ap:
        raise NoResultFound(f"AccessPoint id={ap_id} not found")
    await db.delete(ap)
    await db.commit()
