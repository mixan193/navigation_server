from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(150), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_superuser = Column(Integer, nullable=False, default=0)  # 0/1 для совместимости
    is_active = Column(Integer, nullable=False, default=1)

    wifi_snapshots = relationship("WiFiSnapshot", back_populates="user")
