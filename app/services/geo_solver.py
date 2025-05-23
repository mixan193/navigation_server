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
            select(WiFiObs)
            .join(WiFiSnapshot, WiFiObs.snapshot_id == WiFiSnapshot.id)
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
        observations_list = result.scalars().all()
        processed_observations_data = []
        if observations_list:
            logger.debug(f"Processing {len(observations_list)} WiFiObs for AP {ap.bssid} in update_access_point_positions.")
            for obs_item in observations_list:
                try:
                    logger.debug(f"Obs {obs_item.id} (AP {ap.bssid}): Accessing obs_item.snapshot")
                    snap = obs_item.snapshot
                    if snap is None:
                        logger.warning(f"WiFiObs {obs_item.id} has None snapshot after access for AP {ap.bssid}.")
                        continue
                    if snap.x is not None and snap.y is not None and snap.z is not None:
                        distance = rssi_to_distance(obs_item.rssi)
                        processed_observations_data.append(
                            ((snap.x, snap.y, snap.z), distance)
                        )
                    else:
                        logger.debug(f"Snapshot ID {snap.id} for Obs {obs_item.id} (AP {ap.bssid}) lacks full coordinates.")
                except Exception as e:
                    logger.error(f"Unexpected error for WiFiObs {obs_item.id} (AP {ap.bssid}) in update_access_point_positions: {e}")
                    raise
        
        positions = [data[0] for data in processed_observations_data]
        distances = [data[1] for data in processed_observations_data]
        filtered = filter_observations(positions, distances)
        if len(filtered) >= 4:
            f_positions, f_distances = zip(*filtered)
            try:
                new_coords = weighted_least_squares_3d(f_positions, f_distances)
                # Сглаживание с предыдущими координатами
                old_coords = (ap.x, ap.y, ap.z)
                x_new, y_new, z_new = smooth_coordinates(old_coords, new_coords, alpha=0.5)
                logger.info(f"Обновляем координаты AP {ap.bssid} (3D): ({x_new:.2f}, {y_new:.2f}, {z_new:.2f})")
                await db.execute(
                    update(AccessPoint)
                    .where(AccessPoint.id == ap.id)
                    .values(x=x_new, y=y_new, z=z_new)
                )
            except Exception as e:
                logger.warning(f"Не удалось уточнить координаты AP {ap.bssid} (3D): {e}")
        else:
            # Fallback: 2D позиционирование
            filtered_2d = [((x, y), d) for (x, y, z), d in filtered if x is not None and y is not None]
            if len(filtered_2d) >= 3:
                f2d_positions, f2d_distances = zip(*filtered_2d)
                try:
                    x_new, y_new = weighted_least_squares_2d(f2d_positions, f2d_distances)
                    old_coords = (ap.x, ap.y)
                    x_new, y_new = smooth_coordinates(old_coords, (x_new, y_new), alpha=0.5)
                    logger.info(f"Обновляем координаты AP {ap.bssid} (2D): ({x_new:.2f}, {y_new:.2f})")
                    await db.execute(
                        update(AccessPoint)
                        .where(AccessPoint.id == ap.id)
                        .values(x=x_new, y=y_new)
                    )
                except Exception as e:
                    logger.warning(f"Не удалось уточнить координаты AP {ap.bssid} (2D): {e}")
            else:
                logger.info(f"Недостаточно валидных данных для 2D/3D оптимизации AP {ap.bssid} (есть {len(filtered)})")
    await db.commit()
    logger.info("Обновление координат завершено (3D/2D, WLS)")

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
        select(WiFiObs)
        .join(WiFiSnapshot, WiFiObs.snapshot_id == WiFiSnapshot.id)
        .where(WiFiObs.access_point_id == ap.id)
        .where(
            (WiFiSnapshot.building_id == ap.building_id) &
            (WiFiSnapshot.x.is_not(None)) & (WiFiSnapshot.y.is_not(None)) & (WiFiSnapshot.z.is_not(None))
        )
        .order_by(WiFiSnapshot.timestamp.desc())
        .limit(15)
    )
    result = await db.execute(stmt)
    observations_list = result.scalars().all()
    processed_observations_data = []
    if observations_list:
        logger.debug(f"Processing {len(observations_list)} WiFiObs objects for AP {bssid} in recalculate_access_point_coords.")
        for obs_item in observations_list:
            try:
                logger.debug(f"Obs {obs_item.id} (AP {bssid}): Accessing obs_item.snapshot")
                snap = obs_item.snapshot
                if snap is None:
                     logger.warning(f"WiFiObs {obs_item.id} has None snapshot after access for AP {bssid}.")
                     continue
                if snap.x is not None and snap.y is not None and snap.z is not None:
                    distance = rssi_to_distance(obs_item.rssi)
                    processed_observations_data.append(
                        ((snap.x, snap.y, snap.z), distance)
                    )
                else:
                    logger.debug(f"Snapshot ID {snap.id} for Obs {obs_item.id} (AP {bssid}) lacks full coordinates (x,y,z).")
            except Exception as e:
                logger.error(f"Unexpected error for WiFiObs {obs_item.id} (AP {bssid}) in recalculate_access_point_coords: {e}")
                raise
    
    positions = [data[0] for data in processed_observations_data]
    distances = [data[1] for data in processed_observations_data]
    filtered = filter_observations(positions, distances)
    if len(filtered) >= 4:
        f_positions, f_distances = zip(*filtered)
        try:
            new_coords = weighted_least_squares_3d(f_positions, f_distances)
            old_coords = (ap.x, ap.y, ap.z)
            x_new, y_new, z_new = smooth_coordinates(old_coords, new_coords, alpha=0.5)
            logger.info(f"Обновляем координаты AP {bssid} (3D): ({x_new:.2f}, {y_new:.2f}, {z_new:.2f})")
            await db.execute(
                update(AccessPoint)
                .where(AccessPoint.id == ap.id)
                .values(x=x_new, y=y_new, z=z_new)
            )
        except Exception as e:
            logger.warning(f"Ошибка при уточнении координат AP {bssid} (3D): {e}")
    else:
        filtered_2d = [((x, y), d) for (x, y, z), d in filtered if x is not None and y is not None]
        if len(filtered_2d) >= 3:
            f2d_positions, f2d_distances = zip(*filtered_2d)
            try:
                x_new, y_new = weighted_least_squares_2d(f2d_positions, f2d_distances)
                old_coords = (ap.x, ap.y)
                x_new, y_new = smooth_coordinates(old_coords, (x_new, y_new), alpha=0.5)
                logger.info(f"Обновляем координаты AP {bssid} (2D): ({x_new:.2f}, {y_new:.2f})")
                await db.execute(
                    update(AccessPoint)
                    .where(AccessPoint.id == ap.id)
                    .values(x=x_new, y=y_new)
                )
            except Exception as e:
                logger.warning(f"Ошибка при уточнении координат AP {bssid} (2D): {e}")
        else:
            logger.info(f"Недостаточно валидных данных для 2D/3D оптимизации AP {bssid} (есть {len(filtered)})")

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

