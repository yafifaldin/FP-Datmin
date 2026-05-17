import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix
)

from utils.fetch_data import get_browse
from utils.clean_data import parse_browse
from utils.scoring import add_risk_score

def _inject_css():
    p = Path(__file__).parent.parent / "assets" / "style.css"
    if p.exists():
        with open(p, encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

_inject_css()

st.caption("EARTH'S THREAT MONITOR  ·  05")
st.title("Machine Learning Analysis")
st.markdown("""
Audit kuantitatif klasifikasi PHA NASA menggunakan unsupervised clustering (K-Means)
dan supervised classification (Logistic Regression, Decision Tree, Random Forest).
""")

st.divider()

# ── Konteks Awal ──────────────────────────────────────────────────────────────
st.subheader("📍 Konteks: Apa yang Kita Audit?")

st.markdown("""
Di halaman sebelumnya kita sudah menemukan **observasi awal**: ada asteroid dengan
Composite Risk Score tinggi yang tidak di-label hazardous oleh NASA. Halaman ini
mengubah observasi tersebut menjadi **bukti kuantitatif** melalui dua metode ML.

**Yang penting dipahami:** Kita tidak mengaudit perhitungan fisika orbital NASA — itu
sudah presisi dan tidak perlu dipertanyakan. Yang kita audit adalah **keputusan
klasifikasinya** — apakah threshold MOID ≤ 0.05 AU dan H ≤ 22 mencerminkan pola
yang ada di data fisik asteroid?
""")

st.info("""
**Fitur yang NASA pakai dalam rule PHA:** MOID (jarak orbital) + H (magnitude)

**Fitur yang kita pakai di ML:** diameter, velocity, miss_distance, magnitude

**Gap utama:** Velocity tidak ada di rule NASA, tapi secara fisika krusial untuk
menentukan energi kinetik dampak.
""")

st.divider()

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=7200, show_spinner="Loading data for ML analysis...")
def load_data(pages: int = 8) -> pd.DataFrame:
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
    df = add_risk_score(df)
    return df

df = load_data()
if df.empty:
    st.warning("No data could be loaded.")
    st.stop()

features = ["diameter_km", "velocity_kms", "miss_distance_au", "magnitude"]
df_ml = df.dropna(subset=features + ["is_hazardous"]).reset_index(drop=True)
df_ml = df_ml[df_ml["diameter_km"] > 0].reset_index(drop=True)

if len(df_ml) < 20:
    st.warning("Not enough data for ML analysis.")
    st.stop()

X = df_ml[features].values
y = df_ml["is_hazardous"].astype(int).values

n_total = len(df_ml)
n_haz = int(y.sum())
n_nonhaz = n_total - n_haz

st.markdown(f"""
**Dataset:** {n_total} asteroid dari endpoint `browse` NASA  
**Imbalanced class:** {n_haz} hazardous ({n_haz/n_total*100:.1f}%) vs {n_nonhaz} non-hazardous ({n_nonhaz/n_total*100:.1f}%)
""")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1: CLUSTERING
# ═══════════════════════════════════════════════════════════════════════════════
st.subheader("🔵 Section 1 — K-Means Clustering")

st.markdown("""
**Logika audit:** K-Means tidak tahu label NASA sama sekali. Dia hanya melihat fitur fisik
asteroid dan mengelompokkan secara alami berdasarkan kemiripan. Setelah cluster terbentuk,
kita overlay label NASA ke atasnya.

**Apa yang dicari:** Apakah cluster "High Risk" yang terbentuk dari data secara alami
selaras dengan asteroid yang di-label hazardous NASA?
- Kalau **selaras** → klasifikasi NASA konsisten dengan struktur data
- Kalau **tidak selaras** → label NASA tidak mencerminkan pola alami data
""")

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Elbow method
inertias = []
k_range = range(2, 8)
for k in k_range:
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    km.fit(X_scaled)
    inertias.append(km.inertia_)

st.markdown("**Step 1: Penentuan jumlah cluster optimal (Elbow Method)**")
st.markdown("""
Elbow method menguji k=2 sampai k=7, mengukur inertia (seberapa rapat tiap cluster).
Kita memilih k=3 — bukan k=2 yang terlalu mirip label biner NASA, dan bukan k=4 ke atas
yang terlalu granular untuk diinterpretasikan.
""")

