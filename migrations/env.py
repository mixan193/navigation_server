import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from alembic import context

from app.core.config import settings
from app.db.base import Base  # Здесь собираются все ваши модели

# Этот объект содержит конфиг alembic.ini
config = context.config
# Перезаписываем URL на тот, что задаётся в .env
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Логгирование по конфигу из alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# metadata всех моделей для автогенерации миграций
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Запуск миграций в 'offline' режиме: без подключения к БД."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """
    Запуск миграций в 'online' режиме: через реальное соединение.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,  # чтобы отслеживались изменения типов колонок
        render_as_batch=True,  # полезно при изменении схемы в SQLite (в будущем)
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Асинхронный запуск online-миграций через AsyncEngine."""
    connectable: AsyncEngine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=pool.NullPool,
        future=True,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    # Альтернативно можно писать просто: asyncio.run(run_migrations_online())
    asyncio.get_event_loop().run_until_complete(run_migrations_online())