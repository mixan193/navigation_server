from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class AccessPointBase(BaseModel):
    bssid: str = Field(..., description="MAC-адрес (BSSID)")
    ssid: Optional[str] = Field(None, description="SSID сети")
    building_id: int = Field(..., description="ID здания")
    floor: int = Field(..., description="Этаж")
    x: float = Field(..., description="X-координата (м)")
    y: float = Field(..., description="Y-координата (м)")
    z: float = Field(..., description="Z-координата (м)")
    accuracy: Optional[float] = Field(9999.0, description="Погрешность (м)")
    is_mobile: Optional[bool] = Field(False, description="Мобильная ли точка?")

class AccessPointCreate(AccessPointBase):
    pass

class AccessPointUpdate(BaseModel):
    ssid: Optional[str] = None
    floor: Optional[int] = None
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    accuracy: Optional[float] = None
    is_mobile: Optional[bool] = None

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

class AccessPointAdminOut(AccessPointOut):
    accuracy: float
    is_mobile: bool
    last_update: datetime

    class Config:
        orm_mode = True

class AccessPointListResponse(BaseModel):
    items: List[AccessPointAdminOut] = Field(..., description="Список точек доступа")
    total: int = Field(..., description="Общее количество подходящих точек доступа")
    limit: int = Field(..., description="Лимит на страницу")
    offset: int = Field(..., description="Смещение для пагинации")

    class Config:
        orm_mode = True