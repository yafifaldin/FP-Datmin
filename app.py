import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="Earth's Threat Monitor",
    page_icon="☄️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Inject global CSS ──────────────────────────────────────────────────────────
css_path = Path(__file__).parent / "assets" / "style.css"
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center; padding: 1rem 0 0.5rem 0;">
            <span style="font-size: 2.5rem;">☄️</span>
            <h2 style="color:#ffffff; margin:0.25rem 0 0 0; font-size:1.1rem; font-weight:700;">
                Earth's Threat Monitor
            </h2>
            <p style="color:#8892b0; font-size:0.8rem; margin-top:0.25rem;">
                Powered by NASA NeoWs API
            </p>
        </div>
        <hr style="border-color:#2a2a4a; margin: 0.75rem 0;">
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <p style="color:#8892b0; font-size:0.82rem; line-height:1.6; padding:0 0.5rem;">
        Real-time Near-Earth Object tracking and risk analysis.
        Monitor asteroid approaches, velocities, and potential hazards
        using live data from NASA's Center for Near Earth Object Studies.
        </p>
        <hr style="border-color:#2a2a4a; margin: 0.75rem 0;">
        <p style="color:#2a2a4a; font-size:0.7rem; text-align:center; padding-top:0.5rem;">
            Data: NASA NeoWs · v1.0
        </p>
        """,
        unsafe_allow_html=True,
    )

# ── Landing page content ───────────────────────────────────────────────────────
st.markdown(
    """
    <div style="text-align:center; padding: 3rem 0 2rem 0;">
        <span style="font-size:4rem;">☄️</span>
        <h1 style="font-size:2.8rem; font-weight:800; color:#ffffff; margin:0.5rem 0 0.25rem 0;">
            Earth's Threat Monitor
        </h1>
        <p style="font-size:1.1rem; color:#8892b0; max-width:600px; margin:0 auto;">
            Real-time Near-Earth Object surveillance dashboard.<br>
            Tracking asteroids, velocities, and close approaches — powered by NASA NeoWs.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

cols = st.columns(4, gap="medium")
cards = [
    ("☄️", "Live NEO Feed", "7-day asteroid window", "#7c3aed", "#00d4ff"),
    ("⚠️", "Risk Analysis", "Threat scoring & scatter", "#e040fb", "#7c3aed"),
    ("🔭", "Orbital Deep Dive", "Class distributions & stats", "#00d4ff", "#06b6d4"),
    ("📈", "Historical Trends", "Long-term approach patterns", "#06b6d4", "#00d4ff"),
]
for col, (icon, title, desc, c1, c2) in zip(cols, cards):
    with col:
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, {c1}22, {c2}22);
                border: 1px solid {c1}55;
                border-radius: 16px;
                padding: 24px 20px;
                text-align: center;
                cursor: default;
            ">
                <div style="font-size:2rem; margin-bottom:0.5rem;">{icon}</div>
                <div style="font-size:1rem; font-weight:700; color:#ffffff; margin-bottom:0.3rem;">{title}</div>
                <div style="font-size:0.82rem; color:#8892b0;">{desc}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown(
    """
    <div style="text-align:center; margin-top:2.5rem; color:#8892b0; font-size:0.85rem;">
        Use the sidebar navigation to explore each section.
    </div>
    """,
    unsafe_allow_html=True,
)
