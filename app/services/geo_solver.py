import math
import logging
from sqlalchemy import select, update, inspect as sqlalchemy_inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload, contains_eager # Modified import
import sqlalchemy.exc
import sqlalchemy.orm.attributes # Added import

from app.db.models.access_point import AccessPoint
from app.db.models.wifi_obs import WiFiObs
from app.db.models.wifi_snapshot import WiFiSnapshot

logger = logging.getLogger(__name__)

DEFAULT_TX_POWER_DBM = -50
DEFAULT_PATH_LOSS_EXPONENT = 2.0

def rssi_to_distance(rssi: float, tx_power: float = DEFAULT_TX_POWER_DBM, n: float = DEFAULT_PATH_LOSS_EXPONENT) -> float:
    """
    Преобразует RSSI в оценку расстояния (метры) по log-distance path loss model.
    """
    try:
        return 10 ** ((tx_power - rssi) / (10 * n))
    except Exception as e:
        logger.error(f"Ошибка при вычислении расстояния по RSSI: {e}")
        return float("inf")

def trilaterate_3d(positions, distances):
    """
    Решение системы для 3D триангуляции по формулам Найдена-Хьюза (простая модель)
    positions: [(x, y, z), ...]
    distances: [d1, d2, d3, ...]
    Требуется >= 4 точек.
    """
    if len(positions) < 4:
        raise ValueError("Для 3D триангуляции требуется минимум 4 точки")

    x1, y1, z1 = positions[0]
    A = []
    b = []

    for i in range(1, len(positions)):
        xi, yi, zi = positions[i]
        di2 = distances[i] ** 2
        d1_2 = distances[0] ** 2

        A.append([
            2 * (xi - x1),
            2 * (yi - y1),
            2 * (zi - z1)
        ])
        b.append(
            di2 - d1_2
            - xi**2 + x1**2
            - yi**2 + y1**2
            - zi**2 + z1**2
        )

    try:
        from numpy.linalg import lstsq
        import numpy as np

        A_mat = np.array(A)
        b_vec = np.array(b)

        result, residuals, rank, s = lstsq(A_mat, b_vec, rcond=None)
        x_est = result[0]
        y_est = result[1]
        z_est = result[2]
        return x_est, y_est, z_est
    except Exception as e:
        logger.error(f"Ошибка при триангуляции 3D: {e}")
        raise ValueError("Ошибка при решении системы")

