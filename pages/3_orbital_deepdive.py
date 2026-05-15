import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy import stats
from pathlib import Path

from utils.fetch_data import get_browse
from utils.clean_data import parse_browse
from utils.scoring import add_risk_score

st.set_page_config(
    page_title="Orbital Deep Dive · Earth's Threat Monitor",
    page_icon="🔭",
    layout="wide",
)

css_path = Path(__file__).parent.parent / "assets" / "style.css"
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)

st.markdown(
    """
    <div class="page-title">Orbital Deep Dive</div>
    <div class="page-subtitle">
        Orbital class distributions, velocity profiles, and statistical testing
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Load browse data ───────────────────────────────────────────────────────────
@st.cache_data(ttl=7200, show_spinner="Loading orbital data...")
def load_browse(pages: int = 5) -> pd.DataFrame:
    frames = []
    for p in range(pages):
        try:
            raw = get_browse(page=p, size=20)
            frames.append(parse_browse(raw))
        except Exception:
            break
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    return add_risk_score(df)

df = load_browse()

if df.empty:
    st.warning("No orbital data could be fetched.")
    st.stop()

# Normalise orbit class names
orbit_map = {
    "Amor": "Amor", "Apollo": "Apollo", "Aten": "Aten", "Atira": "Atira",
    "amor": "Amor", "apollo": "Apollo", "aten": "Aten", "atira": "Atira",
}
df["orbit_class"] = df["orbit_class"].map(
    lambda x: orbit_map.get(x, x)
).fillna("Other")

ORBIT_COLORS = {
    "Atira": "#00d4ff",
    "Aten":  "#7c3aed",
    "Apollo": "#e040fb",
    "Amor":  "#06b6d4",
    "Other": "#a78bfa",
}
CHART_COLORS = ["#00d4ff", "#7c3aed", "#e040fb", "#06b6d4", "#a78bfa"]

classes = df["orbit_class"].unique().tolist()

# ── Violin plot: velocity per orbit class ──────────────────────────────────────
st.markdown('<div class="section-title">Velocity Distribution by Orbit Class</div>', unsafe_allow_html=True)

fig_violin = go.Figure()
for cls in classes:
    subset = df.loc[df["orbit_class"] == cls, "velocity_kms"].dropna()
    if len(subset) < 2:
        continue
    fig_violin.add_trace(go.Violin(
        y=subset,
        name=cls,
        line_color=ORBIT_COLORS.get(cls, "#a78bfa"),
        fillcolor=ORBIT_COLORS.get(cls, "#a78bfa"),
        opacity=0.6,
        box_visible=True,
        meanline_visible=True,
        points="outliers",
        hovertemplate=f"<b>{cls}</b><br>Velocity: %{{y:.2f}} km/s<extra></extra>",
    ))

fig_violin.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#ffffff", family="sans-serif"),
    yaxis=dict(
        title="Velocity (km/s)",
        gridcolor="#2a2a4a",
        tickfont=dict(color="#8892b0"),
    ),
    xaxis=dict(tickfont=dict(color="#ffffff")),
    legend=dict(bgcolor="rgba(26,26,46,0.8)", bordercolor="#2a2a4a", borderwidth=1),
    margin=dict(l=0, r=0, t=20, b=0),
    height=380,
    violingap=0.3,
    violinmode="group",
)
st.plotly_chart(fig_violin, use_container_width=True)

# ── Stacked bar: hazardous proportion per orbit class ──────────────────────────
st.markdown('<div class="section-title">Hazardous Proportion by Orbit Class</div>', unsafe_allow_html=True)

haz_counts = (
    df.groupby(["orbit_class", "is_hazardous"])
    .size()
    .unstack(fill_value=0)
    .reset_index()
)
haz_counts.columns.name = None
haz_counts = haz_counts.rename(columns={False: "Non-Hazardous", True: "Hazardous"})
for col in ("Non-Hazardous", "Hazardous"):
    if col not in haz_counts.columns:
        haz_counts[col] = 0

fig_stk = go.Figure()
fig_stk.add_trace(go.Bar(
    x=haz_counts["orbit_class"],
    y=haz_counts["Non-Hazardous"],
    name="Non-Hazardous",
    marker_color="#00d4ff",
    opacity=0.8,
))
fig_stk.add_trace(go.Bar(
    x=haz_counts["orbit_class"],
    y=haz_counts["Hazardous"],
    name="Hazardous",
    marker_color="#e040fb",
    opacity=0.9,
))
fig_stk.update_layout(
    barmode="stack",
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#ffffff"),
    xaxis=dict(tickfont=dict(color="#ffffff"), showgrid=False),
    yaxis=dict(
        title="Count",
        gridcolor="#2a2a4a",
        tickfont=dict(color="#8892b0"),
    ),
    legend=dict(bgcolor="rgba(26,26,46,0.8)", bordercolor="#2a2a4a"),
    margin=dict(l=0, r=0, t=10, b=0),
    height=320,
)
st.plotly_chart(fig_stk, use_container_width=True)

# ── Scatter: magnitude vs diameter (log-log) ───────────────────────────────────
st.markdown('<div class="section-title">Absolute Magnitude vs. Diameter (log-log)</div>', unsafe_allow_html=True)

scatter_df = df.dropna(subset=["magnitude", "diameter_km"])
scatter_df = scatter_df[scatter_df["diameter_km"] > 0]

fig_mag = go.Figure(
    go.Scatter(
        x=scatter_df["diameter_km"],
        y=scatter_df["magnitude"],
        mode="markers",
        marker=dict(
            color="#00d4ff",
            opacity=0.7,
            size=7,
            line=dict(color="#2a2a4a", width=0.5),
        ),
        text=scatter_df["name"],
        hovertemplate=(
            "<b>%{text}</b><br>"
            "Diameter: %{x:.4f} km<br>"
            "Magnitude: %{y:.2f}<extra></extra>"
        ),
    )
)
fig_mag.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#ffffff"),
    xaxis=dict(
        type="log",
        title="Diameter (km) — log scale",
        gridcolor="#2a2a4a",
        tickfont=dict(color="#8892b0"),
    ),
    yaxis=dict(
        type="log",
        title="Absolute Magnitude (H) — log scale",
        gridcolor="#2a2a4a",
        tickfont=dict(color="#8892b0"),
    ),
    margin=dict(l=0, r=0, t=10, b=0),
    height=360,
)
st.plotly_chart(fig_mag, use_container_width=True)

# ── Kruskal-Wallis test ────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Kruskal-Wallis Test: Velocity across Orbit Classes</div>', unsafe_allow_html=True)

groups = [
    df.loc[df["orbit_class"] == cls, "velocity_kms"].dropna().values
    for cls in classes
    if (df["orbit_class"] == cls).sum() >= 2
]

if len(groups) >= 2:
    h_stat, p_val = stats.kruskal(*groups)
    sig = p_val < 0.05
    interpretation = (
        "The velocity distributions differ significantly across orbit classes "
        f"(H = {h_stat:.3f}, p = {p_val:.4f} < 0.05). "
        "This suggests orbit class is a meaningful predictor of approach velocity."
        if sig else
        "No significant difference in velocity distributions across orbit classes "
        f"(H = {h_stat:.3f}, p = {p_val:.4f} ≥ 0.05). "
        "Orbit class does not appear to strongly predict approach velocity in this sample."
    )
    color = "#e040fb" if sig else "#00d4ff"
    st.markdown(
        f"""
        <div class="custom-stat">
            <h4>Kruskal-Wallis H-Test Results</h4>
            <p><span class="highlight">H-statistic:</span> {h_stat:.4f}</p>
            <p><span class="highlight">p-value:</span> {p_val:.6f}</p>
            <p><span class="highlight">Significant:</span>
                <span style="color:{color}; font-weight:600;">
                    {'Yes (p < 0.05)' if sig else 'No (p ≥ 0.05)'}
                </span>
            </p>
            <hr style="border-color:#2a2a4a; margin:0.75rem 0;">
            <p style="color:#ffffff;">{interpretation}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.info("Not enough groups with sufficient data for Kruskal-Wallis test.")
