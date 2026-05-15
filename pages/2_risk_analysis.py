import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

from utils.fetch_data import get_feed
from utils.clean_data import parse_feed
from utils.scoring import add_risk_score, add_risk_label

st.set_page_config(
    page_title="Risk Analysis · Earth's Threat Monitor",
    page_icon="⚠️",
    layout="wide",
)

css_path = Path(__file__).parent.parent / "assets" / "style.css"
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)

st.markdown(
    """
    <div class="page-title">Risk Analysis</div>
    <div class="page-subtitle">
        Threat scoring, velocity vs. distance scatter, and top-risk ranking
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Load data ──────────────────────────────────────────────────────────────────
today = datetime.utcnow().date()
end_dt = today + timedelta(days=6)

@st.cache_data(ttl=3600, show_spinner="Loading risk data...")
def load(start: str, end: str) -> pd.DataFrame:
    raw = get_feed(start, end)
    df = parse_feed(raw)
    df = add_risk_score(df)
    df = add_risk_label(df)
    return df

try:
    df = load(today.isoformat(), end_dt.isoformat())
except Exception as e:
    st.error(f"API error: {e}")
    st.stop()

if df.empty:
    st.warning("No data available.")
    st.stop()

# ── Scatter: velocity vs miss distance ─────────────────────────────────────────
st.markdown('<div class="section-title">Velocity vs. Miss Distance</div>', unsafe_allow_html=True)

haz_mask = df["is_hazardous"]
size_scale = (
    (df["diameter_km"] - df["diameter_km"].min()) /
    (df["diameter_km"].max() - df["diameter_km"].min() + 1e-9)
) * 40 + 6

fig_scatter = go.Figure()

fig_scatter.add_trace(go.Scatter(
    x=df.loc[~haz_mask, "miss_distance_au"],
    y=df.loc[~haz_mask, "velocity_kms"],
    mode="markers",
    name="Non-Hazardous",
    marker=dict(
        size=size_scale[~haz_mask],
        color="#00d4ff",
        opacity=0.75,
        line=dict(color="#2a2a4a", width=0.5),
    ),
    text=df.loc[~haz_mask, "name"],
    hovertemplate=(
        "<b>%{text}</b><br>"
        "Miss Distance: %{x:.4f} AU<br>"
        "Velocity: %{y:.2f} km/s<extra></extra>"
    ),
))

fig_scatter.add_trace(go.Scatter(
    x=df.loc[haz_mask, "miss_distance_au"],
    y=df.loc[haz_mask, "velocity_kms"],
    mode="markers",
    name="Hazardous",
    marker=dict(
        size=size_scale[haz_mask],
        color="#e040fb",
        opacity=0.85,
        symbol="diamond",
        line=dict(color="#ffffff", width=0.8),
    ),
    text=df.loc[haz_mask, "name"],
    hovertemplate=(
        "<b>%{text}</b> ⚠️<br>"
        "Miss Distance: %{x:.4f} AU<br>"
        "Velocity: %{y:.2f} km/s<extra></extra>"
    ),
))

fig_scatter.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#ffffff", family="sans-serif"),
    xaxis=dict(
        title="Miss Distance (AU)",
        gridcolor="#2a2a4a",
        color="#8892b0",
        tickfont=dict(color="#8892b0"),
    ),
    yaxis=dict(
        title="Relative Velocity (km/s)",
        gridcolor="#2a2a4a",
        color="#8892b0",
        tickfont=dict(color="#8892b0"),
    ),
    legend=dict(
        bgcolor="rgba(26,26,46,0.8)",
        bordercolor="#2a2a4a",
        borderwidth=1,
        font=dict(color="#ffffff"),
    ),
    margin=dict(l=0, r=0, t=30, b=0),
    height=420,
    annotations=[dict(
        text="Bubble size = diameter",
        xref="paper", yref="paper",
        x=1, y=1.04,
        showarrow=False,
        font=dict(color="#8892b0", size=11),
    )],
)
st.plotly_chart(fig_scatter, use_container_width=True)

# ── Top 15 by risk score ───────────────────────────────────────────────────────
st.markdown('<div class="section-title">Top 15 Asteroids by Risk Score</div>', unsafe_allow_html=True)

top15 = df.nlargest(15, "risk_score")[["name", "risk_score", "is_hazardous"]].copy()
top15 = top15.sort_values("risk_score")

bar_colors = [
    f"rgba(124,58,{int(237 - 237 * i / max(len(top15)-1, 1))}, {0.55 + 0.45 * i / max(len(top15)-1, 1)})"
    for i in range(len(top15))
]

fig_top = go.Figure(
    go.Bar(
        x=top15["risk_score"],
        y=top15["name"],
        orientation="h",
        marker=dict(color=bar_colors),
        text=top15["risk_score"].round(3),
        textposition="outside",
        textfont=dict(color="#ffffff", size=11),
        hovertemplate="<b>%{y}</b><br>Risk Score: %{x:.4f}<extra></extra>",
    )
)
fig_top.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#ffffff", family="sans-serif"),
    xaxis=dict(
        title="Risk Score",
        gridcolor="#2a2a4a",
        tickfont=dict(color="#8892b0"),
    ),
    yaxis=dict(
        tickfont=dict(color="#ffffff", size=11),
        automargin=True,
    ),
    margin=dict(l=0, r=80, t=10, b=0),
    height=max(350, len(top15) * 28),
)
st.plotly_chart(fig_top, use_container_width=True)

# ── Insight box ────────────────────────────────────────────────────────────────
q75 = df["risk_score"].quantile(0.75)
non_haz_high_risk = df[~df["is_hazardous"] & (df["risk_score"] >= q75)]
count_nhhk = len(non_haz_high_risk)

st.markdown(
    f"""
    <div class="custom-info">
        <strong style="color:#e040fb;">🔍 Insight — Top Quartile Risk (non-hazardous)</strong><br>
        <span style="color:#8892b0;">
        <b style="color:#ffffff;">{count_nhhk}</b> non-hazardous asteroid(s) fall in the
        <b style="color:#a78bfa;">top 25% risk score bracket</b> (threshold: {q75:.4f}).
        These objects are not officially classified as hazardous but exhibit high kinetic
        threat potential based on size, velocity, and proximity.
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Risk distribution ──────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Risk Label Distribution</div>', unsafe_allow_html=True)

risk_counts = df["risk_label"].value_counts().reset_index()
risk_counts.columns = ["label", "count"]
label_colors = {"High": "#e040fb", "Medium": "#7c3aed", "Low": "#00d4ff"}

fig_pie = go.Figure(
    go.Pie(
        labels=risk_counts["label"],
        values=risk_counts["count"],
        hole=0.55,
        marker=dict(
            colors=[label_colors.get(l, "#06b6d4") for l in risk_counts["label"]],
            line=dict(color="#0f0f1a", width=2),
        ),
        textfont=dict(color="#ffffff", size=13),
        hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Share: %{percent}<extra></extra>",
    )
)
fig_pie.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#ffffff"),
    legend=dict(font=dict(color="#ffffff"), bgcolor="rgba(0,0,0,0)"),
    margin=dict(l=0, r=0, t=10, b=0),
    height=300,
    annotations=[dict(
        text=f"<b>{len(df)}</b><br>NEOs",
        x=0.5, y=0.5,
        font=dict(size=16, color="#ffffff"),
        showarrow=False,
    )],
)
st.plotly_chart(fig_pie, use_container_width=True)
