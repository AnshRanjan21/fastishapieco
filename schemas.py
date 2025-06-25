# schemas.py
from pydantic import BaseModel, conint
from datetime import datetime

class SensorReadingIn(BaseModel):
    sensor_id: int
    lux: int
    people: bool

class SensorReadingOut(SensorReadingIn):
    id: int
    ts: datetime

    class Config:
        orm_mode = True

class BrightnessOut(BaseModel):
    led_id: int
    level: int