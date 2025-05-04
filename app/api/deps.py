from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.config import settings


# Dependency to get DB session
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency — выдаёт асинхронную сессию SQLAlchemy.
    Используйте в роутерах:
        db: AsyncSession = Depends(get_db_session)
    """
    async for session in get_db():
        yield session