from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AccessPointOut(BaseModel):
    id: int = Field(..., description="Первичный ключ точки доступа")
    bssid: str = Field(..., description="MAC-адрес (BSSID)")
    ssid: Optional[str] = Field(None, description="SSID сети")
    building_id: int = Field(..., description="ID здания, к которому привязан AP")
    floor: int = Field(..., description="Этаж, где находится AP")
    x: float = Field(..., description="X-координата в локальной системе (м)")
    y: float = Field(..., description="Y-координата в локальной системе (м)")
    z: Optional[float] = Field(None, description="Z-координата (высота) в локальной системе (м)")
    created_at: datetime = Field(..., description="Время создания записи")

    class Config:
        orm_mode = True