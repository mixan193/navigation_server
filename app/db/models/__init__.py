# Пакет моделей базы данных
# Здесь импортируются все модели, чтобы Alembic мог их обнаружить
from .building import Building
from .access_point import AccessPoint
from .wifi_snapshot import WiFiSnapshot
from .wifi_obs import WiFiObs
from .floor_polygon import FloorPolygon
from .user import User
