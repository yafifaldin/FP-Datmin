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

st.caption(f"🔵 LIVE  ·  NASA NEOWS  ·  {today}")
st.title("☄️ Earth's Threat Monitor")

st.markdown("""
Dashboard ini membangun **perspektif alternatif** untuk menilai ancaman asteroid Near-Earth
Object (NEO) berbasis data karakteristik pendekatan aktual — sebagai pelengkap klasifikasi
PHA (Potentially Hazardous Asteroid) milik NASA yang menggunakan kriteria orbital
jangka panjang.
""")

st.divider()

st.subheader("🎯 Latar Belakang & Motivasi")

st.markdown("""
NASA mengklasifikasikan asteroid sebagai **Potentially Hazardous Asteroid (PHA)** berdasarkan
dua kriteria orbital:

- **MOID ≤ 0.05 AU** — Minimum Orbit Intersection Distance, jarak orbital minimum dengan Bumi
- **H ≤ 22.0** — Absolute magnitude, setara diameter ≥ 140 meter

Klasifikasi ini menjawab pertanyaan: *"Apakah orbit asteroid ini berpotensi memotong orbit
Bumi dalam jangka panjang?"*

Namun klasifikasi NASA **tidak mempertimbangkan velocity** — padahal secara fisika,
energi kinetik dampak ditentukan oleh kecepatan (½ × m × v²). Asteroid kecil tapi sangat
cepat bisa lebih destruktif dari asteroid besar tapi lambat.
""")

st.info("""
**Tujuan dashboard ini:** Membangun metrik penilaian ancaman alternatif yang
mempertimbangkan velocity dan kondisi pendekatan aktual — bukan untuk menggantikan
klasifikasi NASA, melainkan sebagai pelengkap yang menangkap dimensi risiko berbeda.
""")

st.divider()

st.subheader("🔬 Pendekatan Analisis")

st.markdown("""
Dashboard ini menggunakan tiga lapis analisis:
""")

col1, col2, col3 = st.columns(3, gap="medium")
with col1:
    st.markdown("**Lapis 1 — Deskriptif**")
    st.markdown("""
    Visualisasi data asteroid langsung dari NASA NeoWs API. Memahami distribusi,
    tren, dan karakteristik populasi NEO yang mendekati Bumi.
    """)
with col2:
    st.markdown("**Lapis 2 — Composite Risk Score**")
    st.markdown("""
    Metrik alternatif berbasis karakteristik pendekatan aktual: (diameter × velocity)
    / miss_distance. Memasukkan velocity yang tidak ada di rule NASA.
    """)
with col3:
    st.markdown("**Lapis 3 — Eksplorasi Data Mining**")
    st.markdown("""
    Clustering untuk memahami struktur alami data, dan classification untuk
    eksplorasi korelasi fitur fisik dengan label NASA.
    """)

st.divider()

st.subheader("⚙️ Detail Teknis")

st.markdown("""
**Sumber Data:** NASA NeoWs API (https://api.nasa.gov/) — dua endpoint:
- `feed` → data pendekatan 7 hari ke depan, refresh tiap jam via `@st.cache_data(ttl=3600)`
- `browse` → database historis dengan informasi orbital class

**Pipeline:** `requests` → `pandas` → `plotly` → `scikit-learn`

**Fitur yang dianalisis dalam dashboard ini:**
- `diameter_km` — estimasi diameter asteroid (midpoint min-max NASA)
- `velocity_kms` — kecepatan relatif saat pendekatan aktual
- `miss_distance_au` — jarak aktual saat pendekatan terdekat
- `magnitude` — absolute magnitude H

**Fitur yang dipakai NASA dalam rule PHA:**
- MOID (jarak orbital jangka panjang — tidak tersedia di NeoWs API)
- H (magnitude)

**Catatan penting:** Prediktor yang kami gunakan **berbeda** dari yang NASA pakai dalam
rule PHA. Karena MOID tidak tersedia di NeoWs API, kami menggunakan miss_distance_au
(jarak aktual) sebagai proxy. Implikasinya, model ML di dashboard ini tidak dapat
diinterpretasikan sebagai audit terhadap rule NASA — melainkan sebagai eksplorasi
perspektif risiko yang berbeda.
""")

