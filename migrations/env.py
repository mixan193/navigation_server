from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

import sys
import os

# Добавляем путь к проекту
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app')))

from app.db.base import Base  # База метаданных
from app.db import models     # ИМПОРТ ВСЕХ МОДЕЛЕЙ для Alembic

from app.core.config import settings

# This is the Alembic Config object
config = context.config

# Указываем URL подключения
config.set_main_option('sqlalchemy.url', str(settings.DATABASE_URL))

# Interpret the config file for Python logging.
fileConfig(config.config_file_name)

# Metadata
target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,  # Обязательно для автогенерации изменения типов
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # Обязательно для отслеживания типов
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
