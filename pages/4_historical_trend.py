import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pathlib import Path

from utils.fetch_data import get_cached_historical
from utils.clean_data import merge_historical_feeds
from utils.scoring import add_risk_score

def _inject_css():
    p = Path(__file__).parent.parent / "assets" / "style.css"
    if p.exists():
        with open(p, encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

_inject_css()

st.markdown("""
<p class="page-eyebrow">Earth's Threat Monitor  ·  04</p>
<h1 class="page-title">Historical Trends</h1>
<p class="page-subtitle">
    Six months of close approach frequency, miss distance patterns,
    and asteroid size distribution.
</p>
""", unsafe_allow_html=True)

@st.cache_data(ttl=86400, show_spinner="Loading historical data - this may take a moment...")
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

total_months = df["year_month"].nunique()
avg_monthly  = len(df) / max(total_months, 1)
close_count  = int((df["miss_distance_ld"] < 10).sum())
avg_diam     = df["diameter_km"].mean()

# ── Stat cards ─────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4, gap="medium")

with c1:
    st.markdown(f"""
    <div class="stat-card" style="--acc:#00d4ff">
        <div class="stat-label">Months tracked</div>
        <div class="stat-num">{total_months}</div>
        <div class="stat-desc">historical windows</div>
    </div>
    """, unsafe_allow_html=True)
with c2:
    st.markdown(f"""
    <div class="stat-card" style="--acc:#a78bfa">
        <div class="stat-label">Avg NEOs / month</div>
        <div class="stat-num">{avg_monthly:.1f}</div>
        <div class="stat-desc">close approaches per month</div>
    </div>
    """, unsafe_allow_html=True)
with c3:
    st.markdown(f"""
    <div class="stat-card" style="--acc:#e040fb">
        <div class="stat-label">Close passes (< 10 LD)</div>
        <div class="stat-num">{close_count}</div>
        <div class="stat-desc">total very close approaches</div>
    </div>
    """, unsafe_allow_html=True)
with c4:
    st.markdown(f"""
    <div class="stat-card" style="--acc:#06b6d4">
        <div class="stat-label">Avg diameter (km)</div>
        <div class="stat-num">{avg_diam:.4f}</div>
        <div class="stat-desc">mean estimated size</div>
    </div>
    """, unsafe_allow_html=True)

# ── Line chart ─────────────────────────────────────────────────────────────────
st.markdown('<p class="section-label">Monthly average miss distance (AU)</p>', unsafe_allow_html=True)

monthly_miss = (
    df.groupby("year_month")["miss_distance_au"]
    .mean().reset_index().sort_values("year_month")
)
min_idx = monthly_miss["miss_distance_au"].idxmin()

fig_line = go.Figure()
fig_line.add_trace(go.Scatter(
    x=monthly_miss["year_month"],
    y=monthly_miss["miss_distance_au"],
    mode="lines+markers",
    line=dict(color="#00d4ff", width=2, shape="spline", smoothing=1.1),
    fill="tozeroy", fillcolor="rgba(0,212,255,0.06)",
    marker=dict(color="#00d4ff", size=5, line=dict(color="#0d0d1f", width=2)),
    hovertemplate="<b>%{x}</b><br>%{y:.4f} AU<extra></extra>",
))
fig_line.add_annotation(
    x=monthly_miss.loc[min_idx, "year_month"],
    y=monthly_miss.loc[min_idx, "miss_distance_au"],
    text=f"  closest avg · {monthly_miss.loc[min_idx, 'miss_distance_au']:.4f} AU",
    showarrow=False, yanchor="top",
    font=dict(color="#00d4ff", size=10),
)
fig_line.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#ffffff", family="sans-serif", size=11),
    xaxis=dict(showgrid=False, tickfont=dict(color="#ffffff"), tickangle=-30),
    yaxis=dict(title="AU", gridcolor="#161630",
               tickfont=dict(color="#ffffff"), zeroline=False),
    margin=dict(l=0, r=0, t=20, b=0),
    height=300,
)
st.plotly_chart(fig_line, use_container_width=True)

