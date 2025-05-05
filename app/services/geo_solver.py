import math
import logging
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.access_point import AccessPoint
from app.db.models.wifi_obs import WiFiObs
from app.db.models.wifi_snapshot import WiFiSnapshot

logger = logging.getLogger(__name__)

DEFAULT_TX_POWER_DBM = -50  # Типовое значение мощности сигнала на 1 м
DEFAULT_PATH_LOSS_EXPONENT = 2.0  # Для помещений: 1.6 - 3.3


def rssi_to_distance(rssi: float, tx_power: float = DEFAULT_TX_POWER_DBM, n: float = DEFAULT_PATH_LOSS_EXPONENT) -> float:
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
    """
    if len(positions) < 4:
        raise ValueError("Для 3D триангуляции требуется минимум 4 точки")

    # Базируем систему на первой точке
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

    # Решаем A * X = b через метод наименьших квадратов
    try:
        # Приводим к матричной форме (используем стандартный питон)
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
    logger.info("Начинаем обновление координат точек доступа (3D)")

    result = await db.execute(
        select(AccessPoint).where(
            (AccessPoint.x.is_(None)) | (AccessPoint.y.is_(None)) | (AccessPoint.z.is_(None))
        )
    )
    aps_to_update = result.scalars().all()

    for ap in aps_to_update:
        logger.info(f"Анализ AP: {ap.bssid}")

        result = await db.execute(
            select(WiFiObs)
            .where(WiFiObs.access_point_id == ap.id)
            .join(WiFiSnapshot, WiFiObs.snapshot_id == WiFiSnapshot.id)
            .where(
                (WiFiSnapshot.x.is_not(None)) &
                (WiFiSnapshot.y.is_not(None)) &
                (WiFiSnapshot.z.is_not(None))
            )
            .order_by(WiFiSnapshot.timestamp.desc())
            .limit(15)
        )
        observations = result.scalars().all()

        positions = []
        distances = []

        for obs in observations:
            snap = obs.snapshot
            if snap.x is not None and snap.y is not None and snap.z is not None:
                distance = rssi_to_distance(obs.rssi)
                positions.append((snap.x, snap.y, snap.z))
                distances.append(distance)

        if len(positions) < 4:
            logger.info(f"Недостаточно данных для 3D триангуляции AP {ap.bssid}")
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
