from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.db.base import Base

class WiFiSnapshot(Base):
    __tablename__ = "wifi_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(Integer, ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False)
    floor = Column(Integer, nullable=False)
    x = Column(Float, nullable=True)
    y = Column(Float, nullable=True)
    z = Column(Float, nullable=True)
    yaw = Column(Float, nullable=True)
    pitch = Column(Float, nullable=True)
    roll = Column(Float, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    accuracy = Column(Float, nullable=True)

    building = relationship("Building", back_populates="wifi_snapshots")
    observations = relationship("WiFiObs", back_populates="snapshot", cascade="all, delete-orphan")
    user = relationship("User", back_populates="wifi_snapshots")
