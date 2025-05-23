from sqlalchemy import Column, Integer, String, DateTime, Float, func, BigInteger
from sqlalchemy.orm import relationship
from app.db.base import Base

class Building(Base):
    __tablename__ = "buildings"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    osm_id = Column(BigInteger, unique=True, nullable=True, comment="OSM building id")
    address = Column(String(255), nullable=True)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    floor_polygons = relationship("FloorPolygon", back_populates="building", cascade="all, delete-orphan")
    access_points = relationship("AccessPoint", back_populates="building", cascade="all, delete-orphan")
    wifi_snapshots = relationship("WiFiSnapshot", back_populates="building", cascade="all, delete-orphan")
    pois = relationship("POI", back_populates="building", cascade="all, delete-orphan")
