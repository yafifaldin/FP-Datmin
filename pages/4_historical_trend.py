import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pathlib import Path

from utils.fetch_data import get_cached_historical
from utils.clean_data import merge_historical_feeds
from utils.scoring import add_risk_score

st.set_page_config(
    page_title="Historical Trends · Earth's Threat Monitor",
    page_icon="📈",
    layout="wide",
)

css_path = Path(__file__).parent.parent / "assets" / "style.css"
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)

st.markdown(
    """
    <div class="page-title">Historical Trends</div>
    <div class="page-subtitle">
        Long-term close approach patterns, size distributions, and monthly statistics
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Load historical data ───────────────────────────────────────────────────────
@st.cache_data(ttl=86400, show_spinner="Loading historical data (this may take a moment)...")
def load_historical() -> pd.DataFrame:
    raw_list = get_cached_historical(months=6)
    df = merge_historical_feeds(raw_list)
    if not df.empty:
        df = add_risk_score(df)
    return df

try:
    df = load_historical()
except Exception as e:
    st.error(f"Failed to load historical data: {e}")
    st.stop()

if df.empty:
    st.warning("No historical data available. Check your API key and network connection.")
    st.stop()

df["year_month"] = df["date"].dt.to_period("M").astype(str)

# ── Monthly metric cards ───────────────────────────────────────────────────────
total_months = df["year_month"].nunique()
avg_monthly = len(df) / max(total_months, 1)
close_count = (df["miss_distance_ld"] < 10).sum()
avg_diam = df["diameter_km"].mean()

c1, c2, c3, c4 = st.columns(4, gap="medium")
with c1:
    st.markdown(
        f"""
        <div class="metric-card metric-grad-1">
            <div class="metric-label">📅 MONTHS TRACKED</div>
            <div class="metric-value">{total_months}</div>
            <div class="metric-sub">Historical windows</div>
        </div>
        """, unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        f"""
        <div class="metric-card metric-grad-3">
            <div class="metric-label">☄️ AVG MONTHLY NEOs</div>
            <div class="metric-value">{avg_monthly:.1f}</div>
            <div class="metric-sub">Approaches per month</div>
        </div>
        """, unsafe_allow_html=True,
    )
with c3:
    st.markdown(
        f"""
        <div class="metric-card metric-grad-2">
            <div class="metric-label">🌙 CLOSE PASSES (&lt;10 LD)</div>
            <div class="metric-value">{close_count}</div>
            <div class="metric-sub">Total close approaches</div>
        </div>
        """, unsafe_allow_html=True,
    )
with c4:
    st.markdown(
        f"""
        <div class="metric-card metric-grad-4">
            <div class="metric-label">📏 AVG DIAMETER (km)</div>
            <div class="metric-value">{avg_diam:.4f}</div>
            <div class="metric-sub">Mean estimated size</div>
        </div>
        """, unsafe_allow_html=True,
    )

st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

# ── Line chart: monthly avg miss distance ──────────────────────────────────────
st.markdown('<div class="section-title">Monthly Average Miss Distance (AU)</div>', unsafe_allow_html=True)

monthly_miss = (
    df.groupby("year_month")["miss_distance_au"]
    .mean()
    .reset_index()
    .sort_values("year_month")
)

fig_line = go.Figure()
fig_line.add_trace(go.Scatter(
    x=monthly_miss["year_month"],
    y=monthly_miss["miss_distance_au"],
    mode="lines+markers",
    line=dict(color="#00d4ff", width=2.5, shape="spline", smoothing=1.2),
    fill="tozeroy",
    fillcolor="rgba(0,212,255,0.12)",
    marker=dict(color="#00d4ff", size=7, line=dict(color="#0f0f1a", width=1.5)),
    hovertemplate="<b>%{x}</b><br>Avg Miss Distance: %{y:.4f} AU<extra></extra>",
    name="Avg Miss Distance",
))
fig_line.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#ffffff"),
    xaxis=dict(
        showgrid=False,
        tickfont=dict(color="#8892b0"),
        tickangle=-30,
    ),
    yaxis=dict(
        title="Miss Distance (AU)",
        gridcolor="#2a2a4a",
        tickfont=dict(color="#8892b0"),
    ),
    margin=dict(l=0, r=0, t=20, b=0),
    height=320,
)
st.plotly_chart(fig_line, use_container_width=True)

# ── Histogram: diameter distribution (log scale) ───────────────────────────────
st.markdown('<div class="section-title">Diameter Distribution (log scale)</div>', unsafe_allow_html=True)

diam_pos = df.loc[df["diameter_km"] > 0, "diameter_km"]
log_diam = np.log10(diam_pos)
bins = np.linspace(log_diam.min(), log_diam.max(), 30)
counts, edges = np.histogram(log_diam, bins=bins)

bin_colors = [
    f"rgba({int(124 + (224-124) * i / max(len(counts)-1, 1))}, "
    f"{int(58 + (64-58) * i / max(len(counts)-1, 1))}, "
    f"{int(237 - (237-251) * i / max(len(counts)-1, 1))}, 0.85)"
    for i in range(len(counts))
]

fig_hist = go.Figure(
    go.Bar(
        x=[(edges[i] + edges[i+1]) / 2 for i in range(len(edges)-1)],
        y=counts,
        width=[(edges[i+1] - edges[i]) * 0.9 for i in range(len(edges)-1)],
        marker=dict(color=bin_colors),
        hovertemplate="log₁₀(D): %{x:.2f}<br>Count: %{y}<extra></extra>",
    )
)
fig_hist.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#ffffff"),
    xaxis=dict(
        title="log₁₀(Diameter km)",
        gridcolor="#2a2a4a",
        tickfont=dict(color="#8892b0"),
    ),
    yaxis=dict(
        title="Count",
        gridcolor="#2a2a4a",
        tickfont=dict(color="#8892b0"),
    ),
    margin=dict(l=0, r=0, t=10, b=0),
    height=300,
)
st.plotly_chart(fig_hist, use_container_width=True)

# ── Bar chart: monthly close approaches < 10 LD ────────────────────────────────
st.markdown('<div class="section-title">Monthly Close Approaches (&lt; 10 Lunar Distances)</div>', unsafe_allow_html=True)

close_df = df[df["miss_distance_ld"] < 10]
monthly_close = (
    close_df.groupby("year_month")
    .size()
    .reset_index(name="count")
    .sort_values("year_month")
)

fig_close = go.Figure(
    go.Bar(
        x=monthly_close["year_month"],
        y=monthly_close["count"],
        marker_color="#06b6d4",
        opacity=0.85,
        text=monthly_close["count"],
        textposition="outside",
        textfont=dict(color="#ffffff", size=11),
        hovertemplate="<b>%{x}</b><br>Close Approaches: %{y}<extra></extra>",
    )
)
fig_close.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#ffffff"),
    xaxis=dict(
        showgrid=False,
        tickfont=dict(color="#8892b0"),
        tickangle=-30,
    ),
    yaxis=dict(
        title="Number of Close Approaches",
        gridcolor="#2a2a4a",
        tickfont=dict(color="#8892b0"),
    ),
    margin=dict(l=0, r=0, t=20, b=40),
    height=320,
)
st.plotly_chart(fig_close, use_container_width=True)

# ── Summary table ──────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Monthly Summary Statistics</div>', unsafe_allow_html=True)

summary = (
    df.groupby("year_month")
    .agg(
        total=("name", "count"),
        hazardous=("is_hazardous", "sum"),
        avg_velocity=("velocity_kms", "mean"),
        avg_miss_au=("miss_distance_au", "mean"),
        min_miss_ld=("miss_distance_ld", "min"),
    )
    .reset_index()
    .sort_values("year_month", ascending=False)
    .rename(columns={
        "year_month": "Month",
        "total": "Total NEOs",
        "hazardous": "Hazardous",
        "avg_velocity": "Avg Velocity (km/s)",
        "avg_miss_au": "Avg Miss Dist (AU)",
        "min_miss_ld": "Min Miss Dist (LD)",
    })
)
summary["Avg Velocity (km/s)"] = summary["Avg Velocity (km/s)"].round(2)
summary["Avg Miss Dist (AU)"] = summary["Avg Miss Dist (AU)"].round(5)
summary["Min Miss Dist (LD)"] = summary["Min Miss Dist (LD)"].round(3)

st.dataframe(summary, use_container_width=True, height=320)
