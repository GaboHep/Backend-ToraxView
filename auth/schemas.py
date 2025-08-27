from pydantic import BaseModel, field_validator, model_validator
from typing import Optional, Union, List
from datetime import date
import json, re

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


class RegistroCreate(BaseModel):
    key: str
    inference_date: date
    birth_date: date
    gender: str
    city: str
    parish: str
    # Backend sigue usando 'canton', pero aceptamos 'provincia'
    canton: Optional[str] = None
    provincia: Optional[str] = None

    precision: Optional[float] = 0.0
    resultados: Union[str, List[dict]]
    feedback: str
    image: Optional[str] = None  # acepta DataURL completo

    # --- Mapeo de alias (provincia → canton) ---
    @model_validator(mode="before")
    @classmethod
    def map_aliases(cls, values):
        if isinstance(values, dict):
            if not values.get("canton") and values.get("provincia"):
                values["canton"] = values["provincia"]
        return values

    # --- Validación de precision ---
    @field_validator("precision", mode="before")
    @classmethod
    def precision_default(cls, v):
        if v in (None, "", "null"):
            return 0.0
        return float(v)

    # --- Normalización de resultados ---
    @field_validator("resultados", mode="before")
    @classmethod
    def ensure_resultados_string(cls, v):
        if isinstance(v, list):
            return json.dumps(v, ensure_ascii=False)
        return v