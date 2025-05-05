from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.models import access_point as ap_model
from app.db.models import wifi_snapshot as ws_model
from app.db.models import wifi_obs as wo_model
from app.db.models import building as building_model
from app.schemas.scan import ScanUpload
from app.db.session import get_db
from app.services.security import get_current_user
from app.db.models.user import User

router = APIRouter(
    prefix="/v1",
    tags=["upload"]
)


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_scan(
    scan: ScanUpload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Проверяем существование здания
    result = await db.execute(
        select(building_model.Building).where(building_model.Building.id == scan.building_id)
    )
    building = result.scalars().first()
    if not building:
        raise HTTPException(status_code=404, detail="Здание не найдено")

    # Создаём WiFiSnapshot с координатами и ориентацией
    snapshot = ws_model.WiFiSnapshot(
        building_id=scan.building_id,
        floor=scan.floor,
        x=scan.x,
        y=scan.y,
        z=scan.z,
        yaw=scan.yaw,
        pitch=scan.pitch,
        roll=scan.roll,
        user_id=current_user.id
    )
    db.add(snapshot)
    await db.flush()

    for obs in scan.observations:
        # Ищем точку доступа по BSSID
        result = await db.execute(
            select(ap_model.AccessPoint).where(ap_model.AccessPoint.bssid == obs.bssid)
        )
        ap_obj = result.scalars().first()

        if not ap_obj:
            ap_obj = ap_model.AccessPoint(
                bssid=obs.bssid,
                ssid=obs.ssid,
                building_id=scan.building_id,
                floor=scan.floor,
                x=None,
                y=None,
                z=None
            )
            db.add(ap_obj)
            await db.flush()

        wifi_obs = wo_model.WiFiObs(
            snapshot_id=snapshot.id,
            access_point_id=ap_obj.id,
            ssid=obs.ssid,
            bssid=obs.bssid,
            rssi=obs.rssi,
            frequency=obs.frequency
        )
        db.add(wifi_obs)

    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения WiFi скана: {str(e)}")

    return {"message": "Скан успешно загружен"}
