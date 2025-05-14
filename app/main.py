from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.db.base import Base
from app.db.session import async_engine

# Импорт роутеров
from app.api.routers.health import router as health_router
from app.api.routers.upload import router as upload_router
from app.api.routers.map import router as map_router
from app.api.routers.ap import router as ap_router

app = FastAPI(
    title="Navigation API",
    version="1.0.0"
)

# Настройка CORS для клиента
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # или указать конкретный домен фронтенда
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    async with async_engine.begin() as conn:
        # Создание всех таблиц при старте
        await conn.run_sync(Base.metadata.create_all)

# Подключаем роутеры с версией API
app.include_router(health_router, prefix="/v1/health", tags=["health"])
app.include_router(upload_router, prefix="/v1/upload", tags=["upload"])
app.include_router(map_router, prefix="/v1/map", tags=["map"])
app.include_router(ap_router, prefix="/v1/ap", tags=["access_points"])

@app.get("/v1/health-db", tags=["health"])
async def health_db(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(text("SELECT 1"))
    return {"db_ok": bool(result.scalar())}