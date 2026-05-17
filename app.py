import streamlit as st
from pathlib import Path
from datetime import datetime

st.set_page_config(
    page_title="Earth's Threat Monitor",
    page_icon="☄️",
    layout="wide",
    initial_sidebar_state="expanded",
)

def _inject_css():
    p = Path(__file__).parent / "assets" / "style.css"
    if p.exists():
        with open(p, encoding="utf-8") as f:
            css = f.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

_inject_css()

with st.sidebar:
    st.markdown("""
    <div style="padding: 1.5rem 1rem 1rem;">
        <div style="font-size:0.62rem; letter-spacing:2px; text-transform:uppercase;
                    color:#5a6480; margin-bottom:8px;">Navigation</div>
        <div style="font-size:1rem; font-weight:700; color:#e8eeff; margin-bottom:2px;">
            Earth's Threat Monitor
        </div>
        <div style="font-size:0.72rem; color:#5a6480;">NASA NeoWs API</div>
    </div>
    <div style="height:1px; background:#1e1e3a; margin:0 1rem 1rem;"></div>
    """, unsafe_allow_html=True)

today = datetime.utcnow().strftime("%d %b %Y").upper()

st.markdown(f"""
<div style="max-width:680px; padding: 1rem 0 0;">

    <div class="status-row">
        <span class="live-dot"></span>
        <span>Live</span>
        <span class="status-sep">&nbsp;·&nbsp;</span>
        <span>NASA NeoWs</span>
        <span class="status-sep">&nbsp;·&nbsp;</span>
        <span>{today}</span>
    </div>

    <h1 style="font-size:2.6rem; font-weight:800; color:#e8eeff;
               margin:0 0 10px; line-height:1.1; letter-spacing:-1px;">
        Earth's Threat Monitor
    </h1>
    <p style="font-size:1rem; color:#6b7490; line-height:1.7; margin:0 0 2.5rem; max-width:520px;">
        Near-Earth Object surveillance powered by NASA's Center for Near Earth Object Studies.
        Tracks asteroid close approaches, relative velocities, and impact risk in real time.
    </p>

    <div style="border-top:1px solid #1e1e3a;">

        <div class="landing-nav-item">
            <div class="landing-nav-num">01</div>
            <div>
                <div class="landing-nav-title">Live NEO Feed</div>
                <div class="landing-nav-desc">
                    Real-time 7-day asteroid close approach window — count, velocity,
                    miss distance, and hazard classification.
                </div>
            </div>
        </div>

        <div class="landing-nav-item">
            <div class="landing-nav-num">02</div>
            <div>
                <div class="landing-nav-title">Risk Analysis</div>
                <div class="landing-nav-desc">
                    Composite threat scoring across diameter, velocity, and proximity.
                    Top-15 ranking and scatter plot by miss distance.
                </div>
            </div>
        </div>

        <div class="landing-nav-item">
            <div class="landing-nav-num">03</div>
            <div>
                <div class="landing-nav-title">Orbital Deep Dive</div>
                <div class="landing-nav-desc">
                    Orbit class distributions, hazardous proportions,
                    magnitude vs. diameter, and Kruskal-Wallis significance test.
                </div>
            </div>
        </div>

        <div class="landing-nav-item" style="border-bottom:none;">
            <div class="landing-nav-num">04</div>
            <div>
                <div class="landing-nav-title">Historical Trends</div>
                <div class="landing-nav-desc">
                    Six months of approach frequency, miss distance patterns,
                    and size distribution over time.
                </div>
            </div>
        </div>

    </div>

    <p style="font-size:0.65rem; color:#3a3e5a; margin-top:2.5rem;
              letter-spacing:1px; text-transform:uppercase;">
        Select a page from the sidebar to begin
    </p>

</div>
""", unsafe_allow_html=True)