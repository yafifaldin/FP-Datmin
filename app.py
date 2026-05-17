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

today = datetime.utcnow().strftime("%d %b %Y").upper()

# ── Header ────────────────────────────────────────────────────────────────────
st.caption(f"🔵 LIVE  ·  NASA NEOWS  ·  {today}")
st.title("☄️ Earth's Threat Monitor")

st.markdown("""
Dashboard ini memvisualisasikan dan menganalisis data asteroid **Near-Earth Object (NEO)**
secara langsung dari **NASA NeoWs API** — API publik resmi NASA yang menyediakan data
pendekatan asteroid ke Bumi secara real-time.
""")

st.markdown("""
Secara teknis, data diambil menggunakan library `requests` dengan dua endpoint utama:
**feed** untuk data pendekatan 7 hari ke depan, dan **browse** untuk data historis orbital.
Setiap respons API di-parse menggunakan `pandas` menjadi dataframe terstruktur, lalu
divisualisasikan dengan `plotly`. Data live di-cache selama **1 jam** via `@st.cache_data`
supaya tidak over-hit API limit, sedangkan data historis disimpan lokal dalam format `.pkl`.

Salah satu fitur analitik utama adalah **Composite Risk Score** — metrik buatan sendiri
yang menghitung tingkat ancaman asteroid berdasarkan kombinasi ukuran diameter, kecepatan
relatif, dan jarak pendekatan, sebagai alternatif dari label biner hazardous NASA yang statis.
""")

st.divider()

# ── Nav items ─────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2, gap="large")

with col1:
    st.markdown("**`01` — Live NEO Feed**")
    st.markdown("""
    Menampilkan asteroid yang mendekati Bumi dalam window 7 hari ke depan secara real-time.
    Dilengkapi 4 metric card (total NEO, jumlah hazardous (labeled by NASA), kecepatan tertinggi, jarak terdekat),
    bar chart distribusi harian, dan tabel interaktif dengan highlight untuk objek di bawah
    5 Lunar Distance.
    """)

    st.markdown("**`03` — Orbital Deep Dive**")
    st.markdown("""
    Analisis mendalam berdasarkan kelas orbit asteroid (Apollo, Amor, Aten, Atira).
    Menggunakan violin plot untuk distribusi kecepatan, stacked bar untuk proporsi hazardous,
    dan uji statistik **Kruskal-Wallis** untuk memverifikasi apakah perbedaan kecepatan
    antar kelas orbit signifikan secara statistik (p-value ditampilkan langsung).
    """)

with col2:
    st.markdown("**`02` — Risk Analysis**")
    st.markdown("""
    Analisis ancaman berbasis Composite Risk Score — formula **(diameter × velocity) / miss_distance**
    yang dikembangkan sendiri untuk mengukur tingkat bahaya secara lebih dinamis dibanding
    label hazardous NASA. Visualisasi berupa scatter plot multivariabel, ranking top-15,
    dan donut chart distribusi risiko.
    """)

    st.markdown("**`04` — Historical Trends**")
    st.markdown("""
    Tren historis 6 bulan terakhir dari data pendekatan asteroid. Menampilkan rata-rata
    miss distance bulanan, distribusi ukuran diameter (log scale), dan frekuensi pendekatan
    sangat dekat (di bawah 10 Lunar Distance) per bulan. Data di-cache lokal untuk efisiensi.
    """)

st.divider()
st.caption("Pilih halaman dari sidebar untuk mulai eksplorasi →")