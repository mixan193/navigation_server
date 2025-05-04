from typing import List
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
    floors: List[FloorSchema] = Field(..., description="Данные по каждому этажу")

    class Config:
        orm_mode = True