st.divider()

st.subheader("📄 Navigasi Halaman")

st.markdown("**`01` — Live NEO Feed**")
st.markdown("""
**Apa yang ditampilkan:** Snapshot real-time semua asteroid yang akan mendekati Bumi dalam
7 hari ke depan. Empat metric utama (jumlah, hazardous count, peak velocity, closest pass),
distribusi per hari, dan tabel interaktif lengkap.

**Apa yang dipelajari:** Konteks awal — seberapa banyak asteroid yang lewat tiap minggu,
seberapa besar, seberapa cepat, seberapa dekat.
""")

st.markdown("**`02` — Risk Analysis**")
st.markdown("""
**Apa yang ditampilkan:** Composite Risk Score diterapkan ke data minggu ini. Scatter plot
multivariabel, ranking top-15 berdasarkan risk score, dan donut chart distribusi risiko.

**Apa yang dipelajari:** Asteroid mana yang paling mengancam minggu ini berdasarkan
perspektif pendekatan aktual — mungkin berbeda dari yang di-label hazardous oleh NASA.
""")

st.markdown("**`03` — Orbital Deep Dive**")
st.markdown("""
**Apa yang ditampilkan:** Analisis berdasarkan kelas orbit asteroid (Apollo, Amor, Aten,
Atira). Violin plot distribusi velocity per kelas, stacked bar proporsi hazardous, dan
uji Kruskal-Wallis untuk signifikansi statistik.

**Apa yang dipelajari:** Apakah velocity berbeda signifikan antar kelas orbit — apakah
variabel yang NASA abaikan ini memang diskriminatif secara statistik.
""")

st.markdown("**`04` — Historical Trends**")
st.markdown("""
**Apa yang ditampilkan:** Tren 6 bulan terakhir dari data pendekatan asteroid.
Line chart miss distance bulanan, histogram distribusi diameter (log scale), dan
frekuensi pendekatan sangat dekat per bulan.

**Apa yang dipelajari:** Konteks temporal — pola pendekatan asteroid dan baseline normal.
""")

st.markdown("**`05` — Data Mining Exploration**")
st.markdown("""
**Apa yang ditampilkan:** Dua analisis data mining yang saling melengkapi.

**Clustering (K-Means):** Mengelompokkan asteroid berdasarkan kemiripan karakteristik fisik
(diameter, velocity, miss_distance, magnitude) tanpa menggunakan label NASA. Cluster diberi
nama berdasarkan karakteristik centroid (bukan interpretasi risiko subjektif).

**Classification (LR vs DT vs RF):** Eksperimen eksploratif untuk mengukur korelasi antara
fitur fisik pendekatan aktual dengan label PHA NASA. Karena prediktor yang kami punya
berbeda dari rule NASA, hasilnya menunjukkan **sejauh mana karakteristik pendekatan aktual
berkorelasi dengan klasifikasi orbital NASA**.

**Apa yang dipelajari:** Pengelompokan alami asteroid berdasarkan karakteristik fisik, dan
pemetaan antara dimensi pendekatan aktual vs dimensi orbital NASA.
""")

st.divider()

st.subheader("🧵 Posisi Akhir")

st.markdown("""
Penelitian ini tidak mengklaim NASA salah atau klasifikasinya inkonsisten. NASA
mengklasifikasikan dari **perspektif orbital jangka panjang** menggunakan MOID — dan
itu valid untuk tujuannya.

Yang kami tawarkan adalah **perspektif kedua yang independen**: penilaian ancaman berbasis
karakteristik pendekatan aktual, termasuk velocity yang tidak ada di rule NASA.
""")

st.success("""
**Kontribusi utama:** Composite Risk Score sebagai metrik pelengkap yang menangkap dimensi
ancaman dinamis pada pendekatan spesifik — informasi yang tidak tertangkap oleh klasifikasi
PHA NASA yang berbasis orbital jangka panjang.
""")

st.caption("Pilih halaman dari sidebar untuk mulai eksplorasi →")