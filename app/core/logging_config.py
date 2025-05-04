import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from app.core.config import settings


def setup_logging() -> None:
    """
    Инициализация логгирования:
    - Создаёт папку для логов, если её нет.
    - Ротирующая запись в файл + вывод в stdout.
    """
    # Убедимся, что директория для логов существует
    os.makedirs(settings.LOG_DIR, exist_ok=True)

    # Путь до файла логов
    log_path = os.path.join(settings.LOG_DIR, settings.LOG_FILENAME)

    # Ротирующий файловый обработчик: до 10 МБ, 5 файлов-архивов
    file_handler = RotatingFileHandler(
        filename=log_path,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )

    # Общий формат логов
    fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    file_handler.setFormatter(fmt)

    # Потоки логов: файл + stdout
    handlers = [file_handler, logging.StreamHandler(sys.stdout)]

    # Конфигурируем root logger
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        handlers=handlers
    )