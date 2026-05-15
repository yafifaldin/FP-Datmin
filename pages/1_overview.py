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

def _inject_css():
    p = Path(__file__).parent.parent / "assets" / "style.css"
    if p.exists():
        with open(p, encoding="utf-8") as f:
            st.html("<style>" + f.read() + "</style>")

_inject_css()

today  = datetime.utcnow().date()
end_dt = today + timedelta(days=6)
start_str = today.isoformat()
end_str   = end_dt.isoformat()

st.html(f"""
<p class="page-eyebrow">Earth's Threat Monitor &nbsp;·&nbsp; 01</p>
<h1 class="page-title">Live NEO Feed</h1>
<p class="page-subtitle">
    Close approach data for {start_str} &rarr; {end_str} &nbsp;&middot;&nbsp; Updates every hour
</p>
""")

@st.cache_data(ttl=3600, show_spinner="Fetching NEO data from NASA...")
def load_feed(start: str, end: str) -> pd.DataFrame:
    raw = get_feed(start, end)
    df  = parse_feed(raw)
    return add_risk_score(df)

try:
    df = load_feed(start_str, end_str)
except Exception as e:
    st.error(f"NASA API error: {e}")
    st.stop()

if df.empty:
    st.warning("No NEO data for this window.")
    st.stop()

total      = len(df)
hazardous  = int(df["is_hazardous"].sum())
fastest    = df["velocity_kms"].max()
closest    = df["miss_distance_ld"].min()
fastest_nm = df.loc[df["velocity_kms"].idxmax(), "name"]
closest_nm = df.loc[df["miss_distance_ld"].idxmin(), "name"]

# ── Stat cards ─────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4, gap="medium")

with c1:
    st.html(f"""
    <div class="stat-card" style="--acc:#00d4ff">
        <div class="stat-label">Tracked this week</div>
        <div class="stat-num">{total}</div>
        <div class="stat-desc">close approaches detected</div>
    </div>
    """)
with c2:
    st.html(f"""
    <div class="stat-card" style="--acc:#e040fb">
        <div class="stat-label">Classified hazardous</div>
        <div class="stat-num">{hazardous}</div>
        <div class="stat-desc">{hazardous / max(total, 1) * 100:.0f}% of total tracked</div>
    </div>
    """)
with c3:
    st.html(f"""
    <div class="stat-card" style="--acc:#a78bfa">
        <div class="stat-label">Peak velocity (km/s)</div>
        <div class="stat-num">{fastest:.1f}</div>
        <div class="stat-desc">{fastest_nm}</div>
    </div>
    """)
with c4:
    st.html(f"""
    <div class="stat-card" style="--acc:#06b6d4">
        <div class="stat-label">Closest pass (LD)</div>
        <div class="stat-num">{closest:.2f}</div>
        <div class="stat-desc">{closest_nm}</div>
    </div>
    """)

# ── Bar chart ──────────────────────────────────────────────────────────────────
st.html('<p class="section-label">Approaches per day</p>')

daily = df.groupby(df["date"].dt.date).size().reset_index(name="count")
daily.columns = ["date", "count"]

max_idx    = int(daily["count"].idxmax())
bar_colors = ["#00d4ff" if i == max_idx else "#7c3aed" for i in range(len(daily))]
bar_opac   = [0.9 if i == max_idx else 0.45 for i in range(len(daily))]

fig_bar = go.Figure(go.Bar(
    x=daily["date"].astype(str),
    y=daily["count"],
    marker=dict(color=bar_colors, opacity=bar_opac,
                line=dict(color="rgba(0,0,0,0)", width=0)),
    hovertemplate="<b>%{x}</b><br>%{y} asteroids<extra></extra>",
))
fig_bar.add_annotation(
    x=daily.loc[max_idx, "date"].isoformat(),
    y=daily.loc[max_idx, "count"],
    text=f"  peak &middot; {daily.loc[max_idx, 'count']}",
    showarrow=False, yanchor="bottom",
    font=dict(color="#00d4ff", size=11),
)
fig_bar.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#8892b0", family="sans-serif", size=11),
    xaxis=dict(showgrid=False, tickfont=dict(color="#3d4460"), linecolor="#161630"),
    yaxis=dict(gridcolor="#161630", tickfont=dict(color="#3d4460"),
               title=None, zeroline=False),
    margin=dict(l=0, r=0, t=30, b=0),
    height=260, bargap=0.35,
)
st.plotly_chart(fig_bar, use_container_width=True)

# ── Table ──────────────────────────────────────────────────────────────────────
st.html('<p class="section-label">Asteroid close approach table</p>')

if (df["miss_distance_ld"] < 5).any():
    st.html("""
    <div class="callout">
        Rows highlighted in <span class="callout-accent">magenta</span>
        have miss distance &lt; 5 lunar distances &mdash; considered very close approaches.
    </div>
    """)

display_df = df[[
    "name", "date", "diameter_km", "velocity_kms",
    "miss_distance_ld", "is_hazardous", "risk_score"
]].copy()
display_df["date"]             = display_df["date"].dt.strftime("%Y-%m-%d")
display_df["diameter_km"]      = display_df["diameter_km"].round(4)
display_df["velocity_kms"]     = display_df["velocity_kms"].round(2)
display_df["miss_distance_ld"] = display_df["miss_distance_ld"].round(3)
display_df["risk_score"]       = display_df["risk_score"].round(4)
display_df.columns = [
    "Name", "Date", "Diameter (km)", "Velocity (km/s)",
    "Miss Dist (LD)", "Hazardous", "Risk Score",
]

def highlight_close(row):
    if row["Miss Dist (LD)"] < 5:
        return ["background-color: rgba(224,64,251,0.10); color: #e8eeff"] * len(row)
    return ["color: #8892b0"] * len(row)

styled = display_df.style.apply(highlight_close, axis=1)
st.dataframe(styled, use_container_width=True, height=400)
