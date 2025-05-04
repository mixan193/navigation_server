from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class AccessPoint(Base):
    __tablename__ = "access_points"

    id = Column(Integer, primary_key=True, index=True)
    bssid = Column(String(17), nullable=False, unique=True, index=True, comment="MAC-адрес точек доступа")
    ssid = Column(String(255), nullable=True, comment="SSID сети, к которой принадлежит AP")

    # К какому зданию и этажу привязана точка доступа
    building_id = Column(
        Integer,
        ForeignKey("buildings.id", ondelete="CASCADE"),
        nullable=False
    )
    floor = Column(Integer, nullable=False, comment="Номер этажа")

    # Координаты в локальной системе (метры)
    x = Column(Float, nullable=False, comment="X-координата на плане")
    y = Column(Float, nullable=False, comment="Y-координата на плане")
    z = Column(Float, nullable=True, comment="Z-координата (высота), если есть")

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # ORM-связи
    building = relationship("Building", back_populates="access_points")
    observations = relationship(
        "WiFiObs",
        back_populates="access_point",
        cascade="all, delete-orphan"
    )