import numpy as np
from scipy.optimize import least_squares

def filter_observations(positions, distances, max_distance=50.0, min_rssi=-95):
    """
    Фильтрует аномальные наблюдения: слишком большие расстояния, неадекватные координаты.
    """
    filtered = [ (pos, dist) for pos, dist in zip(positions, distances)
                if 0 < dist < max_distance and all(np.isfinite(pos)) ]
    return filtered


def weighted_least_squares_3d(positions, distances, weights=None):
    """
    Взвешенная нелинейная оптимизация для уточнения координат AP.
    positions: [(x, y, z), ...]
    distances: [d1, d2, ...]
    weights: [w1, w2, ...] (опционально)
    """
    positions = np.array(positions)
    distances = np.array(distances)
    if weights is None:
        # Чем ближе точка, тем выше вес (обратная пропорция расстоянию)
        weights = 1.0 / np.clip(distances, 1.0, None)
    weights = np.array(weights)

    def residuals(x):
        dists = np.linalg.norm(positions - x, axis=1)
        return weights * (dists - distances)

    # Начальная точка — геометрический центр
    x0 = np.average(positions, axis=0, weights=weights)
    res = least_squares(residuals, x0, loss='huber', f_scale=2.0)
    return tuple(res.x)

def weighted_least_squares_2d(positions, distances, weights=None):
    """
    Взвешенная нелинейная оптимизация для уточнения координат AP в 2D.
    positions: [(x, y), ...]
    distances: [d1, d2, ...]
    weights: [w1, w2, ...] (опционально)
    """
    positions = np.array(positions)
    distances = np.array(distances)
    if weights is None:
        weights = 1.0 / np.clip(distances, 1.0, None)
    weights = np.array(weights)

    def residuals(x):
        dists = np.linalg.norm(positions - x, axis=1)
        return weights * (dists - distances)

    x0 = np.average(positions, axis=0, weights=weights)
    res = least_squares(residuals, x0, loss='huber', f_scale=2.0)
    return tuple(res.x)

def smooth_coordinates(old_coords, new_coords, alpha=0.5):
    """
    Сглаживание координат (экспоненциальное скользящее среднее).
    """
    if old_coords is None or any(c is None for c in old_coords):
        return new_coords
    return tuple(alpha * n + (1 - alpha) * o for o, n in zip(old_coords, new_coords))