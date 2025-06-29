# main.py
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from database import SessionLocal, engine, get_db # create_engine code lives in database.py
import models, schemas
from fastapi.middleware.cors import CORSMiddleware
from led_routers import router as led_router

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Adaptive Lighting API", version="1.0")
app.include_router(led_router)

# allow Streamlit (localhost:8501) to call the API during dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- brightness algorithm ------------------------------------------------
def calculate_level(lux: int, people: bool) -> int:
    """Very simple rule-based example. Tune to your needs."""
    if not people:
        return 0            # room empty → lights off
    if lux >= 600:
        return 10
    if lux >= 400:
        return 40
    if lux >= 200:
        return 70
    return 100

def persist_brightness(db: Session, led_ids: list[int], level: int):
    for led_id in led_ids:
        db.add(models.BrightnessLevel(led_id=led_id, level=level))
    db.commit()

# --- endpoints -----------------------------------------------------------
@app.get("/", status_code=200)
def home():
    return {"message" : "Hello world!"}

@app.post("/readings", response_model=schemas.SensorReadingOut, status_code=201)
def ingest_reading(
    data: schemas.SensorReadingIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # 1 store the raw reading
    reading = models.SensorReading(**data.model_dump())
    db.add(reading)
    db.commit()
    db.refresh(reading)

    # 2 find LEDs linked to this sensor
    led_rows = (
        db.query(models.Led.id)
        .join(models.sensor_led_map)
        .filter(models.sensor_led_map.c.sensor_id == data.sensor_id)
        .all()
    )
    led_ids = [row.id for row in led_rows]

    # 3 compute brightness and schedule persistence
    level = calculate_level(data.lux, data.people)
    background_tasks.add_task(persist_brightness, db, led_ids, level)

    # 4 (optional) trigger the actual hardware update here, e.g. via MQTT

    return reading
