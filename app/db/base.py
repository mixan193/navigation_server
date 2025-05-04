from sqlalchemy.ext.declarative import declarative_base

# declarative_base() создаёт класс-основание для всех ORM-моделей.
Base = declarative_base()

# Импорт моделей гарантирует, что Alembic увидит их при автогенерации миграций.
# Если вы добавите новую модель, не забудьте импортировать её здесь.
from app.db.models import (
    building,
    access_point,
    wifi_snapshot,
    wifi_obs,
    floor_polygon,
)