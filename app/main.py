from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.db.base import Base
from app.db.session import async_engine
from app.tasks.scheduler import start_scheduler

from app.api.routers.health import router as health_router
from app.api.routers.upload import router as upload_router
from app.api.routers.map import router as map_router
from app.api.routers.ap import router as ap_router
from app.api.routers.admin import router as admin_router
from app.api.routers.floor_polygon import router as floor_polygon_router
from app.api.routers.access_point import router as access_point_admin_router
from app.api.routers.poi import router as poi_router

app = FastAPI(
    title="Navigation API",
    version="1.0.0"
)

# CORS (разреши свой фронт если нужно)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    start_scheduler()

# Подключаем роутеры
app.include_router(health_router, tags=["health"])
app.include_router(upload_router, tags=["upload"])
app.include_router(map_router, tags=["map"])
app.include_router(ap_router, tags=["access_points"])
app.include_router(admin_router, tags=["admin"])
app.include_router(floor_polygon_router, tags=["floor_polygon"])
app.include_router(access_point_admin_router, tags=["access_point_admin"])
app.include_router(poi_router, tags=["poi"])

@app.get("/v1/health-db", tags=["health"])
async def health_db(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(text("SELECT 1"))
    return {"db_ok": bool(result.scalar())}