async def update_access_point_positions(db: AsyncSession):
    """
    Пересчитывает координаты ВСЕХ стационарных точек доступа с x/y/z == None
    (глобальная периодическая триангуляция).
    """
    logger.info("Начинаем обновление координат всех AP (3D)")

    result = await db.execute(
        select(AccessPoint).where(
            ((AccessPoint.x.is_(None)) | (AccessPoint.y.is_(None)) | (AccessPoint.z.is_(None))) & (AccessPoint.is_mobile == False)
        )
    )
    aps_to_update = result.scalars().all()

    for ap in aps_to_update:
        logger.info(f"Анализ AP: {ap.bssid} для update_access_point_positions")

        stmt = (
            select(WiFiObs, WiFiSnapshot)
            .join(WiFiSnapshot, WiFiObs.snapshot_id == WiFiSnapshot.id)
            .options(contains_eager(WiFiObs.snapshot))
            .where(WiFiObs.access_point_id == ap.id)
            .where(
                (WiFiSnapshot.building_id == ap.building_id) &
                (WiFiSnapshot.x.is_not(None)) &
                (WiFiSnapshot.y.is_not(None)) &
                (WiFiSnapshot.z.is_not(None))
            )
            .order_by(WiFiSnapshot.timestamp.desc())
            .limit(15)
        )
        result = await db.execute(stmt)
        observations_list = [obs for obs, snap in result.all()]

        # DIAGNOSTIC: Check if selectinload populated snapshots immediately
        if observations_list:
            logger.debug(f"AP {ap.bssid}: Checking snapshot status immediately after initial query with selectinload.")
            for i, obs_check in enumerate(observations_list):
                insp_check = sqlalchemy_inspect(obs_check)
                snapshot_value = insp_check.attrs.snapshot.loaded_value
                if snapshot_value is not sqlalchemy.orm.attributes.NO_VALUE:
                    logger.debug(f"AP {ap.bssid}, Obs {obs_check.id} (index {i}): Snapshot IS LOADED immediately after query. Value: {snapshot_value}")
                else:
                    logger.warning(f"AP {ap.bssid}, Obs {obs_check.id} (index {i}): Snapshot IS NOT LOADED (NO_VALUE) immediately after query.")
        # END DIAGNOSTIC

        processed_observations_data = [] # Store tuples of ((x,y,z), distance)
        if observations_list:
            logger.debug(f"Processing {len(observations_list)} WiFiObs for AP {ap.bssid} in update_access_point_positions.")
            for obs_item in observations_list:
                try:
                    # logger.debug(f"Obs {obs_item.id} (AP {ap.bssid}): Checking snapshot state before refresh.") # Temporarily removed refresh logic
                    # insp = sqlalchemy_inspect(obs_item)
                    # snapshot_loaded_value_before_refresh = insp.attrs.snapshot.loaded_value
                    # if snapshot_loaded_value_before_refresh is not sqlalchemy.orm.attributes.NO_VALUE:
                    #     logger.debug(f"Obs {obs_item.id}: Snapshot ALREADY LOADED before refresh. Value: {snapshot_loaded_value_before_refresh}")
                    # else:
                    #     logger.debug(f"Obs {obs_item.id}: Snapshot NOT loaded before refresh (NO_VALUE).")

                    # logger.debug(f"Obs {obs_item.id}: Attempting await db.refresh(obs_item, attribute_names=['snapshot'])") # Temporarily removed refresh
                    # await db.refresh(obs_item, attribute_names=['snapshot'])
                    
                    # insp_after_refresh = sqlalchemy_inspect(obs_item) # Re-inspect
                    # snapshot_loaded_value_after_refresh = insp_after_refresh.attrs.snapshot.loaded_value
                    # if snapshot_loaded_value_after_refresh is not sqlalchemy.orm.attributes.NO_VALUE:
                    #     logger.debug(f"Obs {obs_item.id}: Snapshot loaded after refresh. Value: {snapshot_loaded_value_after_refresh}")
                    # else:
                    #     logger.error(f"Obs {obs_item.id}: Snapshot STILL NOT loaded after refresh (NO_VALUE). This is problematic.")

                    logger.debug(f"Obs {obs_item.id} (AP {ap.bssid}): Accessing obs_item.snapshot") # Changed logging to include AP BSSID
                    snap = obs_item.snapshot # Access snapshot immediately

                    if snap is None:
                        logger.warning(f"WiFiObs {obs_item.id} has None snapshot after access for AP {ap.bssid}.")
                        continue
                    
                    # Optional: Detailed logging of snapshot state if needed
                    # insp_obs = sqlalchemy_inspect(obs_item)
                    # if insp_obs.persistent:
                    #     loaded_value = insp_obs.attrs.snapshot.loaded_value
                    #     logger.debug(f"Obs {obs_item.id}, Snapshot attr loaded: {type(loaded_value)}, Is instance: {isinstance(loaded_value, WiFiSnapshot)}")

                    if snap.x is not None and snap.y is not None and snap.z is not None:
                        distance = rssi_to_distance(obs_item.rssi)
                        processed_observations_data.append(
                            ((snap.x, snap.y, snap.z), distance)
                        )
                    else:
                        logger.debug(f"Snapshot ID {snap.id} for Obs {obs_item.id} (AP {ap.bssid}) lacks full coordinates.")
                
                except sqlalchemy.exc.MissingGreenlet as mg_exc:
                    logger.error(f"MissingGreenlet for WiFiObs {obs_item.id} (AP {ap.bssid}) in update_access_point_positions: {mg_exc}")
                    insp = sqlalchemy_inspect(obs_item)
                    if insp.persistent:
                         logger.error(f"Object state (snapshot loaded_value): {insp.attrs.snapshot.loaded_value}")
                    else:
                         logger.error("Object not persistent or no inspect info for snapshot in update_access_point_positions.")
                    logger.error(f"Session: {db}")
                    raise 
                except Exception as e:
                    logger.error(f"Unexpected error for WiFiObs {obs_item.id} (AP {ap.bssid}) in update_access_point_positions: {e}")
                    raise
        
        positions = [data[0] for data in processed_observations_data]
        distances = [data[1] for data in processed_observations_data]

        if len(positions) < 4:
            logger.info(f"Недостаточно данных для 3D триангуляции AP {ap.bssid} (нужно >= 4, есть {len(positions)})")
            continue

        try:
            x_new, y_new, z_new = trilaterate_3d(positions, distances)
            logger.info(f"Обновляем координаты AP {ap.bssid}: ({x_new:.2f}, {y_new:.2f}, {z_new:.2f})")
            await db.execute(
                update(AccessPoint)
                .where(AccessPoint.id == ap.id)
                .values(x=x_new, y=y_new, z=z_new)
            )
        except Exception as e:
            logger.warning(f"Не удалось триангулировать AP {ap.bssid}: {e}")

    await db.commit()
    logger.info("Обновление координат завершено (3D)")

