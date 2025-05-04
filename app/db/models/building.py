from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class Building(Base):
    __tablename__ = "buildings"

    # Первичный ключ
    id = Column(Integer, primary_key=True, index=True)

    # Читаемое имя здания
    name = Column(String(255), nullable=False, unique=True, comment="Уникальное название/идентификатор здания")

    # Адрес или описание
    address = Column(String(255), nullable=True, comment="Адрес или описание здания")

    # Автоматические метки времени
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Когда запись была создана"
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Когда запись была обновлена"
    )

    # Связи: полигон этажей и точки доступа
    floor_polygons = relationship(
        "FloorPolygon",
        back_populates="building",
        cascade="all, delete-orphan"
    )
    access_points = relationship(
        "AccessPoint",
        back_populates="building",
        cascade="all, delete-orphan"
    )
    wifi_snapshots = relationship(
        "WiFiSnapshot",
        back_populates="building",
        cascade="all, delete-orphan"
    )