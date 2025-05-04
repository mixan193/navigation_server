import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.api.routers import health, upload, map as map_router, ap

def create_app() -> FastAPI:
    """
    Создаёт и настраивает экземпляр FastAPI:
    - Инициализирует логгирование.
    - Подключает CORS-middleware.
    - Настраивает OpenAPI и Swagger UI под префиксом API.
    - Регистрирует все маршруты.
    """
    # 1) Логи
    setup_logging()

    # 2) Экземпляр приложения
    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
        openapi_url=f"{settings.API_PREFIX}/openapi.json",
        docs_url=f"{settings.API_PREFIX}/docs",
        redoc_url=f"{settings.API_PREFIX}/redoc",
    )

    # 3) CORS — пока что разрешаем всё, в продакшне лучше ограничить по доменам
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 4) Роутеры
    # /health
    app.include_router(health.router, prefix="/health", tags=["Health"])
    # /v1/upload_scan
    app.include_router(upload.router, prefix=f"{settings.API_PREFIX}/upload_scan", tags=["Upload"])
    # /v1/map/{building_id}
    app.include_router(map_router.router, prefix=f"{settings.API_PREFIX}/map", tags=["Map"])
    # /v1/ap/{bssid}
    app.include_router(ap.router, prefix=f"{settings.API_PREFIX}/ap", tags=["Access Point"])

    return app

app = create_app()

if __name__ == "__main__":
    """
    Запускаем Uvicorn, чтобы:
    - слушать на всех интерфейсах (0.0.0.0),
    - порт 8000,
    - логировать в соответствии с уровнем из настроек,
    - включать авто-перезапуск в режиме DEBUG.
    """
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        log_level=settings.LOG_LEVEL.lower(),
        reload=settings.DEBUG,
    )