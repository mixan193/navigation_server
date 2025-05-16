from sqlalchemy import Column, Integer, String, ForeignKey, Float, Boolean, DateTime, func
from sqlalchemy.orm import relationship
from app.db.base import Base

class AccessPoint(Base):
    __tablename__ = "access_points"

    id = Column(Integer, primary_key=True, index=True)
    bssid = Column(String(32), unique=True, nullable=False)
    ssid = Column(String(255), nullable=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=True)
    floor = Column(Integer, nullable=True)
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    z = Column(Float, nullable=False)
    accuracy = Column(Float, nullable=False, default=9999.0)
    is_mobile = Column(Boolean, default=False, nullable=False)
    last_update = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    building = relationship("Building", back_populates="access_points")
    wifi_obs = relationship("WiFiObs", back_populates="access_point", cascade="all, delete-orphan")
