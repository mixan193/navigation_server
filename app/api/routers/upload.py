import math
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import ValidationError

from app.db.models import access_point as ap_model
from app.db.models import wifi_snapshot as ws_model
from app.db.models import wifi_obs as wo_model
from app.db.models import building as building_model
from app.schemas.scan import ScanUpload
from app.db.session import get_db
from app.services import geo_solver
from app.utils.geo_utils import reverse_geocode_osm

router = APIRouter(
    prefix="/v1",
)

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_scan(
    scan: ScanUpload,
    db: AsyncSession = Depends(get_db)
):
    import logging
    logger = logging.getLogger("upload_debug")
    logger.warning(f"RAW SCAN: x={scan.x}, y={scan.y}, lat={scan.lat}, lon={scan.lon}, building_id={scan.building_id}")
    # --- ОТЛАДКА: печать всего scan ---
    logger.warning(f"RAW SCAN FULL: {scan.dict()}")
    # 1. Проверка/создание здания (как раньше)
    result = await db.execute(
        select(building_model.Building).where(building_model.Building.id == scan.building_id)
    )
    building = result.scalars().first()
    if not building and scan.lat is not None and scan.lon is not None:
        osm = await reverse_geocode_osm(scan.lat, scan.lon)
        osm_id = osm.get("osm_id")
        address = osm.get("display_name", "Unknown address")
        name = osm.get("name") or osm.get("address", {}).get("building") or f"Unknown building {osm_id or ''}"  # <--- fix: make name unique
        building = None
        if osm_id is not None:
            result = await db.execute(
                select(building_model.Building).where(building_model.Building.osm_id == osm_id)
            )
            building = result.scalars().first()
        if not building:
            # fix: check for existing building with same name
            result = await db.execute(
                select(building_model.Building).where(building_model.Building.name == name)
            )
            building = result.scalars().first()
        if not building:
            building = building_model.Building(
                name=name,
                address=address,
                osm_id=osm_id,
                lat=scan.lat,
                lon=scan.lon
            )
            db.add(building)
            await db.flush()
    if not building:
        raise HTTPException(status_code=404, detail="Здание не найдено и не может быть определено по координатам")
    scan.building_id = building.id

    # --- Новое: вычисляем локальные x, y из lat/lon если x и y не заданы ---
    if scan.x is None or scan.y is None:
        if scan.lat is not None and scan.lon is not None and building.lat is not None and building.lon is not None:
            # перевод широта/долгота в локальные метры
            scan.x = (scan.lon - building.lon) * math.cos(math.radians(building.lat)) * 111320
            scan.y = (scan.lat - building.lat) * 110574
            logger.warning(f"CALC XY: building.lat={building.lat}, building.lon={building.lon}, scan.lat={scan.lat}, scan.lon={scan.lon}, x={scan.x}, y={scan.y}")
        else:
            logger.warning(f"NO XY: building.lat={building.lat}, building.lon={building.lon}, scan.lat={scan.lat}, scan.lon={scan.lon}")
    else:
        logger.warning(f"CLIENT XY: x={scan.x}, y={scan.y}")

    # 2. Создаём WiFiSnapshot (x, y уже могут быть вычислены)
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

    # 3. Для каждого WiFi-наблюдения:
    for obs in scan.observations:
        result = await db.execute(
            select(ap_model.AccessPoint).where(ap_model.AccessPoint.bssid == obs.bssid)
        )
        ap_obj = result.scalars().first()
        # --- Гарантируем вычисление x/y для AP, если есть lat/lon и координаты здания ---
        # Используем lat/lon из scan, snapshot, либо из последнего wifi_obs (если есть)
        ap_x, ap_y, ap_z = scan.x, scan.y, scan.z
        lat = scan.lat if scan.lat is not None else snapshot.lat
        lon = scan.lon if scan.lon is not None else snapshot.lon
        # Если всё ещё нет lat/lon, пробуем взять из последнего wifi_obs (если есть)
        if (lat is None or lon is None):
            last_obs = await db.execute(
                select(ws_model.WiFiSnapshot).order_by(ws_model.WiFiSnapshot.id.desc())
            )
            last_snap = last_obs.scalars().first()
            if last_snap is not None:
                lat = last_snap.lat
                lon = last_snap.lon
        if (ap_x is None or ap_y is None) and lat is not None and lon is not None and building.lat is not None and building.lon is not None:
            ap_x = (lon - building.lon) * math.cos(math.radians(building.lat)) * 111320
            ap_y = (lat - building.lat) * 110574
            logger.warning(f"AP CALC XY: building.lat={building.lat}, building.lon={building.lon}, lat={lat}, lon={lon}, x={ap_x}, y={ap_y}")
        if not ap_obj:
            if ap_x is None or ap_y is None or (ap_x == 0 and ap_y == 0):
                logger.warning(f"SKIP AP CREATE: bssid={obs.bssid}, x={ap_x}, y={ap_y}, lat={lat}, lon={lon}, building.lat={building.lat}, building.lon={building.lon}")
                continue
            ap_obj = ap_model.AccessPoint(
                bssid=obs.bssid,
                ssid=obs.ssid,
                building_id=scan.building_id,
                floor=scan.floor,
                x=ap_x,
                y=ap_y,
                z=ap_z,
                accuracy=9999.0,
                is_mobile=False
            )
            db.add(ap_obj)
            await db.flush()
        else:
            # Если AP была в другом здании — помечаем мобильной только если здания далеко друг от друга
            if ap_obj.building_id != scan.building_id:
                # Получаем координаты обоих зданий
                b1 = await db.execute(select(building_model.Building).where(building_model.Building.id == ap_obj.building_id))
                b2 = await db.execute(select(building_model.Building).where(building_model.Building.id == scan.building_id))
                b1 = b1.scalars().first()
                b2 = b2.scalars().first()
                if b1 and b2 and b1.lat is not None and b1.lon is not None and b2.lat is not None and b2.lon is not None:
                    # Вычисляем расстояние между зданиями (в метрах)
                    from math import radians, cos, sin, sqrt, atan2
                    R = 6371000  # радиус Земли в метрах
                    dlat = radians(b2.lat - b1.lat)
                    dlon = radians(b2.lon - b1.lon)
                    a = sin(dlat/2)**2 + cos(radians(b1.lat)) * cos(radians(b2.lat)) * sin(dlon/2)**2
                    c = 2 * atan2(sqrt(a), sqrt(1-a))
                    distance = R * c
                    if distance > 500:
                        ap_obj.is_mobile = True
                        logger.warning(f"AP {ap_obj.bssid} помечена как мобильная: здания {ap_obj.building_id} и {scan.building_id} на расстоянии {distance:.1f} м")
                else:
                    # Если координаты зданий неизвестны, по-прежнему помечаем мобильной
                    ap_obj.is_mobile = True
        # Создаём наблюдение
        wifi_obs = wo_model.WiFiObs(
            snapshot_id=snapshot.id,
            access_point_id=ap_obj.id,
            ssid=obs.ssid,
            bssid=obs.bssid,
            rssi=obs.rssi,
            frequency=obs.frequency
        )
        db.add(wifi_obs)
    await db.flush()

    # 4. После добавления всех наблюдений уточняем координаты AP
    bssid_set = {obs.bssid for obs in scan.observations}
    for bssid in bssid_set:
        await geo_solver.recalculate_access_point_coords(bssid, db)
    try:
        await db.commit()
    except ValidationError as ve:
        await db.rollback()
        raise HTTPException(status_code=422, detail=f"Ошибка валидации: {ve.errors()}")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения WiFi скана: {str(e)}")

    # Формируем ответ (как раньше)
    user_coords = {'building_id': snapshot.building_id, 'floor': snapshot.floor}
    if snapshot.x is not None and snapshot.y is not None:
        user_coords.update({'x': snapshot.x, 'y': snapshot.y, 'z': snapshot.z})
    elif snapshot.lat is not None and snapshot.lon is not None:
        user_coords.update({'lat': snapshot.lat, 'lon': snapshot.lon, 'altitude': snapshot.z, 'accuracy': snapshot.accuracy})
    computed_coords = None
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