# ── Histogram ──────────────────────────────────────────────────────────────────
st.markdown('<p class="section-label">Diameter distribution (log scale)</p>', unsafe_allow_html=True)

diam_pos = df.loc[df["diameter_km"] > 0, "diameter_km"]
log_diam  = np.log10(diam_pos)
counts, edges = np.histogram(log_diam, bins=28)

fig_hist = go.Figure(go.Bar(
    x=[(edges[i] + edges[i+1]) / 2 for i in range(len(edges)-1)],
    y=counts,
    width=[(edges[i+1] - edges[i]) * 0.88 for i in range(len(edges)-1)],
    marker=dict(color="#7c3aed", opacity=0.6,
                line=dict(color="rgba(0,0,0,0)", width=0)),
    hovertemplate="log10(D) approx %{x:.2f}<br>Count: %{y}<extra></extra>",
))
fig_hist.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#ffffff", family="sans-serif", size=11),
    xaxis=dict(title="log10(Diameter km)", gridcolor="#161630",
               tickfont=dict(color="#ffffff"), zeroline=False),
    yaxis=dict(title="Count", gridcolor="#161630",
               tickfont=dict(color="#ffffff"), zeroline=False),
    margin=dict(l=0, r=0, t=10, b=0),
    height=280, bargap=0.05,
)
st.plotly_chart(fig_hist, use_container_width=True)

# ── Close approaches bar ───────────────────────────────────────────────────────
st.markdown('<p class="section-label">Monthly close approaches (< 10 lunar distances)</p>', unsafe_allow_html=True)

close_df = df[df["miss_distance_ld"] < 10]
monthly_close = (
    close_df.groupby("year_month").size()
    .reset_index(name="count").sort_values("year_month")
)

fig_close = go.Figure(go.Bar(
    x=monthly_close["year_month"],
    y=monthly_close["count"],
    marker=dict(color="#06b6d4", opacity=0.65,
                line=dict(color="rgba(0,0,0,0)", width=0)),
    hovertemplate="<b>%{x}</b><br>%{y} close approaches<extra></extra>",
))
fig_close.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#ffffff", family="sans-serif", size=11),
    xaxis=dict(showgrid=False, tickfont=dict(color="#ffffff"), tickangle=-30),
    yaxis=dict(title="Count", gridcolor="#161630",
               tickfont=dict(color="#ffffff"), zeroline=False),
    margin=dict(l=0, r=0, t=10, b=40),
    height=280, bargap=0.3,
)
st.plotly_chart(fig_close, use_container_width=True)

# ── Summary table ──────────────────────────────────────────────────────────────
st.markdown('<p class="section-label">Monthly summary</p>', unsafe_allow_html=True)

summary = (
    df.groupby("year_month").agg(
        total=("name", "count"),
        hazardous=("is_hazardous", "sum"),
        avg_velocity=("velocity_kms", "mean"),
        avg_miss_au=("miss_distance_au", "mean"),
        min_miss_ld=("miss_distance_ld", "min"),
    )
    .reset_index()
    .sort_values("year_month", ascending=False)
    .rename(columns={
        "year_month":   "Month",
        "total":        "Total NEOs",
        "hazardous":    "Hazardous",
        "avg_velocity": "Avg Velocity (km/s)",
        "avg_miss_au":  "Avg Miss (AU)",
        "min_miss_ld":  "Min Miss (LD)",
    })
)
summary["Avg Velocity (km/s)"] = summary["Avg Velocity (km/s)"].round(2)
summary["Avg Miss (AU)"]       = summary["Avg Miss (AU)"].round(5)
summary["Min Miss (LD)"]       = summary["Min Miss (LD)"].round(3)

st.dataframe(summary, use_container_width=True, height=300)