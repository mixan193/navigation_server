from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.db.base import Base

class POI(Base):
    __tablename__ = "pois"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(Integer, ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False)
    floor = Column(Integer, nullable=False)
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    z = Column(Float, nullable=True)
    type = Column(String(32), nullable=False, comment="Тип POI: вход, выход, лифт, лестница, туалет, и т.д.")
    name = Column(String(255), nullable=True, comment="Название/описание точки интереса")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    building = relationship("Building", back_populates="pois")
