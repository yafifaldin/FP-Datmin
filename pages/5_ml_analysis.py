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
st.title("Data Mining Exploration")
st.markdown("""
Eksplorasi struktur data asteroid menggunakan unsupervised clustering (K-Means)
dan eksperimen korelasi via supervised classification (Logistic Regression,
Decision Tree, Random Forest).
""")

st.divider()

# ── Konteks Awal ──────────────────────────────────────────────────────────────
st.subheader("📍 Konteks & Keterbatasan Metodologi")

st.markdown("""
Sebelum menampilkan hasil, penting untuk eksplisit tentang **apa yang halaman ini lakukan
dan tidak lakukan**.
""")

st.warning("""
**Keterbatasan inheren:** Prediktor yang tersedia di NASA NeoWs API (diameter, velocity,
miss_distance_au, magnitude) **berbeda** dari prediktor yang NASA gunakan dalam rule PHA
(MOID + H). MOID tidak tersedia di NeoWs API.

**Konsekuensinya:**
- Classification di halaman ini **bukan** audit terhadap rule NASA — kalau model gagal
  mereplikasi label NASA, itu wajar karena prediktornya memang berbeda
- Clustering memberi label cluster berdasarkan **karakteristik centroid** (Large/Fast/Close
  dst), bukan interpretasi "risk" yang subjektif
- Yang valid dipelajari adalah: **pola pengelompokan alami asteroid** dan **sejauh mana
  fitur pendekatan aktual berkorelasi dengan klasifikasi orbital NASA**
""")

st.divider()

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=7200, show_spinner="Loading data for analysis...")
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
    st.warning("Not enough data for analysis.")
    st.stop()

X = df_ml[features].values
y = df_ml["is_hazardous"].astype(int).values

n_total = len(df_ml)
n_haz = int(y.sum())
n_nonhaz = n_total - n_haz

st.markdown(f"""
**Dataset:** {n_total} asteroid dari endpoint `browse` NASA  
**Distribusi class:** {n_haz} hazardous ({n_haz/n_total*100:.1f}%) vs {n_nonhaz} non-hazardous ({n_nonhaz/n_total*100:.1f}%) — moderately imbalanced
""")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1: CLUSTERING
# ═══════════════════════════════════════════════════════════════════════════════
st.subheader("🔵 Section 1 — K-Means Clustering")

st.markdown("""
**Tujuan:** Mengelompokkan asteroid berdasarkan kemiripan karakteristik fisik aktual,
tanpa menggunakan label NASA sama sekali. Murni eksplorasi struktur alami data.

**Yang diharapkan dipelajari:** Pola pengelompokan asteroid berdasarkan empat dimensi
karakteristik fisik. Setelah cluster terbentuk, kita overlay label NASA untuk melihat
**apakah ada korelasi** — bukan untuk klaim NASA salah atau benar.
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
Elbow method menguji k=2 sampai k=7. Kami memilih **k=3** sebagai jalan tengah antara
kesederhanaan (k=2 terlalu mirip label biner NASA) dan granularitas (k=4+ terlalu sulit
diinterpretasikan secara substantif).
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

# Auto-label clusters by characteristic, not subjective risk
# Logic: smallest diameter + slowest + farthest = "Small Slow Distant"
#        largest diameter + fastest + closest = "Large Fast Close"
sort_key = (
    centroid_df["diameter_km"].rank(ascending=True) +
    centroid_df["velocity_kms"].rank(ascending=True) +
    (1 / centroid_df["miss_distance_au"]).rank(ascending=True)
).sort_values()

ordered_clusters = sort_key.index.tolist()
char_labels = {
    ordered_clusters[0]: "Small · Slow · Distant",
    ordered_clusters[1]: "Mid-range",
    ordered_clusters[2]: "Large · Fast · Close",
}
df_ml["cluster_label"] = df_ml["cluster"].map(char_labels)

cluster_colors = {
    "Small · Slow · Distant": "#06b6d4",
    "Mid-range": "#7c3aed",
    "Large · Fast · Close": "#e040fb",
}

st.markdown("**Step 2: Karakteristik tiap cluster yang terbentuk**")
st.markdown("""
Setiap cluster diberi nama deskriptif berdasarkan nilai centroid masing-masing — bukan
interpretasi "risk" yang subjektif. Nama hanya mencerminkan apa adanya dari data:
ukuran rata-rata, kecepatan rata-rata, jarak rata-rata.
""")

centroid_display = centroid_df.round(4)
centroid_display.columns = ["Diameter (km)", "Velocity (km/s)", "Miss Dist (AU)", "Magnitude"]
centroid_display.insert(0, "Cluster", [char_labels[i] for i in range(3)])
order_map = {"Small · Slow · Distant": 0, "Mid-range": 1, "Large · Fast · Close": 2}
centroid_display = centroid_display.sort_values("Cluster", key=lambda x: x.map(order_map))
st.dataframe(centroid_display, use_container_width=True, hide_index=True)

# Scatter
st.markdown("**Step 3: Visualisasi cluster di feature space**")
st.markdown("""
Scatter plot di bawah menunjukkan distribusi asteroid pada dua dimensi utama
(miss distance vs velocity), dengan warna mewakili cluster hasil K-Means.
Ukuran titik proporsional dengan diameter.
""")

fig_cluster = go.Figure()
for label in ["Small · Slow · Distant", "Mid-range", "Large · Fast · Close"]:
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
Tabel di bawah menunjukkan berapa asteroid dari tiap cluster yang di-label hazardous
oleh NASA. Pertanyaan yang bisa dijawab: **apakah ada korelasi antara karakteristik
fisik pendekatan dengan klasifikasi orbital NASA?**

Karena prediktor kami (miss_distance_au) berbeda dari yang NASA pakai (MOID), kami
**tidak mengharapkan** korelasi sempurna. Yang kami lihat adalah: pada cluster mana
asteroid hazardous NASA cenderung berkumpul.
""")

