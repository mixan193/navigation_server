from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.schemas.scan import ScanUpload, ScanResponse
from app.db.models.wifi_snapshot import WiFiSnapshot
from app.db.models.wifi_obs import WiFiObs
from app.db.models.access_point import AccessPoint

router = APIRouter()

@router.post("/", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
async def upload_scan(
    scan: ScanUpload,
    db: AsyncSession = Depends(get_db_session),
) -> ScanResponse:
    """
    Принимает скан Wi-Fi в формате ScanUpload,
    сохраняет WiFiSnapshot + WiFiObs и возвращает ID снимка.
    """
    # 1) Создаём запись snapshot с ориентацией
    snapshot = WiFiSnapshot(
        building_id=scan.building_id,
        floor=scan.floor,
        yaw=scan.yaw,
        pitch=scan.pitch,
        roll=scan.roll,
    )
    db.add(snapshot)
    await db.flush()  # Получаем snapshot.id без коммита

    # 2) Обрабатываем каждое наблюдение
    for obs in scan.observations:
        # Пытаемся найти существующий AP по BSSID
        result = await db.execute(
            select(AccessPoint).where(AccessPoint.bssid == obs.bssid)
        )
        ap_obj = result.scalars().first()
        ap_id = ap_obj.id if ap_obj else None

        wifi_obs = WiFiObs(
            snapshot_id=snapshot.id,
            access_point_id=ap_id,
            ssid=obs.ssid,
            bssid=obs.bssid,
            rssi=obs.rssi,
            frequency=obs.frequency,
        )
        db.add(wifi_obs)

    # 3) Фиксируем транзакцию
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error saving WiFi scan"
        ) from e

    return ScanResponse(snapshot_id=snapshot.id)