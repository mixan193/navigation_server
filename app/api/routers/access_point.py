from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db_session
from app.schemas.ap import AccessPointCreate, AccessPointUpdate, AccessPointAdminOut, AccessPointListResponse
from app.services import access_point as ap_service
from typing import List

router = APIRouter(prefix="/v1/access-points", tags=["AccessPoint"])

@router.get(
    "/",
    response_model=AccessPointListResponse,
    summary="Получить список точек доступа",
    description="Возвращает список всех точек доступа. Можно фильтровать по building_id, floor, bssid, ssid, is_mobile, accuracy_min/max. Поддерживается пагинация и сортировка.",
    examples={
        "filter_by_bssid": {
            "summary": "Фильтрация по BSSID",
            "description": "Получить только одну точку доступа по BSSID.",
            "value": {"bssid": "AA:BB:CC:DD:EE:FF"}
        },
        "filter_mobile": {
            "summary": "Только мобильные точки",
            "description": "Получить только мобильные точки доступа.",
            "value": {"is_mobile": True}
        },
        "filter_accuracy": {
            "summary": "По диапазону точности",
            "description": "Получить точки с точностью от 0 до 10 метров.",
            "value": {"accuracy_min": 0, "accuracy_max": 10}
        }
    }
)
async def list_access_points(
    building_id: int | None = None,
    floor: int | None = None,
    bssid: str | None = Query(None, description="Фильтр по BSSID"),
    ssid: str | None = Query(None, description="Фильтр по SSID"),
    is_mobile: bool | None = Query(None, description="Фильтр по мобильности AP"),
    accuracy_min: float | None = Query(None, description="Минимальная точность (accuracy >=)", ge=0),
    accuracy_max: float | None = Query(None, description="Максимальная точность (accuracy <=)", ge=0),
    limit: int = Query(100, ge=1, le=1000, description="Максимум записей на страницу (пагинация)"),
    offset: int = Query(0, ge=0, description="Смещение для пагинации"),
    order_by: str = Query("id", description="Поле сортировки: id, bssid, accuracy, created_at, last_update"),
    order_dir: str = Query("asc", description="Направление сортировки: asc или desc"),
    db: AsyncSession = Depends(get_db_session)
):
    """Список всех точек доступа (расширенная фильтрация, пагинация и сортировка)"""
    items, total = await ap_service.list_access_points(db, building_id, floor, bssid, ssid, is_mobile, accuracy_min, accuracy_max, limit, offset, order_by, order_dir)
    return AccessPointListResponse(items=items, total=total, limit=limit, offset=offset)

@router.get(
    "/{ap_id}",
    response_model=AccessPointAdminOut,
    summary="Получить точку доступа по ID",
    description="Возвращает одну точку доступа по её уникальному идентификатору."
)
async def get_access_point(
    ap_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    ap = await ap_service.get_access_point(db, ap_id)
    if not ap:
        raise HTTPException(status_code=404, detail="AccessPoint not found")
    return ap

@router.post(
    "/",
    response_model=AccessPointAdminOut,
    status_code=201,
    summary="Создать новую точку доступа",
    description="Создаёт новую точку доступа (AP) вручную. BSSID должен быть уникальным.",
    responses={
        409: {"description": "AccessPoint with this BSSID already exists"}
    }
)
async def create_access_point(
    data: AccessPointCreate,
    db: AsyncSession = Depends(get_db_session)
):
    try:
        ap = await ap_service.create_access_point(db, data)
        return ap
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.put(
    "/{ap_id}",
    response_model=AccessPointAdminOut,
    summary="Обновить точку доступа",
    description="Обновляет параметры точки доступа по её ID. BSSID должен быть уникальным.",
    responses={
        409: {"description": "AccessPoint with this BSSID already exists"}
    }
)
async def update_access_point(
    ap_id: int,
    data: AccessPointUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    try:
        ap = await ap_service.update_access_point(db, ap_id, data)
        return ap
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except NoResultFound:
        raise HTTPException(status_code=404, detail="AccessPoint not found")

@router.delete(
    "/{ap_id}",
    status_code=204,
    summary="Удалить точку доступа",
    description="Удаляет точку доступа по её ID. Если такой точки не существует, возвращает 404."
)
async def delete_access_point(
    ap_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    try:
        await ap_service.delete_access_point(db, ap_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="AccessPoint not found")