crosstab = pd.crosstab(
    df_ml["cluster_label"],
    df_ml["is_hazardous"].map({True: "Hazardous", False: "Non-Hazardous"}),
)
crosstab = crosstab.reindex(["Small · Slow · Distant", "Mid-range", "Large · Fast · Close"])
st.dataframe(crosstab, use_container_width=True)

lfc_count = len(df_ml[df_ml["cluster_label"] == "Large · Fast · Close"])
lfc_haz = len(df_ml[(df_ml["cluster_label"] == "Large · Fast · Close") & (df_ml["is_hazardous"])])
lfc_pct = (lfc_haz / max(lfc_count, 1)) * 100

ssd_count = len(df_ml[df_ml["cluster_label"] == "Small · Slow · Distant"])
ssd_haz = len(df_ml[(df_ml["cluster_label"] == "Small · Slow · Distant") & (df_ml["is_hazardous"])])
ssd_pct = (ssd_haz / max(ssd_count, 1)) * 100

st.info(f"""
**Observasi:**

- **Large · Fast · Close** ({lfc_count} asteroid): **{lfc_haz} ({lfc_pct:.0f}%)** di-label hazardous NASA
- **Small · Slow · Distant** ({ssd_count} asteroid): **{ssd_haz} ({ssd_pct:.0f}%)** di-label hazardous NASA

**Interpretasi (tanpa overclaim):** Korelasi antara karakteristik fisik dan label NASA
ada, tapi tidak sempurna. Ini wajar karena dua sistem klasifikasi (pendekatan aktual
vs orbital jangka panjang) mengukur dimensi yang berbeda — bukan indikasi salah satunya
salah.
""")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2: CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════════════════
st.subheader("🟣 Section 2 — Classification (Eksperimen Korelasi)")

st.markdown("""
**Tujuan:** Mengukur sejauh mana fitur pendekatan aktual (diameter, velocity,
miss_distance_au, magnitude) berkorelasi dengan label PHA NASA. Tiga model dengan
kompleksitas berbeda digunakan untuk melihat konsistensi pola.

**Yang BUKAN tujuan kami:** Membuktikan rule NASA salah atau benar. Karena prediktor
berbeda dari awal, model yang gagal mereplikasi label NASA bukan bukti inkonsistensi NASA —
itu hanya menunjukkan bahwa kedua sistem mengukur hal yang berbeda.
""")

with st.expander("📖 Penjelasan tiap model"):
    st.markdown("""
    **Logistic Regression (LR)** — Model paling sederhana, asumsi hubungan linear antara
    fitur dan target. Berfungsi sebagai **baseline**.
    
    **Decision Tree (DT)** — Belajar rule berbasis threshold seperti "jika X < a dan Y < b
    maka hazardous". Mirip dengan cara NASA mengklasifikasi (threshold-based).
    
    **Random Forest (RF)** — Ensemble dari banyak decision tree. Biasanya lebih akurat,
    tapi pada dataset kecil bisa overfit dan kalah dari model sederhana.
    """)

