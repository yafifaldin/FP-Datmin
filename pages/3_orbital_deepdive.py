import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from scipy import stats
from pathlib import Path

from utils.fetch_data import get_browse
from utils.clean_data import parse_browse
from utils.scoring import add_risk_score

st.set_page_config(
    page_title="Orbital Deep Dive · Earth's Threat Monitor",
    page_icon="☄️",
    layout="wide",
)

def _inject_css():
    p = Path(__file__).parent.parent / "assets" / "style.css"
    if p.exists():
        with open(p, encoding="utf-8") as f:
            st.html("<style>" + f.read() + "</style>")

_inject_css()

st.html("""
<p class="page-eyebrow">Earth's Threat Monitor &nbsp;·&nbsp; 03</p>
<h1 class="page-title">Orbital Deep Dive</h1>
<p class="page-subtitle">
    Velocity profiles by orbit class, hazard proportions,
    magnitude&ndash;diameter relationship, and significance testing.
</p>
""")

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
    return add_risk_score(pd.concat(frames, ignore_index=True))

df = load_browse()
if df.empty:
    st.warning("No orbital data could be fetched.")
    st.stop()

orbit_map = {c.lower(): c for c in ["Amor", "Apollo", "Aten", "Atira"]}
df["orbit_class"] = df["orbit_class"].apply(
    lambda x: orbit_map.get(str(x).lower(), x)
).fillna("Other")

ORBIT_COLORS = {
    "Atira": "#00d4ff", "Aten": "#7c3aed",
    "Apollo": "#e040fb", "Amor": "#06b6d4", "Other": "#a78bfa",
}
classes = [c for c in ORBIT_COLORS if c in df["orbit_class"].unique()]
classes += [c for c in df["orbit_class"].unique() if c not in classes]

# ── Violin ─────────────────────────────────────────────────────────────────────
st.html('<p class="section-label">Velocity by orbit class</p>')

fig_violin = go.Figure()
for cls in classes:
    subset = df.loc[df["orbit_class"] == cls, "velocity_kms"].dropna()
    if len(subset) < 2:
        continue
    col = ORBIT_COLORS.get(cls, "#a78bfa")
    fig_violin.add_trace(go.Violin(
        y=subset, name=cls, line_color=col, fillcolor=col,
        opacity=0.45, box_visible=True, meanline_visible=True, points=False,
        hovertemplate=f"<b>{cls}</b><br>%{{y:.2f}} km/s<extra></extra>",
    ))
fig_violin.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#8892b0", family="sans-serif", size=11),
    yaxis=dict(title="Velocity (km/s)", gridcolor="#161630",
               tickfont=dict(color="#3d4460"), zeroline=False),
    xaxis=dict(tickfont=dict(color="#8892b0")),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#4a5470"), borderwidth=0),
    margin=dict(l=0, r=0, t=10, b=0),
    height=360, violingap=0.25, violinmode="group",
)
st.plotly_chart(fig_violin, use_container_width=True)

# ── Stacked bar ────────────────────────────────────────────────────────────────
st.html('<p class="section-label">Hazardous proportion by orbit class</p>')

haz_counts = (
    df.groupby(["orbit_class", "is_hazardous"]).size()
    .unstack(fill_value=0).reset_index()
)
haz_counts.columns.name = None
haz_counts = haz_counts.rename(columns={False: "Non-Hazardous", True: "Hazardous"})
for col in ("Non-Hazardous", "Hazardous"):
    if col not in haz_counts.columns:
        haz_counts[col] = 0

fig_stk = go.Figure()
fig_stk.add_trace(go.Bar(
    x=haz_counts["orbit_class"], y=haz_counts["Non-Hazardous"],
    name="Non-hazardous", marker_color="#7c3aed", opacity=0.4,
))
fig_stk.add_trace(go.Bar(
    x=haz_counts["orbit_class"], y=haz_counts["Hazardous"],
    name="Hazardous", marker_color="#e040fb", opacity=0.8,
))
fig_stk.update_layout(
    barmode="stack", template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#8892b0", family="sans-serif", size=11),
    xaxis=dict(tickfont=dict(color="#8892b0"), showgrid=False),
    yaxis=dict(title="Count", gridcolor="#161630",
               tickfont=dict(color="#3d4460"), zeroline=False),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#4a5470"), borderwidth=0),
    margin=dict(l=0, r=0, t=10, b=0),
    height=300, bargap=0.3,
)
st.plotly_chart(fig_stk, use_container_width=True)

# ── Magnitude vs diameter ──────────────────────────────────────────────────────
st.html('<p class="section-label">Absolute magnitude vs. diameter (log&ndash;log)</p>')

scatter_df = df.dropna(subset=["magnitude", "diameter_km"])
scatter_df = scatter_df[scatter_df["diameter_km"] > 0]

fig_mag = go.Figure(go.Scatter(
    x=scatter_df["diameter_km"], y=scatter_df["magnitude"], mode="markers",
    marker=dict(color="#7c3aed", opacity=0.55, size=6,
                line=dict(color="rgba(0,0,0,0)", width=0)),
    text=scatter_df["name"],
    hovertemplate="<b>%{text}</b><br>D: %{x:.4f} km &middot; H: %{y:.1f}<extra></extra>",
))
fig_mag.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#8892b0", family="sans-serif", size=11),
    xaxis=dict(type="log", title="Diameter (km) - log scale",
               gridcolor="#161630", tickfont=dict(color="#3d4460"), zeroline=False),
    yaxis=dict(type="log", title="Absolute Magnitude (H) - log scale",
               gridcolor="#161630", tickfont=dict(color="#3d4460"), zeroline=False),
    margin=dict(l=0, r=0, t=10, b=0),
    height=340,
)
st.plotly_chart(fig_mag, use_container_width=True)

# ── Kruskal-Wallis ─────────────────────────────────────────────────────────────
st.html('<p class="section-label">Kruskal&ndash;Wallis test &middot; velocity across orbit classes</p>')

groups = [
    df.loc[df["orbit_class"] == cls, "velocity_kms"].dropna().values
    for cls in classes
    if (df["orbit_class"] == cls).sum() >= 2
]

if len(groups) >= 2:
    h_stat, p_val = stats.kruskal(*groups)
    sig = p_val < 0.05
    sig_color  = "#e040fb" if sig else "#3d4460"
    sig_label  = "Yes" if sig else "No"
    interpret = (
        "Velocity distributions differ significantly across orbit classes "
        "at the 0.05 level. Orbit class is a meaningful predictor of approach velocity."
        if sig else
        "No significant velocity difference found across orbit classes "
        "at the 0.05 level. Sample size may be too small to detect an effect."
    )
    st.html(f"""
    <div class="stats-box">
        <div class="stats-box-title">Test result</div>
        <div class="stats-row">
            <span class="stats-key">H-statistic</span>
            <span class="stats-val">{h_stat:.4f}</span>
        </div>
        <div class="stats-row">
            <span class="stats-key">p-value</span>
            <span class="stats-val">{p_val:.6f}</span>
        </div>
        <div class="stats-row">
            <span class="stats-key">Significant (&alpha; = 0.05)</span>
            <span class="stats-val" style="color:{sig_color}">{sig_label}</span>
        </div>
        <div class="stats-interpret">{interpret}</div>
    </div>
    """)
else:
    st.info("Not enough groups for Kruskal-Wallis test.")
