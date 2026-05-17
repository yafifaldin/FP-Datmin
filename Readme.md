# ☄️ Earth's Threat Monitor

Dashboard analisis data Near-Earth Object (NEO) yang membangun perspektif alternatif untuk
menilai ancaman asteroid berbasis data karakteristik pendekatan aktual — sebagai pelengkap
klasifikasi PHA (Potentially Hazardous Asteroid) milik NASA yang menggunakan kriteria
orbital jangka panjang.

---

## 📌 Latar Belakang

NASA mengklasifikasikan asteroid sebagai **Potentially Hazardous Asteroid (PHA)**
berdasarkan dua kriteria orbital:

- **MOID ≤ 0.05 AU** — Minimum Orbit Intersection Distance, jarak orbital minimum dengan Bumi
- **H ≤ 22.0** — Absolute magnitude, setara diameter ≥ 140 meter

Klasifikasi tersebut menjawab pertanyaan: *"Apakah orbit asteroid ini berpotensi memotong
orbit Bumi dalam jangka panjang?"*

Namun MOID dan H secara fundamental **tidak mengandung velocity** — MOID adalah kalkulasi
geometris orbital murni, dan H adalah proxy ukuran fisik. Padahal secara fisika, energi
kinetik dampak ditentukan oleh kecepatan (½ × m × v²). Asteroid kecil tapi sangat cepat
bisa lebih destruktif dari asteroid besar tapi lambat.

Dashboard ini dibangun untuk mengeksplorasi gap tersebut menggunakan data publik dari
NASA NeoWs API.

---

## 🎯 Tujuan

- Membangun **Composite Risk Score** sebagai metrik alternatif yang memasukkan velocity
  dan kondisi pendekatan aktual
- Mengeksplorasi struktur alami data asteroid menggunakan **K-Means clustering**
- Mengukur korelasi antara fitur pendekatan aktual dengan label PHA NASA menggunakan
  **classification** (Logistic Regression, Decision Tree, Random Forest)
- Memberikan visualisasi real-time data NEO yang sedang mendekati Bumi

---

## 🛠️ Tech Stack

| Layer | Tools |
|---|---|
| Backend & API | Python, `requests`, `python-dotenv` |
| Data Processing | `pandas`, `numpy` |
| Visualization | `plotly`, `streamlit` |
| Machine Learning | `scikit-learn`, `scipy` |
| Deployment | Streamlit Cloud (opsional) |

---

## 📂 Struktur Project

```
FP-Datmin/
├── app.py                        # Entry point — landing page
├── pages/
│   ├── 1_overview.py             # Live NEO feed 7 hari
│   ├── 2_risk_analysis.py        # Composite Risk Score
│   ├── 3_orbital_deepdive.py     # Analisis per kelas orbit + Kruskal-Wallis
│   ├── 4_historical_trend.py     # Tren 6 bulan terakhir
│   └── 5_ml_analysis.py          # K-Means clustering & classification
├── utils/
│   ├── fetch_data.py             # API calls ke NASA NeoWs
│   ├── clean_data.py             # Parsing & feature engineering
│   └── scoring.py                # Composite Risk Score
├── assets/
│   └── style.css                 # Dark theme styling
├── data/
│   └── cache.pkl                 # Cache historical data (auto-generated)
├── .streamlit/
│   └── config.toml               # Streamlit theme config
├── .env.example                  # Template API key
├── requirements.txt              # Dependencies
└── README.md
```

---

## 🚀 Cara Menjalankan

### 1. Clone repository

```bash
git clone https://github.com/yafifaldin/FP-Datmin.git
cd FP-Datmin
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Setup API key

Daftar gratis di https://api.nasa.gov/ untuk mendapatkan API key.

Buat file `.env` di root project:

```env
NASA_API_KEY=your_api_key_here
```

Atau pakai `DEMO_KEY` (rate-limited 30 request/jam) — dashboard akan otomatis fallback
ke demo key jika `.env` tidak ada.

### 4. Run dashboard

```bash
streamlit run app.py
```

Browser akan otomatis terbuka di `http://localhost:8501`.

---

## 📊 Halaman Dashboard

### `01` — Live NEO Feed
Snapshot real-time asteroid yang mendekati Bumi dalam 7 hari ke depan. Empat metric
utama (jumlah total, hazardous count, peak velocity, closest pass), bar chart distribusi
per hari, dan tabel interaktif dengan highlight untuk objek di bawah 5 Lunar Distance.

### `02` — Risk Analysis
Penerapan Composite Risk Score = `(diameter × velocity) / miss_distance` pada data
minggu ini. Scatter plot multivariabel (velocity vs miss distance, ukuran = diameter,
warna = hazardous NASA), ranking top-15 berdasarkan risk score, dan donut chart
distribusi risiko.

### `03` — Orbital Deep Dive
Analisis berdasarkan kelas orbit asteroid (Apollo, Amor, Aten, Atira). Violin plot
distribusi velocity per kelas, stacked bar proporsi hazardous, dan uji statistik
**Kruskal-Wallis H-test** untuk verifikasi signifikansi perbedaan velocity antar kelas.

