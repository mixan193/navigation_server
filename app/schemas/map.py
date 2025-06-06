from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from app.schemas.ap import AccessPointOut


class FloorSchema(BaseModel):
    floor: int = Field(..., description="Номер этажа")
    polygon: List[List[float]] = Field(
        ...,
        description="Список 3D-точек [[x, y, z], …] для контура этажа"
    )
    access_points: List[AccessPointOut] = Field(
        ..., description="Список точек доступа на данном этаже"
    )

    class Config:
        orm_mode = True


class MapResponse(BaseModel):
    building_id: int = Field(..., description="ID здания")
    building_name: str = Field(..., description="Название здания")
    address: str = Field(..., description="Адрес или описание здания")
    lat: Optional[float] = Field(None, description="Широта центра здания")
    lon: Optional[float] = Field(None, description="Долгота центра здания")
    floors: List[FloorSchema] = Field(..., description="Данные по каждому этажу")

    class Config:
        orm_mode = True


class FloorPolygonBase(BaseModel):
    building_id: int = Field(..., description="ID здания")
    floor: int = Field(..., description="Номер этажа")
    polygon: list[list[float]] = Field(..., description="Список 3D-точек [[x, y, z], …] для контура этажа")


class FloorPolygonCreate(FloorPolygonBase):
    pass


class FloorPolygonUpdate(BaseModel):
    polygon: list[list[float]] = Field(..., description="Обновлённый список 3D-точек для этажа")


class FloorPolygonOut(FloorPolygonBase):
    id: int
    created_at: str

    class Config:
        orm_mode = True


class POIBase(BaseModel):
    building_id: int = Field(..., description="ID здания")
    floor: int = Field(..., description="Этаж")
    x: float = Field(..., description="X-координата (м)")
    y: float = Field(..., description="Y-координата (м)")
    z: Optional[float] = Field(None, description="Z-координата (м)")
    type: str = Field(..., description="Тип POI: вход, выход, лифт, лестница и т.д.")
    name: Optional[str] = Field(None, description="Название/описание точки интереса")


class POICreate(POIBase):
    pass


class POIUpdate(BaseModel):
    floor: Optional[int] = None
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    type: Optional[str] = None
    name: Optional[str] = None


class POIOut(POIBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


class RoutePoint(BaseModel):
    x: float
    y: float
    z: float
    floor: int


class RouteResponse(BaseModel):
    id: str
    points: list[RoutePoint]
    length: float
    floor_from: int
    floor_to: int