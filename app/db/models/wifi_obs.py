from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship
from app.db.base import Base

class WiFiObs(Base):
    __tablename__ = "wifi_observations"

    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(Integer, ForeignKey("wifi_snapshots.id", ondelete="CASCADE"), nullable=False)
    access_point_id = Column(Integer, ForeignKey("access_points.id", ondelete="SET NULL"), nullable=True)
    ssid = Column(String(255), nullable=False)
    bssid = Column(String(17), nullable=False)
    rssi = Column(Integer, nullable=False)
    frequency = Column(Integer, nullable=True)

    snapshot = relationship("WiFiSnapshot", back_populates="observations")
    access_point = relationship("AccessPoint", back_populates="wifi_obs")
