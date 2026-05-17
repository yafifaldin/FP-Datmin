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
Dashboard ini bukan sekadar visualisasi data asteroid. Ini adalah **audit terhadap cara
NASA mengklasifikasikan asteroid berbahaya** — menggunakan data dari NASA NeoWs API itu sendiri,
ditambah teknik machine learning untuk menguji konsistensi klasifikasi tersebut.
""")

st.divider()

st.subheader("🎯 Pertanyaan Penelitian Utama")

st.markdown("""
NASA menetapkan asteroid sebagai **Potentially Hazardous Asteroid (PHA)** jika memenuhi dua kriteria:

- **MOID ≤ 0.05 AU** (jarak orbit minimum dengan orbit Bumi)
- **H ≤ 22.0** (absolute magnitude, setara diameter ≥ 140 meter)

Yang menarik: **kecepatan asteroid (velocity) tidak dipertimbangkan dalam kriteria ini sama sekali.**
Padahal secara fisika, energi kinetik dampak ditentukan oleh kecepatan (½ × m × v²).
""")

st.info("""
**Apakah kriteria klasifikasi NASA — yang berbasis threshold statis dan tidak memperhitungkan
velocity — konsisten dengan pola dinamis yang muncul dari data pendekatan aktual?**
""")

st.divider()

st.subheader("🔬 Pendekatan Analisis")

st.markdown("Dashboard ini menggunakan **tiga lapis analisis** yang saling menguatkan:")

col1, col2, col3 = st.columns(3, gap="medium")
with col1:
    st.markdown("**Lapis 1 — Deskriptif**")
    st.markdown("""
    Memvisualisasikan data asteroid langsung dari NASA NeoWs API — endpoint feed (7 hari
    ke depan) dan browse (historis). Untuk memahami struktur dan distribusi data.
    """)
with col2:
    st.markdown("**Lapis 2 — Risk Score**")
    st.markdown("""
    Membangun metrik alternatif **Composite Risk Score** = (diameter × velocity) / miss_distance,
    yang memasukkan velocity yang diabaikan NASA, dan menggunakan jarak aktual bukan orbital.
    """)
with col3:
    st.markdown("**Lapis 3 — ML Audit**")
    st.markdown("""
    Menggunakan **clustering (K-Means)** dan **classification (Logistic Regression, Decision Tree,
    Random Forest)** untuk menguji secara kuantitatif apakah pola data selaras dengan label NASA.
    """)

st.divider()

st.subheader("⚙️ Detail Teknis")

st.markdown("""
**Sumber Data:** NASA NeoWs API (https://api.nasa.gov/) — dua endpoint utama:
- `feed` → data pendekatan 7 hari ke depan, refresh tiap jam via `@st.cache_data(ttl=3600)`
- `browse` → database historis lengkap dengan informasi orbital class

**Pipeline:** `requests` → `pandas` (cleaning + feature engineering) → `plotly` (visualisasi) → `scikit-learn` (ML)

**Fitur yang dianalisis:**
- `diameter_km` — estimasi diameter asteroid (midpoint min-max NASA)
- `velocity_kms` — kecepatan relatif saat pendekatan
- `miss_distance_au` — jarak aktual saat pendekatan terdekat
- `magnitude` — absolute magnitude H

**Fitur yang dipakai NASA dalam rule PHA:**
- MOID (jarak orbital jangka panjang, bukan jarak aktual)
- H (magnitude)
- **Velocity tidak masuk rule NASA** ← ini gap yang kami eksploitasi
""")

st.divider()

st.subheader("📄 Navigasi Halaman")

st.markdown("**`01` — Live NEO Feed**")
st.markdown("""
**Apa yang ditampilkan:** Snapshot real-time semua asteroid yang akan mendekati Bumi dalam 7 hari ke depan.
Empat metric utama (jumlah, hazardous count, peak velocity, closest pass), distribusi per hari,
dan tabel interaktif lengkap.

**Apa yang dipelajari:** Konteks awal — seberapa banyak asteroid yang lewat tiap minggu,
seberapa besar, seberapa cepat, seberapa dekat. Tabel ini juga jadi titik awal untuk
melihat asteroid spesifik yang nanti kembali muncul di analisis risk score.
""")

st.markdown("**`02` — Risk Analysis**")
st.markdown("""
**Apa yang ditampilkan:** Composite Risk Score diterapkan ke data minggu ini.
Scatter plot multivariabel (velocity vs miss distance, ukuran = diameter, warna = hazardous NASA),
ranking top-15 berdasarkan risk score, dan donut chart distribusi risiko.

**Apa yang dipelajari:** Temuan awal — beberapa asteroid dengan risk score tinggi
**tidak di-label hazardous oleh NASA.** Ini observasi yang memunculkan pertanyaan:
apakah klasifikasi NASA memang tidak konsisten? Pertanyaan ini yang dijawab page 5.
""")

st.markdown("**`03` — Orbital Deep Dive**")
st.markdown("""
**Apa yang ditampilkan:** Analisis berdasarkan kelas orbit asteroid (Apollo, Amor, Aten, Atira).
Violin plot distribusi velocity per kelas, stacked bar proporsi hazardous, dan
**uji statistik Kruskal-Wallis** untuk verifikasi signifikansi perbedaan antar kelas.

**Apa yang dipelajari:** Apakah kelas orbit yang berbeda memiliki karakteristik velocity
yang berbeda secara signifikan? Kalau ya, ini bukti bahwa velocity adalah variabel
diskriminatif — yang seharusnya jadi pertimbangan dalam klasifikasi hazardous.
""")

st.markdown("**`04` — Historical Trends**")
st.markdown("""
**Apa yang ditampilkan:** Tren 6 bulan terakhir dari data pendekatan asteroid.
Line chart miss distance bulanan, histogram distribusi diameter (log scale),
dan frekuensi pendekatan sangat dekat (< 10 Lunar Distance) per bulan.

**Apa yang dipelajari:** Konteks temporal — apakah ada pola seasonal atau tren naik/turun
dalam frekuensi pendekatan. Berguna untuk memahami baseline normal sebelum menarik
kesimpulan tentang minggu tertentu.
""")

st.markdown("**`05` — Machine Learning Analysis**")
st.markdown("""
**Apa yang ditampilkan:** Audit kuantitatif klasifikasi NASA menggunakan dua pendekatan
ML yang saling menguatkan.

**Clustering (K-Means):** Mengelompokkan asteroid berdasarkan fitur fisik tanpa mengetahui
label NASA, lalu membandingkan apakah kelompok yang terbentuk selaras dengan klasifikasi NASA.

**Classification (LR vs DT vs RF):** Tiga model dilatih untuk mereplikasi label NASA dari
data fisik. Jika model konsisten kesulitan, itu bukti bahwa label NASA mengandung
informasi yang tidak tertangkap dari fitur fisik saja.

**Apa yang dipelajari:** Bukti kuantitatif final untuk argumen utama dashboard — pola data
fisik aktual tidak sepenuhnya selaras dengan rule PHA NASA, sehingga Composite Risk Score
yang memasukkan velocity menjadi pelengkap yang relevan untuk penilaian ancaman dinamis.
""")

st.divider()

st.subheader("🧵 Benang Merah Analisis")

st.markdown("Kelima halaman membentuk satu argumen utuh:")

st.markdown("""
1. **Page 1** menampilkan data sebagaimana adanya — apa yang sedang terjadi minggu ini
2. **Page 2** memperkenalkan Composite Risk Score dan menemukan **observasi awal**:
   ada asteroid dengan risk score tinggi yang tidak di-label hazardous oleh NASA
3. **Page 3** menunjukkan bahwa velocity (variabel yang NASA abaikan) sebenarnya **berbeda
   signifikan** antar kelas orbit — secara statistik terbukti diskriminatif
4. **Page 4** memberikan **konteks historis** — pola pendekatan asteroid selama 6 bulan
5. **Page 5** memberikan **bukti kuantitatif final** melalui ML — pola data dan rule NASA
   memang tidak sepenuhnya selaras
""")

st.success("""
**Kesimpulan akhir:** Klasifikasi PHA NASA optimal untuk tujuannya sendiri (potensi orbital
jangka panjang), tapi tidak menangkap dinamika ancaman pada pendekatan spesifik. Composite
Risk Score yang mempertimbangkan velocity dan jarak aktual mengisi gap analitik ini.
""")

st.caption("Pilih halaman dari sidebar untuk mulai eksplorasi →")