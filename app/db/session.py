from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Создаём асинхронный движок SQLAlchemy.
# future=True включает поведение SQLAlchemy 2.0
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,        # в продакшне обычно отключаем эхо SQL
    future=True
)

# factory для получения сессий AsyncSession
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # не сбрасывать объекты после коммита, если нужны для дальнейшего чтения
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Зависимость FastAPI для получения сессии БД.
    Используйте в роутерах так:
        async def some_endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        yield session