async def recalculate_access_point_coords(bssid: str, db: AsyncSession):
    """
    Пересчитывает координаты только одной точки доступа по bssid.
    """
    result = await db.execute(
        select(AccessPoint).where(AccessPoint.bssid == bssid)
    )
    ap = result.scalars().first()
    if not ap or ap.is_mobile:
        logger.info(f"AP {bssid} не найден или является мобильной, пересчёт не требуется")
        return

    logger.info(f"Начинаем пересчёт координат для AP: {ap.bssid}") # Added logging
    stmt = (
        select(WiFiObs, WiFiSnapshot)
        .join(WiFiSnapshot, WiFiObs.snapshot_id == WiFiSnapshot.id)
        .options(contains_eager(WiFiObs.snapshot)) # Changed to contains_eager
        .where(WiFiObs.access_point_id == ap.id)
        .where(
            (WiFiSnapshot.building_id == ap.building_id) &
            (WiFiSnapshot.x.is_not(None)) & (WiFiSnapshot.y.is_not(None)) & (WiFiSnapshot.z.is_not(None))
        )
        .order_by(WiFiSnapshot.timestamp.desc())
        .limit(15)
    )
    result = await db.execute(stmt)
    observations_list = [obs for obs, snap in result.all()]

    # DIAGNOSTIC: Check if selectinload populated snapshots immediately
    if observations_list:
        logger.debug(f"AP {bssid}: Checking snapshot status immediately after initial query with selectinload.")
        for i, obs_check in enumerate(observations_list):
            insp_check = sqlalchemy_inspect(obs_check)
            snapshot_value = insp_check.attrs.snapshot.loaded_value
            if snapshot_value is not sqlalchemy.orm.attributes.NO_VALUE:
                logger.debug(f"AP {bssid}, Obs {obs_check.id} (index {i}): Snapshot IS LOADED immediately after query. Value: {snapshot_value}")
            else:
                logger.warning(f"AP {bssid}, Obs {obs_check.id} (index {i}): Snapshot IS NOT LOADED (NO_VALUE) immediately after query.")
    # END DIAGNOSTIC

    processed_observations_data = [] # Store tuples of ((x,y,z), distance)
    if observations_list:
        logger.debug(f"Processing {len(observations_list)} WiFiObs objects for AP {bssid} in recalculate_access_point_coords.")
        for obs_item in observations_list:
            try:
                # logger.debug(f"Obs {obs_item.id} (AP {bssid}): Checking snapshot state before refresh.") # Temporarily removed refresh logic
                # insp = sqlalchemy_inspect(obs_item)
                # snapshot_loaded_value_before_refresh = insp.attrs.snapshot.loaded_value
                # if snapshot_loaded_value_before_refresh is not sqlalchemy.orm.attributes.NO_VALUE:
                #     logger.debug(f"Obs {obs_item.id}: Snapshot ALREADY LOADED before refresh. Value: {snapshot_loaded_value_before_refresh}")
                # else:
                #     logger.debug(f"Obs {obs_item.id}: Snapshot NOT loaded before refresh (NO_VALUE).")

                # logger.debug(f"Obs {obs_item.id}: Attempting await db.refresh(obs_item, attribute_names=['snapshot'])") # Temporarily removed refresh
                # await db.refresh(obs_item, attribute_names=['snapshot'])
                
                # insp_after_refresh = sqlalchemy_inspect(obs_item) # Re-inspect
                # snapshot_loaded_value_after_refresh = insp_after_refresh.attrs.snapshot.loaded_value
                # if snapshot_loaded_value_after_refresh is not sqlalchemy.orm.attributes.NO_VALUE:
                #     logger.debug(f"Obs {obs_item.id}: Snapshot loaded after refresh. Value: {snapshot_loaded_value_after_refresh}")
                # else:
                #     logger.error(f"Obs {obs_item.id}: Snapshot STILL NOT loaded after refresh (NO_VALUE). This is problematic.")

                logger.debug(f"Obs {obs_item.id} (AP {bssid}): Accessing obs_item.snapshot") # Changed logging to include AP BSSID
                snap = obs_item.snapshot # Access snapshot immediately

                if snap is None:
                     logger.warning(f"WiFiObs {obs_item.id} has None snapshot after access for AP {bssid}.")
                     continue
                
                # Optional: Detailed logging of snapshot state if needed
                # insp_obs = sqlalchemy_inspect(obs_item)
                # if insp_obs.persistent:
                #    loaded_value = insp_obs.attrs.snapshot.loaded_value
                #    logger.debug(f"Obs {obs_item.id}, Snapshot attr loaded: {type(loaded_value)}, Is instance: {isinstance(loaded_value, WiFiSnapshot)}")

                if snap.x is not None and snap.y is not None and snap.z is not None:
                    distance = rssi_to_distance(obs_item.rssi)
                    processed_observations_data.append(
                        ((snap.x, snap.y, snap.z), distance)
                    )
                else:
                    logger.debug(f"Snapshot ID {snap.id} for Obs {obs_item.id} (AP {bssid}) lacks full coordinates (x,y,z).")

            except sqlalchemy.exc.MissingGreenlet as mg_exc:
                logger.error(f"MissingGreenlet for WiFiObs {obs_item.id} (AP {bssid}) in recalculate_access_point_coords: {mg_exc}")
                insp = sqlalchemy_inspect(obs_item)
                if insp.persistent:
                     logger.error(f"Object state (snapshot loaded_value): {insp.attrs.snapshot.loaded_value}")
                else:
                     logger.error("Object not persistent or no inspect info for snapshot in recalculate_access_point_coords.")
                logger.error(f"Session: {db}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error for WiFiObs {obs_item.id} (AP {bssid}) in recalculate_access_point_coords: {e}")
                raise
    
    positions = [data[0] for data in processed_observations_data]
    distances = [data[1] for data in processed_observations_data]

    if len(positions) < 4:
        logger.info(f"Недостаточно данных для 3D триангуляции AP {bssid} (нужно >= 4, есть {len(positions)})")
        return

    try:
        x_new, y_new, z_new = trilaterate_3d(positions, distances)
        logger.info(f"Обновляем координаты AP {bssid}: ({x_new:.2f}, {y_new:.2f}, {z_new:.2f})")
        await db.execute(
            update(AccessPoint)
            .where(AccessPoint.id == ap.id)
            .values(x=x_new, y=y_new, z=z_new)
        )
    except Exception as e:
        logger.warning(f"Ошибка при пересчёте координат AP {bssid}: {e}")
        # Можно рассмотреть необходимость db.rollback() здесь в определенных сценариях,
        # но основной откат обрабатывается в вызывающей функции upload_scan.
        # Если здесь произойдет исключение, оно поднимется выше и приведет к откату в upload_scan.

import httpx

async def reverse_geocode_osm(lat: float, lon: float) -> dict:
    """
    Асинхронно получает информацию о здании по координатам через OSM Nominatim.
    """
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "format": "jsonv2",
        "lat": lat,
        "lon": lon,
        "addressdetails": 1,
        "extratags": 1,
        "zoom": 18
    }
    headers = {
        "User-Agent": "navigation-diploma/1.0"
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()