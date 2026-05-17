import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from pathlib import Path

from utils.fetch_data import get_feed
from utils.clean_data import parse_feed
from utils.scoring import add_risk_score, add_risk_label

def _inject_css():
    p = Path(__file__).parent.parent / "assets" / "style.css"
    if p.exists():
        with open(p, encoding="utf-8") as f:
            st.html("<style>" + f.read() + "</style>")

_inject_css()

st.html("""
<p class="page-eyebrow">Earth's Threat Monitor &nbsp;·&nbsp; 02</p>
<h1 class="page-title">Risk Analysis</h1>
<p class="page-subtitle">
    Composite threat scoring across size, velocity, and proximity &mdash;
    ranked and visualised for the current 7-day window.
</p>
""")

today  = datetime.utcnow().date()
end_dt = today + timedelta(days=6)

@st.cache_data(ttl=3600, show_spinner="Loading risk data...")
def load(start: str, end: str) -> pd.DataFrame:
    raw = get_feed(start, end)
    df  = parse_feed(raw)
    df  = add_risk_score(df)
    df  = add_risk_label(df)
    return df

try:
    df = load(today.isoformat(), end_dt.isoformat())
except Exception as e:
    st.error(f"API error: {e}")
    st.stop()

if df.empty:
    st.warning("No data available.")
    st.stop()

haz_mask = df["is_hazardous"]

# ── Scatter ────────────────────────────────────────────────────────────────────
st.html('<p class="section-label">Velocity vs. miss distance</p>')
st.html("""
<p style="font-size:0.8rem; color:#2a2e4a; margin:-0.25rem 0 0.75rem; line-height:1.6;">
    Bubble size encodes estimated diameter.
    <span style="color:#e040fb">&#9670; Hazardous</span> objects are diamonds.
</p>
""")

size_scale = (
    (df["diameter_km"] - df["diameter_km"].min()) /
    (df["diameter_km"].max() - df["diameter_km"].min() + 1e-9)
) * 36 + 6

avg_dist = df["miss_distance_au"].mean()

fig_scatter = go.Figure()
fig_scatter.add_vline(
    x=avg_dist, line=dict(color="#1e1e3a", width=1, dash="dot"),
    annotation_text="avg dist",
    annotation_font=dict(color="#2a2e4a", size=10),
    annotation_position="top left",
)
fig_scatter.add_trace(go.Scatter(
    x=df.loc[~haz_mask, "miss_distance_au"],
    y=df.loc[~haz_mask, "velocity_kms"],
    mode="markers", name="Non-hazardous",
    marker=dict(size=size_scale[~haz_mask], color="#7c3aed", opacity=0.5,
                line=dict(color="rgba(0,0,0,0)", width=0)),
    text=df.loc[~haz_mask, "name"],
    hovertemplate="<b>%{text}</b><br>%{x:.4f} AU &middot; %{y:.1f} km/s<extra></extra>",
))
fig_scatter.add_trace(go.Scatter(
    x=df.loc[haz_mask, "miss_distance_au"],
    y=df.loc[haz_mask, "velocity_kms"],
    mode="markers", name="Hazardous",
    marker=dict(size=size_scale[haz_mask], color="#e040fb", opacity=0.85,
                symbol="diamond", line=dict(color="#0d0d1f", width=1)),
    text=df.loc[haz_mask, "name"],
    hovertemplate="<b>%{text}</b> &#9888;<br>%{x:.4f} AU &middot; %{y:.1f} km/s<extra></extra>",
))
fig_scatter.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#8892b0", family="sans-serif", size=11),
    xaxis=dict(title="Miss Distance (AU)", gridcolor="#161630",
               tickfont=dict(color="#3d4460"), zeroline=False),
    yaxis=dict(title="Velocity (km/s)", gridcolor="#161630",
               tickfont=dict(color="#3d4460"), zeroline=False),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#4a5470", size=11), borderwidth=0),
    margin=dict(l=0, r=0, t=10, b=0),
    height=400,
)
st.plotly_chart(fig_scatter, use_container_width=True)

# ── Top 15 ────────────────────────────────────────────────────────────────────
st.html('<p class="section-label">Top 15 by risk score</p>')

top15 = df.nlargest(15, "risk_score")[["name", "risk_score", "is_hazardous"]].sort_values("risk_score")
bar_colors = ["#e040fb" if r else "#7c3aed" for r in top15["is_hazardous"]]
bar_opac   = [0.9 if r else 0.5 for r in top15["is_hazardous"]]

fig_top = go.Figure(go.Bar(
    x=top15["risk_score"], y=top15["name"], orientation="h",
    marker=dict(color=bar_colors, opacity=bar_opac,
                line=dict(color="rgba(0,0,0,0)", width=0)),
    hovertemplate="<b>%{y}</b><br>Risk score: %{x:.4f}<extra></extra>",
))
fig_top.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#8892b0", family="sans-serif", size=11),
    xaxis=dict(title="Risk Score", gridcolor="#161630",
               tickfont=dict(color="#3d4460"), zeroline=False),
    yaxis=dict(tickfont=dict(color="#8892b0", size=10), automargin=True),
    margin=dict(l=0, r=30, t=10, b=0),
    height=max(320, len(top15) * 26),
)
st.plotly_chart(fig_top, use_container_width=True)

# ── Insight ────────────────────────────────────────────────────────────────────
q75 = df["risk_score"].quantile(0.75)
non_haz_high = df[~df["is_hazardous"] & (df["risk_score"] >= q75)]

st.html(f"""
<div class="callout">
    <b>{len(non_haz_high)} non-hazardous</b> asteroid(s) fall in the top-quartile
    risk bracket (score &ge; {q75:.3f}).
    These objects carry high kinetic threat potential &mdash; large size, fast velocity,
    or close proximity &mdash; despite not meeting NASA's official hazard criteria.
</div>
""")

# ── Donut ──────────────────────────────────────────────────────────────────────
st.html('<p class="section-label">Risk distribution</p>')

risk_counts = df["risk_label"].value_counts().reset_index()
risk_counts.columns = ["label", "count"]
lc = {"High": "#e040fb", "Medium": "#7c3aed", "Low": "#2a2e4a"}

fig_pie = go.Figure(go.Pie(
    labels=risk_counts["label"],
    values=risk_counts["count"],
    hole=0.62,
    marker=dict(
        colors=[lc.get(l, "#7c3aed") for l in risk_counts["label"]],
        line=dict(color="#0d0d1f", width=3),
    ),
    textfont=dict(color="#8892b0", size=12),
    hovertemplate="<b>%{label}</b><br>%{value} objects (%{percent})<extra></extra>",
))
fig_pie.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#8892b0"),
    legend=dict(font=dict(color="#4a5470", size=11), bgcolor="rgba(0,0,0,0)"),
    margin=dict(l=0, r=0, t=10, b=0),
    height=280,
    annotations=[dict(
        text=f"<b>{len(df)}</b><br>NEOs",
        x=0.5, y=0.5, showarrow=False,
        font=dict(color="#8892b0", size=14),
    )],
)
st.plotly_chart(fig_pie, use_container_width=True)