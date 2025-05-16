from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Импорт моделей — чтобы таблицы создавались автоматически
from app.db.models import (
    building,
    access_point,
    wifi_snapshot,
    wifi_obs,
    floor_polygon,
)
