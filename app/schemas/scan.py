from typing import List, Optional
from pydantic import BaseModel, Field


class WiFiObservation(BaseModel):
    ssid: str = Field(..., description="SSID сети, обнаруженной в скане")
    bssid: str = Field(..., description="MAC-адрес точки доступа")
    rssi: int = Field(..., description="Уровень сигнала (dBm)")
    frequency: Optional[int] = Field(None, description="Частота (MHz)")

    class Config:
        orm_mode = True


class ScanUpload(BaseModel):
    building_id: int = Field(..., description="ID здания, в котором сделан скан")
    floor: int = Field(..., description="Номер этажа")
    yaw: Optional[float] = Field(
        None, description="Поворот вокруг вертикальной оси (Z) в градусах"
    )
    pitch: Optional[float] = Field(
        None, description="Наклон вокруг боковой оси (X) в градусах"
    )
    roll: Optional[float] = Field(
        None, description="Наклон вокруг продольной оси (Y) в градусах"
    )
    observations: List[WiFiObservation] = Field(
        ..., description="Список наблюдений по каждой сети в скане"
    )


class ScanResponse(BaseModel):
    snapshot_id: int = Field(..., description="ID созданного снимка скана Wi-Fi")

    class Config:
        orm_mode = True