import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.db.session import AsyncSessionLocal
from app.services.geo_solver import update_access_point_positions

logger = logging.getLogger(__name__)

# инициализируем планировщик
scheduler = AsyncIOScheduler()

async def _run_update_job() -> None:
    """
    Обёртка для асинхронного запуска пересчёта координат AP.
    """
    logger.info("Job 'update_access_point_positions' started")
    async with AsyncSessionLocal() as session:
        await update_access_point_positions(session)
    logger.info("Job 'update_access_point_positions' finished")

def start_scheduler() -> None:
    """
    Запускает APScheduler и добавляет задачу:

    - ID: update_ap_positions
    - Расписание: каждый день в 3:00 утра
    """
    # удалим старую задачу, если она была
    scheduler.remove_job('update_ap_positions', jobstore=None, job_defaults=None, silence_exception=True)

    # добавляем новую по cron
    scheduler.add_job(
        _run_update_job,
        trigger=CronTrigger(hour=3, minute=0),
        id='update_ap_positions',
        replace_existing=True,
        coalesce=True,      # если пропущено выполнение, выполнить сразу после старта
        max_instances=1
    )
    scheduler.start()
    logger.info("Scheduler started: job 'update_ap_positions' scheduled at 03:00 daily")
