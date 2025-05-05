from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.api.routers import health, upload, map as map_router, ap, auth
from app.tasks.scheduler import start_scheduler

# Настраиваем логирование
setup_logging()

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    openapi_prefix=settings.API_PREFIX
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-domain.com"],  # Настроить реальные домены в продакшене
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(upload.router)
app.include_router(map_router.router)
app.include_router(ap.router)

# Запуск планировщика задач
start_scheduler()
