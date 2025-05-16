from typing import List, Optional
from pydantic import BaseModel, Field, constr, conint, confloat

from typing import Annotated
from pydantic import BaseModel, Field

class WiFiObservation(BaseModel):
    ssid: Annotated[str, Field(min_length=1, example="MyWiFiNetwork")]
    bssid: Annotated[str, Field(pattern=r"^([0-9A-Fa-f]{2}:){5}([0-9A-Fa-f]{2})$", example="AA:BB:CC:DD:EE:FF")]
    rssi: Annotated[int, Field(le=0, example=-45)]
    frequency: Annotated[int, Field(ge=2400, le=2500, example=2412)]

class ScanUpload(BaseModel):
    building_id: int = Field(..., example=1)
    floor: int = Field(..., example=2)
    x: Optional[float] = Field(None, example=12.34)
    y: Optional[float] = Field(None, example=56.78)
    z: Optional[float] = Field(None, example=3.0)
    yaw: Optional[float] = Field(None, example=90.0)
    pitch: Optional[float] = Field(None, example=0.0)
    roll: Optional[float] = Field(None, example=0.0)
    lat: Optional[float] = Field(None, example=55.7512)
    lon: Optional[float] = Field(None, example=37.6175)
    accuracy: Optional[float] = Field(None, example=5.0)
    observations: List[WiFiObservation]

class ScanResponseCoordinates(BaseModel):
    building_id: Optional[int] = Field(None, example=1)
    floor: Optional[int] = Field(None, example=2)
    x: Optional[float] = Field(None, example=12.34)
    y: Optional[float] = Field(None, example=56.78)
    z: Optional[float] = Field(None, example=3.0)
    lat: Optional[float] = Field(None, example=55.7512)
    lon: Optional[float] = Field(None, example=37.6175)
    altitude: Optional[float] = Field(None, example=100.0)
    accuracy: Optional[float] = Field(None, example=5.0)

class ScanResponse(BaseModel):
    status: str = Field(..., example="success")
    coordinates: Optional[ScanResponseCoordinates]