fig_elbow = go.Figure(go.Scatter(
    x=list(k_range), y=inertias,
    mode="lines+markers",
    line=dict(color="#00d4ff", width=2, shape="spline"),
    marker=dict(color="#00d4ff", size=8, line=dict(color="#0d0d1f", width=2)),
    hovertemplate="k=%{x}<br>Inertia: %{y:.2f}<extra></extra>",
))
fig_elbow.add_vline(
    x=3, line=dict(color="#e040fb", width=1, dash="dot"),
    annotation_text="k = 3 dipilih",
    annotation_font=dict(color="#e040fb", size=11),
    annotation_position="top right",
)
fig_elbow.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#ffffff", size=11),
    xaxis=dict(title="Jumlah Cluster (k)", gridcolor="#161630",
               tickfont=dict(color="#ffffff"), zeroline=False),
    yaxis=dict(title="Inertia", gridcolor="#161630",
               tickfont=dict(color="#ffffff"), zeroline=False),
    margin=dict(l=0, r=0, t=10, b=0),
    height=300,
)
st.plotly_chart(fig_elbow, use_container_width=True)

# Fit K-Means with k=3
kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
clusters = kmeans.fit_predict(X_scaled)
df_ml["cluster"] = clusters

centroids_scaled = kmeans.cluster_centers_
centroids_original = scaler.inverse_transform(centroids_scaled)
centroid_df = pd.DataFrame(centroids_original, columns=features)

# Auto-label clusters by risk
risk_avg = df_ml.groupby("cluster").apply(
    lambda g: (g["diameter_km"].mean() * g["velocity_kms"].mean()) / (g["miss_distance_au"].mean() + 1e-9)
)
sorted_clusters = risk_avg.sort_values().index.tolist()
cluster_labels = {sorted_clusters[0]: "Low Risk", sorted_clusters[1]: "Medium Risk", sorted_clusters[2]: "High Risk"}
df_ml["cluster_label"] = df_ml["cluster"].map(cluster_labels)

cluster_colors = {"Low Risk": "#06b6d4", "Medium Risk": "#7c3aed", "High Risk": "#e040fb"}

st.markdown("**Step 2: Karakteristik tiap cluster yang terbentuk**")
st.markdown("""
Setelah K-Means konvergen, tiap cluster punya centroid yang merepresentasikan asteroid
"tipikal" dari kelompok tersebut. Label Low/Medium/High Risk ditentukan berdasarkan
nilai centroid masing-masing.
""")

centroid_display = centroid_df.round(4)
centroid_display.columns = ["Diameter (km)", "Velocity (km/s)", "Miss Dist (AU)", "Magnitude"]
centroid_display.insert(0, "Cluster", [cluster_labels[i] for i in range(3)])
centroid_display = centroid_display.sort_values("Cluster", key=lambda x: x.map({"Low Risk": 0, "Medium Risk": 1, "High Risk": 2}))
st.dataframe(centroid_display, use_container_width=True, hide_index=True)

# Scatter
st.markdown("**Step 3: Visualisasi cluster di feature space**")
st.markdown("""
Scatter plot di bawah menunjukkan distribusi asteroid pada dua dimensi utama
(miss distance dan velocity), dengan warna mewakili cluster hasil K-Means.
Ukuran titik proporsional dengan diameter.
""")

fig_cluster = go.Figure()
for label in ["Low Risk", "Medium Risk", "High Risk"]:
    subset = df_ml[df_ml["cluster_label"] == label]
    fig_cluster.add_trace(go.Scatter(
        x=subset["miss_distance_au"],
        y=subset["velocity_kms"],
        mode="markers",
        name=label,
        marker=dict(
            size=subset["diameter_km"].clip(upper=2) * 8 + 5,
            color=cluster_colors[label],
            opacity=0.7,
            line=dict(color="#0d0d1f", width=1),
        ),
        text=subset["name"],
        customdata=subset["is_hazardous"],
        hovertemplate="<b>%{text}</b><br>" +
                      "Miss: %{x:.4f} AU<br>" +
                      "Vel: %{y:.1f} km/s<br>" +
                      "NASA Hazardous: %{customdata}<extra></extra>",
    ))