### `04` — Historical Trends
Tren 6 bulan terakhir dari data pendekatan asteroid. Line chart monthly average
miss distance, histogram distribusi diameter (log scale), dan bar chart frekuensi
pendekatan sangat dekat (< 10 Lunar Distance) per bulan.

### `05` — Data Mining Exploration
Dua analisis data mining yang saling melengkapi:

- **K-Means Clustering** — Pengelompokan asteroid berdasarkan kemiripan karakteristik
  fisik (diameter, velocity, miss_distance, magnitude) tanpa menggunakan label NASA.
  Cluster diberi nama berdasarkan karakteristik centroid (`Small · Slow · Distant`,
  `Mid-range`, `Large · Fast · Close`).
- **Classification (LR vs DT vs RF)** — Eksperimen korelasi antara fitur pendekatan
  aktual dengan label PHA NASA. Tiga model dengan kompleksitas berbeda dibandingkan
  via accuracy, precision, recall, dan F1-score.

---

## 🔬 Metodologi

### Composite Risk Score

```
Risk Score = (diameter_km × velocity_kms) / (miss_distance_au + ε)
```

- **Pembilang** — proxy energi kinetik (semakin besar dan cepat, semakin berbahaya)
- **Penyebut** — jarak aktual (semakin dekat, semakin meningkatkan risk score)
- **ε** = 1e-9, untuk mencegah pembagian dengan nol

### K-Means Clustering

- **Feature scaling** — `StandardScaler` wajib karena skala antar fitur berbeda drastis
- **Pemilihan k** — Elbow method menguji k=2 sampai k=7, dipilih k=3 sebagai jalan
  tengah antara kesederhanaan dan granularitas
- **Cluster labeling** — Berdasarkan nilai centroid masing-masing, bukan interpretasi
  risiko subjektif

### Classification

Tiga model dilatih dengan train-test split 75:25 (stratified):

| Model | Hyperparameter |
|---|---|
| Logistic Regression | `class_weight='balanced'`, `max_iter=1000` |
| Decision Tree | `class_weight='balanced'`, `max_depth=3` |
| Random Forest | `class_weight='balanced'`, `n_estimators=100`, `max_depth=8` |

Karena data imbalanced (~28% hazardous), F1-Score digunakan sebagai kriteria utama
evaluasi — bukan accuracy yang bisa misleading.

---

## ⚠️ Keterbatasan Metodologi

Prediktor yang tersedia di NASA NeoWs API berbeda dari prediktor yang NASA gunakan
dalam rule PHA:

| Fitur NASA | Fitur di Dashboard | Overlap |
|---|---|---|
| MOID (jarak orbital minimum) | `miss_distance_au` (jarak aktual) | ❌ Berbeda |
| H (absolute magnitude) | `magnitude` | ✅ Sama |
| — | `diameter_km` | Turunan dari H |
| — | `velocity_kms` | Tidak ada di rule NASA |

Konsekuensinya:

- Classification di dashboard ini **bukan** audit terhadap rule NASA — karena prediktor
  berbeda, ketidaksempurnaan replikasi label NASA adalah konsekuensi metodologis yang
  diharapkan
- Yang dapat dipelajari adalah: **pola pengelompokan alami asteroid** dan **sejauh mana
  fitur pendekatan aktual berkorelasi dengan klasifikasi orbital NASA**
- Kontribusi utama dashboard ini ada pada Composite Risk Score sebagai metrik pelengkap,
  bukan pada klaim audit ML

---

## 📡 Data Source

NASA Near Earth Object Web Service (NeoWs) — https://api.nasa.gov/

Dua endpoint yang digunakan:

- **`/feed`** — Data pendekatan asteroid dalam window 7 hari, refresh tiap jam via
  `@st.cache_data(ttl=3600)`
- **`/browse`** — Database historis lengkap dengan informasi orbital class, di-cache
  lokal sebagai `.pkl`

---

## 🎨 Design System

Dashboard menggunakan dark theme dengan palette:

| Color | Hex | Penggunaan |
|---|---|---|
| Background | `#0d0d1f` | Background utama |
| Card | `#0f0f26` | Card / panel |
| Cyan | `#00d4ff` | Accent primer, neutral data |
| Purple | `#7c3aed` | Accent sekunder |
| Magenta | `#e040fb` | Highlight, hazardous, risk |
| Text | `#ffffff` | Teks utama |

Semua chart Plotly menggunakan template `plotly_dark` dengan override warna sesuai palette.

---

## 📝 Catatan

Project ini dibuat sebagai final project untuk mata kuliah Data Mining. Fokus utama
pada eksplorasi pipeline data science end-to-end: API integration, data cleaning,
feature engineering, statistical testing, machine learning, dan visualisasi
interaktif — dalam konteks domain astronomi yang konkret dan terbatas datanya.

---

## 📄 License

MIT License — bebas digunakan untuk keperluan akademik dan pembelajaran.
