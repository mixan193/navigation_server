from sqlalchemy import Column, Integer, ForeignKey, JSON, DateTime, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class FloorPolygon(Base):
    __tablename__ = "floor_polygons"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(
        Integer,
        ForeignKey("buildings.id", ondelete="CASCADE"),
        nullable=False
    )
    floor = Column(Integer, nullable=False, comment="Этаж, к которому привязан полигон")

    polygon = Column(
        JSON,
        nullable=False,
        comment="Список 3D-координат точек [[x, y, z], …] для карты этажа"
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    building = relationship("Building", back_populates="floor_polygons")