fig_cluster.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#ffffff", size=11),
    xaxis=dict(title="Miss Distance (AU)", gridcolor="#161630",
               tickfont=dict(color="#ffffff"), zeroline=False),
    yaxis=dict(title="Velocity (km/s)", gridcolor="#161630",
               tickfont=dict(color="#ffffff"), zeroline=False),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#ffffff")),
    margin=dict(l=0, r=0, t=10, b=0),
    height=400,
)
st.plotly_chart(fig_cluster, use_container_width=True)

# Crosstab
st.markdown("**Step 4: Crosstab cluster vs label hazardous NASA**")
st.markdown("""
Inilah inti audit clustering. Tabel di bawah menunjukkan berapa asteroid dari tiap cluster
yang di-label hazardous oleh NASA. Kalau klasifikasi NASA konsisten dengan pola data,
cluster High Risk harusnya didominasi asteroid hazardous.
""")

crosstab = pd.crosstab(
    df_ml["cluster_label"],
    df_ml["is_hazardous"].map({True: "Hazardous", False: "Non-Hazardous"}),
)
crosstab = crosstab.reindex(["Low Risk", "Medium Risk", "High Risk"])
st.dataframe(crosstab, use_container_width=True)

high_risk_count = len(df_ml[df_ml["cluster_label"] == "High Risk"])
high_risk_haz = len(df_ml[(df_ml["cluster_label"] == "High Risk") & (df_ml["is_hazardous"])])
high_risk_pct = (high_risk_haz / max(high_risk_count, 1)) * 100

st.warning(f"""
**Temuan Clustering:** Dari **{high_risk_count}** asteroid yang masuk cluster High Risk,
hanya **{high_risk_haz} ({high_risk_pct:.0f}%)** yang di-label hazardous oleh NASA.

**Interpretasi:** Mayoritas asteroid di cluster High Risk — yang secara karakteristik fisik
(besar, cepat, dekat) seharusnya berisiko — justru **tidak** masuk klasifikasi PHA NASA.
Ini bukti pertama bahwa pola data fisik tidak selaras dengan rule NASA.
""")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2: CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════════════════
st.subheader("🟣 Section 2 — Classification (3 Model Comparison)")

st.markdown("""
**Logika audit:** Kalau rule NASA sederhana dan konsisten dengan data, model ML harusnya
bisa belajar mereplikasi rule tersebut dengan mudah. Kalau model konsisten kesulitan,
berarti rule NASA mengandung informasi yang tidak ada di fitur fisik dasar.

**Mengapa 3 model?** Tiap model punya asumsi berbeda — kalau ketiganya menghasilkan
pola yang sama, kesimpulan jauh lebih kuat dibanding satu model saja.
""")

with st.expander("📖 Penjelasan tiap model"):
    st.markdown("""
    **Logistic Regression (LR)** — Model paling sederhana, asumsi hubungan linear antara
    fitur dan target. Berfungsi sebagai **baseline**.
    
    **Decision Tree (DT)** — Belajar rule berbasis threshold seperti "jika MOID < X dan H < Y
    maka hazardous". Paling mirip dengan cara NASA mengklasifikasi.
    
    **Random Forest (RF)** — Ensemble dari banyak decision tree. Biasanya lebih akurat
    karena bisa menangkap interaksi antar fitur. Tapi pada dataset kecil, kadang
    overfit dan kalah dari model sederhana.
    """)

if y.sum() < 2:
    st.warning("Not enough hazardous samples for classification.")
    st.stop()

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.25, random_state=42, stratify=y
)

models = {
    "Logistic Regression": LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42),
    "Decision Tree": DecisionTreeClassifier(class_weight="balanced", max_depth=5, random_state=42),
    "Random Forest": RandomForestClassifier(class_weight="balanced", n_estimators=100, max_depth=8, random_state=42),
}

scaler_clf = StandardScaler()
X_train_scaled = scaler_clf.fit_transform(X_train)
X_test_scaled = scaler_clf.transform(X_test)

results = []
predictions = {}
for name, model in models.items():
    if name == "Logistic Regression":
        model.fit(X_train_scaled, y_train)
        y_pred = model.predict(X_test_scaled)
    else:
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
    predictions[name] = y_pred
    results.append({
        "Model": name,
        "Accuracy": accuracy_score(y_test, y_pred),
        "Precision": precision_score(y_test, y_pred, zero_division=0),
        "Recall": recall_score(y_test, y_pred, zero_division=0),
        "F1-Score": f1_score(y_test, y_pred, zero_division=0),
    })

