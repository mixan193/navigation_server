from sqlalchemy import Column, Integer, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class WiFiSnapshot(Base):
    __tablename__ = "wifi_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(
        Integer,
        ForeignKey("buildings.id", ondelete="CASCADE"),
        nullable=False
    )
    floor = Column(Integer, nullable=False, comment="Этаж, на котором сделан снимок")

    # Ориентация устройства в трёхмерном пространстве (градусы)
    yaw = Column(Float, nullable=True, comment="Поворот вокруг вертикальной оси (Z) — yaw")
    pitch = Column(Float, nullable=True, comment="Наклон вокруг боковой оси (X) — pitch")
    roll = Column(Float, nullable=True, comment="Наклон вокруг продольной оси (Y) — roll")

    timestamp = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Время получения снимка"
    )

    # ORM-связи
    building = relationship("Building", back_populates="wifi_snapshots")
    observations = relationship(
        "WiFiObs",
        back_populates="snapshot",
        cascade="all, delete-orphan"
    )