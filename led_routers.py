# api/led_routes.py  – actual endpoints
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import schemas as s
import models                   # your SQLAlchemy models
#import api.schemas as s                    # the file above
# from main import get_db                # SessionLocal dependency
from database import get_db


router = APIRouter(prefix="/api", tags=["leds"])

# ──────────────────────────────────────────────────────────────
@router.get("/leds", response_model=list[s.LedOut])
def list_leds(db: Session = Depends(get_db)):
    """
    Return every LED fixture (id + wattage) for the dropdown menu.
    """
    return db.query(models.Led).order_by(models.Led.id).all()

# ──────────────────────────────────────────────────────────────
@router.get("/leds/{led_id}/history", response_model=list[s.BrightnessPoint])
def led_history(
    led_id: int,
    hours: int = Query(24, ge=1, le=168),   # user-tunable, but safe-bounded
    db: Session = Depends(get_db),
):
    """
    Brightness timeline for the past ⧖ *hours*.
    """
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    rows = (
        db.query(models.BrightnessLevel)
          .filter(
              models.BrightnessLevel.led_id == led_id,
              models.BrightnessLevel.ts >= cutoff,
          )
          .order_by(models.BrightnessLevel.ts)
          .all()
    )

    # extra guard: 404 if LED id doesn’t exist at all
    if not rows and not db.query(models.Led.id).filter_by(id=led_id).first():
        raise HTTPException(status_code=404, detail="LED not found")

    return rows
