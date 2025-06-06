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
    Пересчитывает координаты ВСЕХ стационарных точек доступа (глобальная периодическая триангуляция).
    Формирует подробный лог по каждой AP: статус, причина, изменение точности и координат.
    """
    logger.info("Начинаем обновление координат всех AP (3D)")
    ap_recalc_log = []

    result = await db.execute(
        select(AccessPoint).where(AccessPoint.is_mobile == False)
    )
    aps_to_update = result.scalars().all()

    for ap in aps_to_update:
        ap_log = {
            "bssid": ap.bssid,
            "id": ap.id,
            "old_coords": (ap.x, ap.y, ap.z),
            "old_accuracy": ap.accuracy,
            "status": None,
            "reason": None,
            "new_coords": None,
            "new_accuracy": None,
            "accuracy_delta": None
        }
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
                    if obs_item.snapshot is None:
                        logger.warning(f"WiFiObs {obs_item.id} has None snapshot after access for AP {ap.bssid}.")
                        continue
                    if obs_item.snapshot.x is not None and obs_item.snapshot.y is not None and obs_item.snapshot.z is not None:
                        distance = rssi_to_distance(obs_item.rssi)
                        processed_observations_data.append(
                            ((obs_item.snapshot.x, obs_item.snapshot.y, obs_item.snapshot.z), distance)
                        )
                    else:
                        logger.debug(f"Snapshot ID {obs_item.snapshot.id} for Obs {obs_item.id} (AP {ap.bssid}) lacks full coordinates.")
                except Exception as e:
                    logger.error(f"Unexpected error for WiFiObs {obs_item.id} (AP {ap.bssid}) in update_access_point_positions: {e}")
                    continue
        positions = [data[0] for data in processed_observations_data]
        distances = [data[1] for data in processed_observations_data]
        filtered = filter_observations(positions, distances)
        try:
            if len(filtered) >= 4:
                f_positions, f_distances = zip(*filtered)
                new_coords = weighted_least_squares_3d(f_positions, f_distances)
                old_coords = (ap.x, ap.y, ap.z)
                x_new, y_new, z_new = smooth_coordinates(old_coords, new_coords, alpha=0.5)
                import numpy as np
                est_point = np.array([x_new, y_new, z_new])
                pred_dists = [np.linalg.norm(est_point - np.array(pos)) for pos in f_positions]
                accuracy = float(np.mean([abs(pd - dd) for pd, dd in zip(pred_dists, f_distances)]))
                await db.execute(
                    update(AccessPoint)
                    .where(AccessPoint.id == ap.id)
                    .values(x=x_new, y=y_new, z=z_new, accuracy=accuracy if accuracy is not None else 9999.0)
                )
                ap_log["status"] = "пересчитана"
                ap_log["reason"] = "3D multilateration"
                ap_log["new_coords"] = (x_new, y_new, z_new)
                ap_log["new_accuracy"] = accuracy
                ap_log["accuracy_delta"] = (ap.accuracy - accuracy) if (ap.accuracy is not None and accuracy is not None) else None
                logger.info(f"Обновляем координаты AP {ap.bssid} (3D): ({x_new:.2f}, {y_new:.2f}, {z_new:.2f}), accuracy={accuracy:.2f} м")
            else:
                filtered_2d = [((x, y), d) for (x, y, z), d in filtered if x is not None and y is not None]
                if len(filtered_2d) >= 3:
                    f2d_positions, f2d_distances = zip(*filtered_2d)
                    x_new, y_new = weighted_least_squares_2d(f2d_positions, f2d_distances)
                    old_coords = (ap.x, ap.y)
                    x_new, y_new = smooth_coordinates(old_coords, (x_new, y_new), alpha=0.5)
                    est_point = np.array([x_new, y_new])
                    pred_dists = [np.linalg.norm(est_point - np.array(pos)) for pos in f2d_positions]
                    accuracy = float(np.mean([abs(pd - dd) for pd, dd in zip(pred_dists, f2d_distances)]))
                    await db.execute(
                        update(AccessPoint)
                        .where(AccessPoint.id == ap.id)
                        .values(x=x_new, y=y_new, accuracy=accuracy if accuracy is not None else 9999.0)
                    )
                    ap_log["status"] = "пересчитана"
                    ap_log["reason"] = "2D multilateration"
                    ap_log["new_coords"] = (x_new, y_new, ap.z)
                    ap_log["new_accuracy"] = accuracy
                    ap_log["accuracy_delta"] = (ap.accuracy - accuracy) if (ap.accuracy is not None and accuracy is not None) else None
                    logger.info(f"Обновляем координаты AP {ap.bssid} (2D): ({x_new:.2f}, {y_new:.2f}), accuracy={accuracy:.2f} м")
                else:
                    ap_log["status"] = "не пересчитана"
                    ap_log["reason"] = f"Недостаточно валидных данных для 2D/3D оптимизации (есть {len(filtered)})"
                    logger.info(f"Недостаточно валидных данных для 2D/3D оптимизации AP {ap.bssid} (есть {len(filtered)})")
        except Exception as e:
            ap_log["status"] = "не пересчитана"
            ap_log["reason"] = f"Ошибка оптимизации: {e}"
            logger.warning(f"Не удалось уточнить координаты AP {ap.bssid}: {e}")
        ap_recalc_log.append(ap_log)
    await db.commit()
    logger.info("Обновление координат завершено (3D/2D, WLS)")
    # Итоговый summary-лог по массовому пересчёту AP
    total = len(ap_recalc_log)
    success = sum(1 for entry in ap_recalc_log if entry["status"] == "пересчитана")
    failed = total - success
    # Считаем среднее улучшение точности только для успешно пересчитанных
    deltas = [entry["accuracy_delta"] for entry in ap_recalc_log if entry["status"] == "пересчитана" and entry["accuracy_delta"] is not None]
    percent_improvement = (sum(deltas) / len(deltas) / max([entry["old_accuracy"] for entry in ap_recalc_log if entry["old_accuracy"]]) * 100) if deltas else 0.0
    logger.info(f"Массовый пересчёт AP: успешно {success}/{total}, неуспешно {failed}/{total}, среднее улучшение точности: {percent_improvement:.2f}%")

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
    snapshot_accuracies = []
    if observations_list:
        logger.debug(f"Processing {len(observations_list)} WiFiObs objects for AP {bssid} in recalculate_access_point_coords.")
        for obs_item in observations_list:
            try:
                obs_accuracy = None
                if hasattr(obs_item.snapshot, 'accuracy') and obs_item.snapshot.accuracy is not None:
                    obs_accuracy = obs_item.snapshot.accuracy
                    snapshot_accuracies.append(obs_accuracy)
                if obs_item.snapshot.x is not None and obs_item.snapshot.y is not None and obs_item.snapshot.z is not None:
                    distance = rssi_to_distance(obs_item.rssi)
                    processed_observations_data.append(
                        ((obs_item.snapshot.x, obs_item.snapshot.y, obs_item.snapshot.z), distance, obs_accuracy)
                    )
                else:
                    logger.debug(f"Snapshot ID {obs_item.snapshot.id} for Obs {obs_item.id} (AP {bssid}) lacks full coordinates (x,y,z).")
            except Exception as e:
                logger.error(f"Unexpected error for WiFiObs {obs_item.id} (AP {bssid}) in recalculate_access_point_coords: {e}")
                raise
    
    # Новый формат: позиции, расстояния, точности
    positions = [data[0] for data in processed_observations_data]
    distances = [data[1] for data in processed_observations_data]
    accuracies = [data[2] if data[2] is not None else 10.0 for data in processed_observations_data]
    import numpy as np
    logger.info(f"AP {bssid}: used positions={positions}, distances={distances}, accuracies={accuracies}")
    if len(positions) >= 4:
        # Веса: чем хуже accuracy или больше distance, тем меньше вес
        weights = []
        for acc, dist in zip(accuracies, distances):
            w_acc = 1.0 / max(acc, 1.0) if acc is not None else 0.1
            w_dist = 1.0 / max(dist, 1.0) if dist < 200.0 else 0.01
            weights.append(w_acc * w_dist)
        logger.info(f"AP {bssid}: weights={weights}")
        try:
            # --- robust multilateration (RANSAC + NLS) ---
            new_coords, inliers = robust_multilateration_3d(positions, distances, weights=weights, n_iter=50, min_inliers=4, threshold=5.0)
            logger.info(f"AP {bssid}: robust multilateration inliers: {inliers}")
            old_coords = (ap.x, ap.y, ap.z)
            x_new, y_new, z_new = smooth_coordinates(old_coords, new_coords, alpha=0.5)
            est_point = np.array([x_new, y_new, z_new])
            pred_dists = [np.linalg.norm(est_point - np.array(positions[i])) for i in inliers]
            inlier_distances = [distances[i] for i in inliers]
            accuracy = float(np.mean([abs(pd - dd) for pd, dd in zip(pred_dists, inlier_distances)]))
            valid_snapshot_accuracies = [accuracies[i] for i in inliers if accuracies[i] is not None and accuracies[i] < 100.0]
            if (accuracy is None or accuracy > 1000.0) and valid_snapshot_accuracies:
                accuracy = float(min(valid_snapshot_accuracies))
                logger.info(f"Fallback: используем минимальную snapshot accuracy для AP {bssid}: {accuracy:.2f} м")
            logger.info(f"Обновляем координаты AP {bssid} (3D, robust): ({x_new:.2f}, {y_new:.2f}, {z_new:.2f}), accuracy={accuracy:.2f} м")
            await db.execute(
                update(AccessPoint)
                .where(AccessPoint.id == ap.id)
                .values(x=x_new, y=y_new, z=z_new, accuracy=accuracy if accuracy is not None else 9999.0)
            )
        except Exception as e:
            logger.warning(f"Ошибка при robust уточнении координат AP {bssid} (3D): {e}")
            # fallback на старый метод
            try:
                new_coords = weighted_least_squares_3d(positions, distances, weights=weights)
                old_coords = (ap.x, ap.y, ap.z)
                x_new, y_new, z_new = smooth_coordinates(old_coords, new_coords, alpha=0.5)
                est_point = np.array([x_new, y_new, z_new])
                pred_dists = [np.linalg.norm(est_point - np.array(pos)) for pos in positions]
                accuracy = float(np.mean([abs(pd - dd) for pd, dd in zip(pred_dists, distances)]))
                valid_snapshot_accuracies = [a for a in snapshot_accuracies if a is not None and a < 100.0]
                if (accuracy is None or accuracy > 1000.0) and valid_snapshot_accuracies:
                    accuracy = float(min(valid_snapshot_accuracies))
                    logger.info(f"Fallback: используем минимальную snapshot accuracy для AP {bssid}: {accuracy:.2f} м")
                logger.info(f"Обновляем координаты AP {bssid} (3D, fallback): ({x_new:.2f}, {y_new:.2f}, {z_new:.2f}), accuracy={accuracy:.2f} м")
                await db.execute(
                    update(AccessPoint)
                    .where(AccessPoint.id == ap.id)
                    .values(x=x_new, y=y_new, z=z_new, accuracy=accuracy if accuracy is not None else 9999.0)
                )
            except Exception as e2:
                logger.warning(f"Ошибка при уточнении координат AP {bssid} (3D, fallback): {e2}")
    else:
        filtered_2d = [((x, y), d) for (x, y, z), d in zip(positions, distances) if x is not None and y is not None]
        if len(filtered_2d) >= 3:
            f2d_positions, f2d_distances = zip(*filtered_2d)
            f2d_accuracies = [accuracies[i] for i, ((x, y), d) in enumerate(filtered_2d)]
            weights2d = []
            for acc, dist in zip(f2d_accuracies, f2d_distances):
                w_acc = 1.0 / max(acc, 1.0) if acc is not None else 0.1
                w_dist = 1.0 / max(dist, 1.0) if dist < 200.0 else 0.01
                weights2d.append(w_acc * w_dist)
            logger.info(f"AP {bssid}: weights2d={weights2d}")
            try:
                x_new, y_new = weighted_least_squares_2d(f2d_positions, f2d_distances, weights=weights2d)
                old_coords = (ap.x, ap.y)
                x_new, y_new = smooth_coordinates(old_coords, (x_new, y_new), alpha=0.5)
                est_point = np.array([x_new, y_new])
                pred_dists = [np.linalg.norm(est_point - np.array(pos)) for pos in f2d_positions]
                accuracy = float(np.mean([abs(pd - dd) for pd, dd in zip(pred_dists, f2d_distances)]))
                valid_snapshot_accuracies = [a for a in snapshot_accuracies if a is not None and a < 100.0]
                if (accuracy is None or accuracy > 1000.0) and valid_snapshot_accuracies:
                    accuracy = float(min(valid_snapshot_accuracies))
                    logger.info(f"Fallback: используем минимальную snapshot accuracy для AP {bssid}: {accuracy:.2f} м")
                logger.info(f"Обновляем координаты AP {bssid} (2D): ({x_new:.2f}, {y_new:.2f}), accuracy={accuracy:.2f} м")
                await db.execute(
                    update(AccessPoint)
                    .where(AccessPoint.id == ap.id)
                    .values(x=x_new, y=y_new, accuracy=accuracy if accuracy is not None else 9999.0)
                )
            except Exception as e:
                logger.warning(f"Ошибка при уточнении координат AP {bssid} (2D): {e}")
        else:
            logger.info(f"Недостаточно валидных данных для 2D/3D оптимизации AP {bssid} (есть {len(filtered_2d)})")

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
from numpy.linalg import lstsq
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

from random import sample

def robust_multilateration_3d(positions, distances, weights=None, n_iter=50, min_inliers=4, threshold=5.0):
    """
    RANSAC + NLS для устойчивого multilateration.
    positions: [(x, y, z), ...]
    distances: [d1, d2, ...]
    weights: [w1, w2, ...] (опционально)
    threshold: максимальное отклонение (м) для inlier
    Возвращает: best_coords, best_inliers
    """
    import numpy as np
    from scipy.optimize import least_squares
    n = len(positions)
    if n < min_inliers:
        raise ValueError("Недостаточно данных для robust multilateration")
    best_inliers = []
    best_coords = None
    best_loss = float('inf')
    idxs = list(range(n))
    for _ in range(n_iter):
        try:
            subset = sample(idxs, min_inliers)
            pos_sub = [positions[i] for i in subset]
            dist_sub = [distances[i] for i in subset]
            w_sub = [weights[i] for i in subset] if weights is not None else None
            # NLS на подмножестве
            def residuals(x):
                dists = np.linalg.norm(np.array(pos_sub) - x, axis=1)
                if w_sub is not None:
                    return np.array(w_sub) * (dists - np.array(dist_sub))
                return dists - np.array(dist_sub)
            x0 = np.mean(pos_sub, axis=0)
            res = least_squares(residuals, x0, loss='huber', f_scale=2.0)
            candidate = res.x
            # Проверяем inliers на всех данных
            dists_all = np.linalg.norm(np.array(positions) - candidate, axis=1)
            errors = np.abs(dists_all - np.array(distances))
            inliers = [i for i, err in enumerate(errors) if err < threshold]
            loss = np.mean(errors[inliers]) if inliers else float('inf')
            if len(inliers) > len(best_inliers) or (len(inliers) == len(best_inliers) and loss < best_loss):
                best_inliers = inliers
                best_coords = candidate
                best_loss = loss
        except Exception as e:
            continue
    if not best_inliers:
        raise ValueError("RANSAC не нашёл inliers для multilateration")
    # Финальная оптимизация по inliers
    pos_in = [positions[i] for i in best_inliers]
    dist_in = [distances[i] for i in best_inliers]
    w_in = [weights[i] for i in best_inliers] if weights is not None else None
    def residuals(x):
        dists = np.linalg.norm(np.array(pos_in) - x, axis=1)
        if w_in is not None:
            return np.array(w_in) * (dists - np.array(dist_in))
        return dists - np.array(dist_in)
    x0 = np.mean(pos_in, axis=0)
    res = least_squares(residuals, x0, loss='huber', f_scale=2.0)
    return tuple(res.x), best_inliers