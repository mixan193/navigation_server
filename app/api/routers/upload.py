import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.models import access_point as ap_model
from app.db.models import wifi_snapshot as ws_model
from app.db.models import wifi_obs as wo_model
from app.db.models import building as building_model
from app.schemas.scan import ScanUpload
from app.db.session import get_db
from app.services import geo_solver

router = APIRouter(
    # prefix="/v1",
    tags=["upload"]
)

@router.post("/", status_code=status.HTTP_201_CREATED)
async def upload_scan(
    scan: ScanUpload,
    db: AsyncSession = Depends(get_db)
):
    # Проверяем существование здания по ID
    result = await db.execute(
        select(building_model.Building).where(building_model.Building.id == scan.building_id)
    )
    building = result.scalars().first()
    if not building:
        raise HTTPException(status_code=404, detail="Здание не найдено")

    # Создаём WiFiSnapshot с координатами и ориентацией (если есть)
    snapshot = ws_model.WiFiSnapshot(
        building_id=scan.building_id,
        floor=scan.floor,
        x=scan.x,
        y=scan.y,
        z=scan.z,
        yaw=scan.yaw,
        pitch=scan.pitch,
        roll=scan.roll,
        user_id=None,
        lat=scan.lat,
        lon=scan.lon,
        accuracy=scan.accuracy
    )
    db.add(snapshot)
    await db.flush()

    # Обрабатываем каждое WiFi-наблюдение (точку доступа)
    for obs in scan.observations:
        # Ищем точку доступа по BSSID
        result = await db.execute(
            select(ap_model.AccessPoint).where(ap_model.AccessPoint.bssid == obs.bssid)
        )
        ap_obj = result.scalars().first()

        if not ap_obj:
            # Создаем новую точку доступа
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
        else:
            # Помечаем AP как мобильную, если она уже была в другом здании
            if ap_obj.building_id != scan.building_id:
                ap_obj.is_mobile = True

        # Сохраняем наблюдение WiFi, привязанное к snapshot и AP
        wifi_obs = wo_model.WiFiObs(
            snapshot_id=snapshot.id,
            access_point_id=ap_obj.id,
            ssid=obs.ssid,
            bssid=obs.bssid,
            rssi=obs.rssi,
            frequency=obs.frequency
        )
        db.add(wifi_obs)

    # Сохраняем все добавленные объекты в базе
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения WiFi скана: {str(e)}")

    # Формируем ответ с рассчитанными координатами пользователя
    user_coords = {'building_id': snapshot.building_id, 'floor': snapshot.floor}
    if snapshot.x is not None and snapshot.y is not None:
        user_coords.update({'x': snapshot.x, 'y': snapshot.y, 'z': snapshot.z})
    elif snapshot.lat is not None and snapshot.lon is not None:
        user_coords.update({'lat': snapshot.lat, 'lon': snapshot.lon, 'altitude': snapshot.z, 'accuracy': snapshot.accuracy})

    computed_coords = None
    # Попробуем вычислить координаты пользователя по сигналам Wi-Fi
    try:
        positions = []
        distances = []
        result_ap = await db.execute(
            select(ap_model.AccessPoint).where(ap_model.AccessPoint.bssid.in_([obs.bssid for obs in scan.observations]))
        )
        ap_list = result_ap.scalars().all()
        for ap in ap_list:
            if ap.is_mobile or ap.x is None or ap.y is None or ap.z is None:
                continue
            for obs in scan.observations:
                if obs.bssid == ap.bssid:
                    distances.append(geo_solver.rssi_to_distance(obs.rssi))
                    positions.append((ap.x, ap.y, ap.z))
                    break
        if len(positions) >= 4:
            x_u, y_u, z_u = geo_solver.trilaterate_3d(positions, distances)
            computed_coords = {'x': float(x_u), 'y': float(y_u), 'z': float(z_u)}
    except Exception as e:
        logging.getLogger(__name__).warning(f'Не удалось вычислить координаты по Wi-Fi: {e}')
    if computed_coords:
        user_coords.update(computed_coords)

    return {'status': 'success', 'coordinates': user_coords}
