import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from pathlib import Path

from utils.fetch_data import get_feed
from utils.clean_data import parse_feed
from utils.scoring import add_risk_score

st.set_page_config(
    page_title="Live NEO Feed · Earth's Threat Monitor",
    page_icon="☄️",
    layout="wide",
)

css_path = Path(__file__).parent.parent / "assets" / "style.css"
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)

# ── Date window ────────────────────────────────────────────────────────────────
today = datetime.utcnow().date()
end_dt = today + timedelta(days=6)
start_str = today.isoformat()
end_str = end_dt.isoformat()

st.markdown(
    f"""
    <div class="page-title">Live NEO Feed</div>
    <div class="page-subtitle">
        Near-Earth Objects approaching Earth &nbsp;·&nbsp;
        <span style="color:#00d4ff;">{start_str}</span> →
        <span style="color:#00d4ff;">{end_str}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Fetch data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner="Fetching NEO data from NASA...")
def load_feed(start: str, end: str) -> pd.DataFrame:
    raw = get_feed(start, end)
    df = parse_feed(raw)
    return add_risk_score(df)

try:
    df = load_feed(start_str, end_str)
except Exception as e:
    st.error(f"Failed to fetch data from NASA API: {e}")
    st.stop()

if df.empty:
    st.warning("No NEO data returned for this date window.")
    st.stop()

# ── Metric cards ───────────────────────────────────────────────────────────────
total = len(df)
hazardous = int(df["is_hazardous"].sum())
fastest = df["velocity_kms"].max()
closest = df["miss_distance_ld"].min()

c1, c2, c3, c4 = st.columns(4, gap="medium")

with c1:
    st.markdown(
        f"""
        <div class="metric-card metric-grad-1">
            <div class="metric-label">☄️ TOTAL NEOs THIS WEEK</div>
            <div class="metric-value">{total}</div>
            <div class="metric-sub">Close approaches detected</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        f"""
        <div class="metric-card metric-grad-2">
            <div class="metric-label">⚠️ HAZARDOUS ASTEROIDS</div>
            <div class="metric-value">{hazardous}</div>
            <div class="metric-sub">Potentially hazardous objects</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c3:
    st.markdown(
        f"""
        <div class="metric-card metric-grad-3">
            <div class="metric-label">🚀 FASTEST (km/s)</div>
            <div class="metric-value">{fastest:.2f}</div>
            <div class="metric-sub">Relative approach velocity</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c4:
    st.markdown(
        f"""
        <div class="metric-card metric-grad-4">
            <div class="metric-label">🌙 CLOSEST (Lunar Distance)</div>
            <div class="metric-value">{closest:.2f}</div>
            <div class="metric-sub">Lunar distances from Earth</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

# ── Daily count bar chart ──────────────────────────────────────────────────────
st.markdown('<div class="section-title">Daily Approach Count</div>', unsafe_allow_html=True)

daily = df.groupby(df["date"].dt.date).size().reset_index(name="count")
daily.columns = ["date", "count"]

n = len(daily)
colors = [
    f"rgba({int(124 - (124 - 0) * i / max(n - 1, 1))}, "
    f"{int(58 + (212 - 58) * i / max(n - 1, 1))}, "
    f"{int(237 - (237 - 255) * i / max(n - 1, 1))}, 0.9)"
    for i in range(n)
]

fig_bar = go.Figure(
    go.Bar(
        x=daily["date"].astype(str),
        y=daily["count"],
        marker=dict(color=colors, line=dict(color="#2a2a4a", width=0.5)),
        text=daily["count"],
        textposition="outside",
        textfont=dict(color="#ffffff", size=12),
        hovertemplate="<b>%{x}</b><br>Asteroids: %{y}<extra></extra>",
    )
)
fig_bar.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#ffffff", family="sans-serif"),
    xaxis=dict(
        showgrid=False,
        color="#8892b0",
        tickfont=dict(color="#8892b0"),
    ),
    yaxis=dict(
        gridcolor="#2a2a4a",
        color="#8892b0",
        tickfont=dict(color="#8892b0"),
        title="Number of NEOs",
    ),
    margin=dict(l=0, r=0, t=30, b=0),
    height=300,
)
st.plotly_chart(fig_bar, use_container_width=True)

# ── Interactive dataframe ──────────────────────────────────────────────────────
st.markdown('<div class="section-title">Asteroid Close Approach Table</div>', unsafe_allow_html=True)

display_df = df[[
    "name", "date", "diameter_km", "velocity_kms",
    "miss_distance_ld", "is_hazardous", "risk_score"
]].copy()
display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
display_df.columns = [
    "Name", "Date", "Diameter (km)", "Velocity (km/s)",
    "Miss Distance (LD)", "Hazardous", "Risk Score"
]
display_df["Diameter (km)"] = display_df["Diameter (km)"].round(4)
display_df["Velocity (km/s)"] = display_df["Velocity (km/s)"].round(3)
display_df["Miss Distance (LD)"] = display_df["Miss Distance (LD)"].round(3)
display_df["Risk Score"] = display_df["Risk Score"].round(4)

close_mask = df["miss_distance_ld"] < 5

st.markdown(
    """
    <div class="custom-info">
        <strong style="color:#e040fb;">⚠️ Highlight:</strong>
        Rows with <span style="color:#e040fb; font-weight:600;">Miss Distance &lt; 5 LD</span>
        are marked as very close approaches.
    </div>
    """,
    unsafe_allow_html=True,
)

def highlight_close(row):
    if row["Miss Distance (LD)"] < 5:
        return ["background-color: rgba(224,64,251,0.15); color: #ffffff"] * len(row)
    return [""] * len(row)

styled = display_df.style.apply(highlight_close, axis=1)
st.dataframe(styled, use_container_width=True, height=420)
