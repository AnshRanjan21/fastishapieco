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
        from_attributes = True

class BrightnessOut(BaseModel):
    led_id: int
    level: int

class LedOut(BaseModel):
    id: int
    wattage: float          # e.g. 18.75

    class Config:
        from_attributes = True

class BrightnessPoint(BaseModel):
    ts: datetime
    level: int

    class Config:
        from_attributes = True

class BrightnessOverrideIn(BaseModel):
    led_id: int
    level: int