results_df = pd.DataFrame(results)

st.markdown("**Step 1: Tabel perbandingan metrik tiga model**")
st.markdown("""
- **Accuracy** — total prediksi benar / total prediksi (kurang reliable untuk imbalanced data)
- **Precision** — dari yang diprediksi hazardous, berapa yang benar
- **Recall** — dari yang sebenarnya hazardous, berapa yang berhasil terdeteksi
- **F1-Score** — harmonic mean precision dan recall (paling reliable untuk imbalanced data)
""")

display_results = results_df.copy()
for col in ["Accuracy", "Precision", "Recall", "F1-Score"]:
    display_results[col] = display_results[col].apply(lambda x: f"{x:.3f}")
st.dataframe(display_results, use_container_width=True, hide_index=True)

st.markdown("**Step 2: Visualisasi metrik per model**")

metrics_long = results_df.melt(id_vars="Model", var_name="Metric", value_name="Score")
fig_metrics = px.bar(
    metrics_long, x="Metric", y="Score", color="Model",
    barmode="group",
    color_discrete_map={
        "Logistic Regression": "#06b6d4",
        "Decision Tree": "#7c3aed",
        "Random Forest": "#e040fb",
    },
)
fig_metrics.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#ffffff", size=11),
    xaxis=dict(tickfont=dict(color="#ffffff"), showgrid=False),
    yaxis=dict(title="Score", gridcolor="#161630",
               tickfont=dict(color="#ffffff"), zeroline=False, range=[0, 1.05]),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#ffffff")),
    margin=dict(l=0, r=0, t=10, b=0),
    height=320,
)
st.plotly_chart(fig_metrics, use_container_width=True)

# Feature importance
st.markdown("**Step 3: Feature Importance dari Random Forest**")
st.markdown("""
Feature importance menunjukkan fitur mana yang paling sering dipakai Random Forest
untuk memprediksi label NASA. Ini secara tidak langsung menunjukkan fitur mana
yang paling berkorelasi dengan rule NASA.
""")

rf = models["Random Forest"]
importance_df = pd.DataFrame({
    "Feature": features,
    "Importance": rf.feature_importances_,
}).sort_values("Importance", ascending=True)

fig_imp = go.Figure(go.Bar(
    x=importance_df["Importance"], y=importance_df["Feature"],
    orientation="h",
    marker=dict(color="#e040fb", opacity=0.8, line=dict(color="rgba(0,0,0,0)", width=0)),
    hovertemplate="<b>%{y}</b><br>Importance: %{x:.4f}<extra></extra>",
))
fig_imp.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#ffffff", size=11),
    xaxis=dict(title="Importance", gridcolor="#161630",
               tickfont=dict(color="#ffffff"), zeroline=False),
    yaxis=dict(tickfont=dict(color="#ffffff", size=11)),
    margin=dict(l=0, r=0, t=10, b=0),
    height=280,
)
st.plotly_chart(fig_imp, use_container_width=True)

top_feature = importance_df.iloc[-1]["Feature"]
top_importance = importance_df.iloc[-1]["Importance"]
velocity_importance = importance_df[importance_df["Feature"] == "velocity_kms"]["Importance"].values[0]

st.markdown(f"""
**Interpretasi Feature Importance:**
- Fitur paling berpengaruh: **{top_feature}** (importance: {top_importance:.3f})
- Velocity importance: **{velocity_importance:.3f}**

Ini sejalan dengan kriteria PHA NASA — fitur yang paling penting adalah yang berkorelasi
dengan MOID dan H. Velocity, meski secara fisika krusial untuk energi dampak, kurang
berpengaruh dalam memprediksi label NASA — karena memang tidak ada di rule mereka.
""")

# Confusion matrix
best_model_name = results_df.sort_values("F1-Score", ascending=False).iloc[0]["Model"]
best_f1 = results_df[results_df["Model"] == best_model_name]["F1-Score"].values[0]

