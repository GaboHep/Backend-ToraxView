from pydantic import BaseModel
from typing import Optional
from datetime import date

class UserLogin(BaseModel):
    username: str
    password: str


class RadiologoBase(BaseModel):
    username: str

class RadiologoCreate(RadiologoBase):
    password: str

class RadiologoUpdate(BaseModel):
    username: str
    password: str

class RadiologoOut(RadiologoBase):
    id: int

    class Config:
        orm_mode = True

##Registros de inferencia / resultados
class RegistroCreate(BaseModel):
    key: str
    inference_date: date
    birth_date: date
    gender: str
    city: str
    parish: str
    canton: str
    precision: float
    resultados: str  # JSON.stringify en el frontend
    feedback: str
    image: str       # base64