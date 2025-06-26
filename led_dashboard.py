# led_dashboard.py
"""
Streamlit dashboard that calls a FastAPI backend to show
24-hour brightness history for any LED fixture, plus a Cost-savings page.
"""

import streamlit as st
import pandas as pd
import httpx
from datetime import datetime

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

# --------------------------------------------------------------------
# Page renderers
# --------------------------------------------------------------------
def render_home() -> None:
    """Brightness trend page (existing UI)."""
    st.title("💡 LED Brightness – 24 h Trend")

    led_lookup = fetch_led_list()
    if not led_lookup:
        st.error("No LEDs returned by the API.")
        return

    selected_id = st.selectbox(
        "Select a fixture",
        options=list(led_lookup.keys()),
        format_func=led_lookup.get,
    )

    hist_df = fetch_history_df(selected_id)

    if hist_df.empty:
        st.info("No brightness records for the past 24 hours.")
    else:
        st.line_chart(hist_df["level"])
        latest_ts = hist_df.index[-1].to_pydatetime()
        latest_lvl = hist_df["level"].iloc[-1]
        st.caption(
            f"Last change: {latest_lvl}% at "
            f"{latest_ts.strftime('%Y-%m-%d %H:%M UTC')}"
        )

    st.markdown("---")
    st.caption(
        f"Data window: last {HISTORY_WINDOW_H} h &nbsp;|&nbsp; "
        f"Updated {datetime.utcnow():%Y-%m-%d %H:%M UTC}"
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