st.markdown(f"**Step 4: Confusion Matrix — {best_model_name} (F1 tertinggi: {best_f1:.3f})**")
st.markdown(f"""
Confusion matrix menunjukkan detail prediksi vs reality untuk model dengan F1 terbaik.
Kita pilih berdasarkan F1, bukan accuracy, karena data imbalanced.

- **TP** (True Positive) — hazardous, diprediksi hazardous ✅
- **TN** (True Negative) — non-haz, diprediksi non-haz ✅
- **FP** (False Positive) — non-haz, diprediksi hazardous (false alarm)
- **FN** (False Negative) — hazardous, diprediksi non-haz (paling berbahaya — miss!)
""")

y_pred_best = predictions[best_model_name]
cm = confusion_matrix(y_test, y_pred_best)

cm_labels = [["TN", "FP"], ["FN", "TP"]]
cm_text = [[f"{cm_labels[i][j]}<br>{cm[i][j]}" for j in range(2)] for i in range(2)]

fig_cm = go.Figure(go.Heatmap(
    z=cm,
    x=["Predicted Non-Haz", "Predicted Hazardous"],
    y=["Actual Non-Haz", "Actual Hazardous"],
    text=cm_text,
    texttemplate="%{text}",
    textfont=dict(color="#ffffff", size=14),
    colorscale=[[0, "#0c0c22"], [1, "#e040fb"]],
    showscale=False,
    hovertemplate="%{y}<br>%{x}<br>Count: %{z}<extra></extra>",
))
fig_cm.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#ffffff", size=11),
    xaxis=dict(tickfont=dict(color="#ffffff"), side="bottom"),
    yaxis=dict(tickfont=dict(color="#ffffff")),
    margin=dict(l=0, r=0, t=10, b=0),
    height=320,
)
st.plotly_chart(fig_cm, use_container_width=True)

fp_count = int(((y_pred_best == 1) & (y_test == 0)).sum())
fn_count = int(((y_pred_best == 0) & (y_test == 1)).sum())

st.warning(f"""
**Temuan Classification:** F1-Score terbaik hanya **{best_f1:.3f}** — model konsisten
kesulitan mereplikasi label NASA secara presisi dari fitur fisik saja. Khususnya:

- **{fp_count} asteroid** diprediksi hazardous oleh model **tapi NASA bilang tidak** —
  kandidat yang fitur fisiknya mirip hazardous tapi tidak memenuhi threshold MOID NASA.
  
- **{fn_count} asteroid** sebenarnya hazardous tapi model gagal mendeteksi — menunjukkan
  bahwa label NASA mengandung informasi orbital yang tidak ada di fitur fisik dasar kami.

**Interpretasi:** Rule NASA berbasis fitur orbital (MOID) yang tidak ada di dataset kami,
sehingga model dari diameter + velocity + miss_distance + magnitude saja tidak cukup
untuk replikasi sempurna. Tapi justru di sini letak temuan analitiknya — fitur fisik
aktual dan rule orbital NASA memang dua hal yang berbeda.
""")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# CONCLUSION
# ═══════════════════════════════════════════════════════════════════════════════
st.subheader("🎯 Kesimpulan Audit ML")

st.markdown(f"""
Dua pendekatan ML dari arah yang berbeda menghasilkan kesimpulan yang konsisten:

**Dari Clustering (bottom-up):**  
Hanya {high_risk_pct:.0f}% asteroid di cluster High Risk yang di-label hazardous NASA.
Pola alami data tidak selaras dengan klasifikasi NASA.

**Dari Classification (top-down):**  
F1-Score terbaik hanya {best_f1:.3f}. Model kesulitan mempelajari rule NASA dari
fitur fisik dasar, mengindikasikan rule NASA mengandung informasi yang tidak
sepenuhnya tertangkap dari diameter, velocity, miss_distance, dan magnitude.
""")

st.success("""
**Kesimpulan Final:** Klasifikasi PHA NASA didasarkan pada **fitur orbital jangka panjang
(MOID)** yang berbeda dari **fitur fisik pendekatan aktual** (diameter, velocity, miss_distance).
Keduanya bukan saling bertentangan — melainkan menjawab pertanyaan yang berbeda:

- **NASA:** "Apakah orbit asteroid ini berpotensi memotong orbit Bumi dalam ratusan tahun?"
- **Risk Score kami:** "Seberapa berbahaya pendekatan asteroid ini hari ini?"

Audit ML ini memperkuat argumen bahwa **Composite Risk Score adalah pelengkap, bukan
pengganti**, klasifikasi PHA NASA — keduanya dibutuhkan untuk penilaian ancaman yang
komprehensif.
""")