if y.sum() < 2:
    st.warning("Not enough hazardous samples for classification.")
    st.stop()

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.25, random_state=42, stratify=y
)

models = {
    "Logistic Regression": LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42),
    "Decision Tree": DecisionTreeClassifier(class_weight="balanced", max_depth=3, random_state=42),
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
untuk memprediksi label NASA. Ini menunjukkan **fitur pendekatan aktual mana yang
paling berkorelasi dengan klasifikasi orbital NASA** — bukan fitur yang NASA pakai
secara langsung (NASA pakai MOID yang tidak ada di data kami).
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
**Interpretasi:**
- Fitur paling berkorelasi dengan label NASA: **{top_feature}** ({top_importance:.3f})
- Velocity importance: **{velocity_importance:.3f}**

Hasil ini konsisten dengan ekspektasi — magnitude (satu-satunya fitur yang overlap dengan
prediktor NASA H) menjadi salah satu yang paling penting. Velocity berkorelasi lemah
karena memang tidak ada di rule NASA.
""")

# Confusion matrix
best_model_name = results_df.sort_values("F1-Score", ascending=False).iloc[0]["Model"]
best_f1 = results_df[results_df["Model"] == best_model_name]["F1-Score"].values[0]

st.markdown(f"**Step 4: Confusion Matrix — {best_model_name} (F1 tertinggi: {best_f1:.3f})**")
st.markdown(f"""
Confusion matrix model dengan F1 terbaik. F1 dipilih sebagai kriteria karena data
imbalanced — accuracy bisa misleading.

- **TP** — hazardous, diprediksi hazardous ✅
- **TN** — non-haz, diprediksi non-haz ✅
- **FP** — non-haz, diprediksi hazardous (false alarm)
- **FN** — hazardous, diprediksi non-haz (miss detection)
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

st.info(f"""
**Interpretasi (jujur tanpa overclaim):**

F1-Score terbaik adalah **{best_f1:.3f}** — menunjukkan korelasi moderat antara fitur
pendekatan aktual dengan label PHA NASA. Bukan korelasi sempurna, dan **tidak diharapkan**
sempurna karena prediktor yang dipakai berbeda dari rule NASA.

Yang bisa disimpulkan: fitur pendekatan aktual menangkap **sebagian** sinyal yang ada di
label NASA — kemungkinan melalui korelasi tidak langsung (asteroid dengan MOID rendah
cenderung juga punya miss_distance rendah pada banyak pendekatan).
""")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# CONCLUSION
# ═══════════════════════════════════════════════════════════════════════════════
st.subheader("🎯 Kesimpulan Eksplorasi")

st.markdown(f"""
**Dari Clustering:**  
Asteroid mengelompok secara alami ke dalam 3 cluster berdasarkan karakteristik fisik —
Small/Slow/Distant, Mid-range, dan Large/Fast/Close. Korelasi dengan label hazardous NASA
ada tapi tidak sempurna ({lfc_pct:.0f}% hazardous di cluster Large/Fast/Close).

**Dari Classification:**  
Fitur pendekatan aktual (diameter, velocity, miss_distance, magnitude) berkorelasi
**moderat** dengan label NASA — F1-Score terbaik {best_f1:.3f}. Korelasi sempurna tidak
diharapkan karena prediktor berbeda dari rule NASA.
""")

st.success("""
**Posisi akhir yang jujur:**

Analisis di halaman ini **tidak** memberikan bukti bahwa rule NASA salah atau inkonsisten —
karena prediktor yang kami punya berbeda dari yang NASA pakai. Yang dipelajari adalah
bahwa fitur pendekatan aktual dan klasifikasi orbital NASA mengukur dimensi risiko yang
berbeda namun memiliki korelasi moderat.

**Kontribusi utama dashboard ini tetap pada Composite Risk Score di Page 2** — metrik
alternatif berbasis pendekatan aktual yang memasukkan velocity, melengkapi (bukan
menggantikan) klasifikasi PHA NASA yang berbasis orbital jangka panjang.
""")