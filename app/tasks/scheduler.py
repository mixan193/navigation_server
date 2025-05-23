import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.db.session import AsyncSessionLocal
from app.services.geo_solver import update_access_point_positions
from app.services.map_builder import adjust_building_maps

logger = logging.getLogger(__name__)

# Инициализируем планировщик
scheduler = AsyncIOScheduler()

async def _run_update_job() -> None:
    """
    Обёртка для асинхронного запуска пересчёта координат AP.
    """
    logger.info("Job 'update_access_point_positions' started")
    async with AsyncSessionLocal() as session:
        await update_access_point_positions(session)
    logger.info("Job 'update_access_point_positions' finished")

async def _run_map_adjust_job() -> None:
    """
    Обёртка для запуска автокоррекции карт зданий.
    """
    logger.info("Job 'adjust_building_maps' started")
    async with AsyncSessionLocal() as session:
        await adjust_building_maps(session)
    logger.info("Job 'adjust_building_maps' finished")

def start_scheduler() -> None:
    """
    Запускает APScheduler и добавляет задачи:
    - update_ap_positions: каждый день в 3:00 утра
    - adjust_building_maps: каждый день в 4:00 утра
    """
    # Удаляем старые задачи, если были, перед повторной регистрацией
    try:
        scheduler.remove_job('update_ap_positions')
    except Exception:
        pass
    try:
        scheduler.remove_job('adjust_building_maps')
    except Exception:
        pass

    # Добавляем задачу пересчёта координат AP (ежедневно в 03:00)
    scheduler.add_job(
        _run_update_job,
        trigger=CronTrigger(hour=3, minute=0),
        id='update_ap_positions',
        replace_existing=True,
        coalesce=True,
        max_instances=1
    )
    # Добавляем задачу автокорректировки карт зданий (ежедневно в 04:00)
    scheduler.add_job(
        _run_map_adjust_job,
        trigger=CronTrigger(hour=4, minute=0),
        id='adjust_building_maps',
        replace_existing=True,
        coalesce=True,
        max_instances=1
    )
    scheduler.start()
    logger.info("Scheduler started: job 'update_ap_positions' scheduled at 03:00 and job 'adjust_building_maps' at 04:00 daily")
