# led_dashboard.py
import streamlit as st
from datetime import datetime, timedelta

import pandas as pd
from sqlalchemy.orm import Session

from database import SessionLocal          # same helper you used in FastAPI
import models                              # Sensor, Led, BrightnessLevel, ...

# ---------- helper functions -------------------------------------------------
@st.cache_data(ttl=60)          # re-query at most once a minute
def fetch_led_list() -> dict[int, str]:
    """Return {led_id: friendly name}."""
    with SessionLocal() as db:
        leds = db.query(models.Led).order_by(models.Led.id).all()
        return {led.id: f"LED {led.id} – {led.wattage} W" for led in leds}

@st.cache_data(ttl=30)
def fetch_latest_brightness(led_id: int) -> int | None:
    """Most recent brightness % for the given LED (or None)."""
    with SessionLocal() as db:
        row = (
            db.query(models.BrightnessLevel.level)
              .filter(models.BrightnessLevel.led_id == led_id)
              .order_by(models.BrightnessLevel.ts.desc())
              .first()
        )
        return row[0] if row else None

@st.cache_data(ttl=30)
def fetch_history(led_id: int, hours: int = 24) -> pd.DataFrame:
    """Brightness timeline for the last *hours* (UTC)."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    with SessionLocal() as db:
        rows = (
            db.query(models.BrightnessLevel.ts, models.BrightnessLevel.level)
              .filter(models.BrightnessLevel.led_id == led_id,
                      models.BrightnessLevel.ts >= cutoff)
              .order_by(models.BrightnessLevel.ts)
              .all()
        )
    df = pd.DataFrame(rows, columns=["ts", "level"])
    df["ts"] = pd.to_datetime(df["ts"])          # ensure proper dtype
    return df.set_index("ts")

# ---------- Streamlit layout -------------------------------------------------
st.set_page_config(page_title="LED Brightness Monitor", layout="centered")
st.title("💡 LED Brightness Monitor")

led_lookup = fetch_led_list()
if not led_lookup:
    st.error("No LEDs found in the database.")
    st.stop()

# dropdown
chosen_id = st.selectbox(
    label="Select a fixture",
    options=list(led_lookup.keys()),
    format_func=lambda k: led_lookup[k],
)

# latest value
current_level = fetch_latest_brightness(chosen_id)
col1, col2 = st.columns(2)
with col1:
    st.metric("Current brightness %", current_level if current_level is not None else "—")
with col2:
    st.write("")  # spacer
    st.caption(f"Last update: {datetime.utcnow():%Y-%m-%d %H:%M} UTC")

# history chart
hist_df = fetch_history(chosen_id, hours=24)
if hist_df.empty:
    st.info("No brightness records in the last 24 h.")
else:
    st.markdown("##### 24-hour history")
    st.line_chart(hist_df["level"])
