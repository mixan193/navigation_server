from typing import List, Optional
from pydantic import BaseModel, Field, constr, conint, confloat


class WiFiObservation(BaseModel):
    ssid: str = Field(..., example="MyWiFiNetwork")
    bssid: constr(regex=r"^([0-9A-Fa-f]{2}:){5}([0-9A-Fa-f]{2})$") = Field(..., example="AA:BB:CC:DD:EE:FF")
    rssi: conint(le=0) = Field(..., example=-45)
    frequency: Optional[int] = Field(None, example=2412)


class ScanUpload(BaseModel):
    building_id: int = Field(..., example=1)
    floor: int = Field(..., example=2)
    x: Optional[confloat(ge=0)] = Field(None, example=12.34)
    y: Optional[confloat(ge=0)] = Field(None, example=56.78)
    z: Optional[confloat(ge=0)] = Field(None, example=3.0)
    yaw: Optional[float] = Field(None, example=90.0)
    pitch: Optional[float] = Field(None, example=0.0)
    roll: Optional[float] = Field(None, example=0.0)
    observations: List[WiFiObservation]
