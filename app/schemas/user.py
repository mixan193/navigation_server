from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str = Field(..., example="john_doe")
    password: str = Field(..., example="supersecret")


class UserOut(BaseModel):
    id: int
    username: str

    class Config:
        orm_mode = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
