# app/api/deps.py

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Зависимость FastAPI, возвращающая асинхронную сессию SQLAlchemy.
    Сессия автоматически открывается при входе в контекст и закрывается по выходу.
    """
    async with AsyncSessionLocal() as session:
        yield session
