# led_dashboard.py
"""
Streamlit dashboard that calls a FastAPI backend to show
24-hour brightness history for any LED fixture, plus a Cost-savings page.
"""

import streamlit as st
import pandas as pd
import httpx
from datetime import datetime, timezone


# --------------------------------------------------------------------
# Configuration – change for your deployment
# --------------------------------------------------------------------
API_BASE = "http://localhost:8000/api"         # FastAPI base url
HISTORY_WINDOW_H = 24                          # hours of data to plot
REQUEST_TIMEOUT  = 15.0                        # seconds
# --------------------------------------------------------------------

# ---------- helper functions ----------------------------------------
@st.cache_data(ttl=3000)
def fetch_led_list() -> dict[int, str]:
    """Return {led_id: 'LED 3 – 18.75 W', …} for dropdown."""
    resp = httpx.get(f"{API_BASE}/leds", timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    return {row["id"]: f"LED {row['id']} – {row['wattage']} W" for row in data}

@st.cache_data(ttl=30)
def fetch_history_df(led_id: int, hours: int = HISTORY_WINDOW_H) -> pd.DataFrame:
    """Return a DataFrame indexed by ts with a 'level' column."""
    resp = httpx.get(
        f"{API_BASE}/leds/{led_id}/history",
        params={"hours": hours},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    rows = resp.json()                         # [{ts: "...", level: 40}, …]
    if not rows:
        return pd.DataFrame([], columns=["ts", "level"]).set_index("ts")

    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["ts"])
    return df.set_index("ts").sort_index()

def override_brightness(led_id: int, level: int) -> bool:
    """
    POST /api/override_brightness
    """
    try:
        r = httpx.post(
            f"{API_BASE}/override_brightness",
            json={"led_id": led_id, "level": level},
            timeout=REQUEST_TIMEOUT,
        )
        return r.status_code == 201      # created
    except httpx.RequestError:
        return False


# --------------------------------------------------------------------
# Page renderers
# --------------------------------------------------------------------

from datetime import datetime, timezone
import streamlit as st

def render_home() -> None:
    st.title("💡 LED Brightness – 24 h Trend")

    # ──────────────────────────────────────────────────────────────
    # 1️⃣  Fixture selector
    # ──────────────────────────────────────────────────────────────
    led_lookup = fetch_led_list()
    if not led_lookup:
        st.error("No LEDs returned by the API.")
        return

    selected_id = st.selectbox(
        "Select a fixture",
        options=list(led_lookup.keys()),
        format_func=led_lookup.get,
    )

    # ──────────────────────────────────────────────────────────────
    # 2️⃣  Data fetch + placeholders
    # ──────────────────────────────────────────────────────────────
    hist_df   = fetch_history_df(selected_id)
    latest_ts = hist_df.index[-1].to_pydatetime() if not hist_df.empty else None
    latest_lv = int(hist_df["level"].iloc[-1])    if not hist_df.empty else None

    metric_ph = st.empty()      # KPI placeholder
    chart_ph  = st.empty()      # Chart placeholder (needs to be defined early!)

    # ──────────────────────────────────────────────────────────────
    # 3️⃣  KPI + Manual override (side-by-side)
    # ──────────────────────────────────────────────────────────────
    col_kpi, col_ctrl = st.columns([1, 2])   # 1/3 + 2/3 width

    with col_kpi:
        metric_ph.metric(
            label="Current brightness",
            value=f"{latest_lv} %" if latest_lv is not None else "—",
        )

    with col_ctrl:
        st.markdown("**Manual override**")
        new_level = st.slider(
            "Brightness (%)",
            min_value=0,
            max_value=100,
            value=latest_lv or 50,
            step=1,
            key="override_slider",
            label_visibility="collapsed",
        )
        if st.button("Apply", key="override_apply"):
            if override_brightness(selected_id, new_level):
                st.success(f"Brightness set to {new_level}%")

                # live KPI refresh
                metric_ph.metric("Current brightness", f"{new_level} %")

                # update chart (optimistic append)
                if not hist_df.empty:
                    hist_df.loc[datetime.utcnow()] = new_level
                    chart_ph.line_chart(hist_df["level"])
            else:
                st.error("Failed to apply override")

    # ──────────────────────────────────────────────────────────────
    # 4️⃣  24-hour chart (initial render)
    # ──────────────────────────────────────────────────────────────
    if hist_df.empty:
        st.info("No brightness records for the past 24 hours.")
    else:
        chart_ph.line_chart(hist_df["level"])

    # ──────────────────────────────────────────────────────────────
    # 5️⃣  Footer
    # ──────────────────────────────────────────────────────────────
    st.caption(
        f"Data window: last {HISTORY_WINDOW_H} h · "
        f"Updated {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}"
    )

def render_cost_savings() -> None:
    """Placeholder cost-savings analytics page."""
    st.title("💰 Cost Savings Overview")

    st.markdown(
        """
        | Metric | Last 30 days |
        |--------|-------------:|
        | Energy saved | **143 kWh** |
        | Money saved  | **₹ 1 240** |
        | CO₂ avoided  | **112 kg** |
        """
    )

    sample = pd.DataFrame(
        {
            "Month": ["Apr", "May", "Jun", "Jul"],
            "₹ Saved": [410, 515, 620, 705],
        }
    ).set_index("Month")
    st.bar_chart(sample)

# --------------------------------------------------------------------
# Main entrypoint
# --------------------------------------------------------------------
def main() -> None:
    st.set_page_config(page_title="Adaptive Lighting Dashboard", layout="centered")

    # Sidebar navigation
    st.sidebar.title("🔀 Navigation")
    page = st.sidebar.radio("Jump to:", ["Home", "Cost savings"], index=0)

    # Route to selected page
    if page == "Home":
        render_home()
    else:
        render_cost_savings()

# Run immediately when Streamlit executes the file
if __name__ == "__main__":
    main()
