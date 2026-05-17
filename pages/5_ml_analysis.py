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

st.markdown("""
<p class="page-eyebrow">Earth's Threat Monitor &nbsp;·&nbsp; 05</p>
<h1 class="page-title">Machine Learning Analysis</h1>
<p class="page-subtitle">
    Audit kuantitatif klasifikasi NASA menggunakan unsupervised clustering (K-Means)
    dan supervised classification (Logistic Regression, Decision Tree, Random Forest).
</p>
""", unsafe_allow_html=True)

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

# Clean for ML
features = ["diameter_km", "velocity_kms", "miss_distance_au", "magnitude"]
df_ml = df.dropna(subset=features + ["is_hazardous"]).reset_index(drop=True)
df_ml = df_ml[df_ml["diameter_km"] > 0].reset_index(drop=True)

if len(df_ml) < 20:
    st.warning("Not enough data for ML analysis.")
    st.stop()

X = df_ml[features].values
y = df_ml["is_hazardous"].astype(int).values

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1: CLUSTERING
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<p class="section-label">Section 1 — K-Means Clustering</p>', unsafe_allow_html=True)

st.markdown("""
Apakah asteroid secara alami terbagi dalam kelompok yang selaras
dengan klasifikasi NASA, atau pola data menunjukkan struktur yang berbeda?
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

col_a, col_b = st.columns([1, 1], gap="large")

with col_a:
    st.markdown("**Elbow Method — Penentuan k Optimal**")
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

# Cluster centroids in original scale
centroids_scaled = kmeans.cluster_centers_
centroids_original = scaler.inverse_transform(centroids_scaled)
centroid_df = pd.DataFrame(centroids_original, columns=features)
centroid_df.index = [f"Cluster {i}" for i in range(3)]

# Auto-label clusters by risk
risk_avg = df_ml.groupby("cluster").apply(
    lambda g: (g["diameter_km"].mean() * g["velocity_kms"].mean()) / (g["miss_distance_au"].mean() + 1e-9)
)
sorted_clusters = risk_avg.sort_values().index.tolist()
cluster_labels = {sorted_clusters[0]: "Low Risk", sorted_clusters[1]: "Medium Risk", sorted_clusters[2]: "High Risk"}
df_ml["cluster_label"] = df_ml["cluster"].map(cluster_labels)

cluster_colors = {"Low Risk": "#06b6d4", "Medium Risk": "#7c3aed", "High Risk": "#e040fb"}

with col_b:
    st.markdown("**Karakteristik Centroid per Cluster**")
    centroid_display = centroid_df.round(4)
    centroid_display.columns = ["Diameter (km)", "Velocity (km/s)", "Miss Dist (AU)", "Magnitude"]
    centroid_display["Label"] = [cluster_labels[i] for i in range(3)]
    st.dataframe(centroid_display, use_container_width=True, height=200)

# Scatter: cluster visualization
st.markdown("**Visualisasi Cluster — Velocity vs. Miss Distance**")
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

# Crosstab: cluster vs hazardous
st.markdown("**Crosstab — Cluster vs. Label Hazardous NASA**")
crosstab = pd.crosstab(
    df_ml["cluster_label"],
    df_ml["is_hazardous"].map({True: "Hazardous", False: "Non-Hazardous"}),
)
crosstab = crosstab.reindex(["Low Risk", "Medium Risk", "High Risk"])
st.dataframe(crosstab, use_container_width=True)

# Analysis
high_risk_count = len(df_ml[df_ml["cluster_label"] == "High Risk"])
high_risk_haz = len(df_ml[(df_ml["cluster_label"] == "High Risk") & (df_ml["is_hazardous"])])
high_risk_pct = (high_risk_haz / max(high_risk_count, 1)) * 100

st.markdown(f"""
<div class="callout">
    Dari <b>{high_risk_count}</b> asteroid yang masuk cluster <span class="callout-accent">High Risk</span>,
    hanya <b>{high_risk_haz} ({high_risk_pct:.0f}%)</b> yang di-label hazardous oleh NASA.
    Ini menunjukkan bahwa pola alami data tidak sepenuhnya selaras dengan klasifikasi NASA —
    ada asteroid yang secara karakteristik fisik masuk kategori berisiko tinggi
    namun tidak memenuhi kriteria PHA NASA (MOID ≤ 0.05 AU dan H ≤ 22.0).
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2: CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<p class="section-label">Section 2 — Classification: Model Comparison</p>', unsafe_allow_html=True)

st.markdown("""
Bisakah model machine learning belajar dan mereplikasi klasifikasi NASA
hanya dari data fisik asteroid? Tiga model dibandingkan: Logistic Regression (baseline),
Decision Tree (interpretable), Random Forest (ensemble utama).
""")

# Train-test split
if y.sum() < 2:
    st.warning("Not enough hazardous samples for classification.")
    st.stop()

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.25, random_state=42, stratify=y
)

# Train models
models = {
    "Logistic Regression": LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42),
    "Decision Tree": DecisionTreeClassifier(class_weight="balanced", max_depth=5, random_state=42),
    "Random Forest": RandomForestClassifier(class_weight="balanced", n_estimators=100, max_depth=8, random_state=42),
}

# Scale only for LR
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

st.markdown("**Tabel Perbandingan Metrik**")
display_results = results_df.copy()
for col in ["Accuracy", "Precision", "Recall", "F1-Score"]:
    display_results[col] = display_results[col].apply(lambda x: f"{x:.3f}")
st.dataframe(display_results, use_container_width=True, hide_index=True)

# Metrics bar chart
st.markdown("**Visualisasi Perbandingan Metrik**")
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

# Feature importance (RF)
st.markdown("**Feature Importance — Random Forest**")
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
st.markdown(f"""
<div class="callout">
    Fitur paling berpengaruh dalam prediksi klasifikasi NASA adalah
    <b>{top_feature}</b>. Ini sejalan dengan kriteria PHA NASA yang berbasis
    MOID (jarak orbit) dan absolute magnitude — keduanya berkorelasi langsung
    dengan fitur-fitur tersebut.
</div>
""", unsafe_allow_html=True)

# Confusion matrix for best model
best_model_name = results_df.sort_values("F1-Score", ascending=False).iloc[0]["Model"]
st.markdown(f"**Confusion Matrix — {best_model_name} (Best F1-Score)**")

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

# False positives — asteroids predicted hazardous but NASA says no
test_indices = np.arange(len(y_test))
fp_mask = (y_pred_best == 1) & (y_test == 0)
fp_count = fp_mask.sum()

if fp_count > 0:
    st.markdown(f"""
    <div class="callout">
        <b>{fp_count}</b> asteroid(s) diprediksi <span class="callout-accent">hazardous</span> oleh model
        namun tidak di-label hazardous oleh NASA. Objek-objek ini memiliki karakteristik fisik
        (diameter, velocity, miss distance, magnitude) yang mirip dengan asteroid hazardous,
        meski tidak memenuhi kriteria formal PHA NASA — kandidat yang patut diperhatikan
        lebih lanjut.
    </div>
    """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# CONCLUSION
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<p class="section-label">Kesimpulan Analisis</p>', unsafe_allow_html=True)

st.markdown(f"""
<div class="stats-box">
    <div class="stats-box-title">Temuan Utama</div>
    <div class="stats-interpret">
        <b>1. Clustering:</b> Hanya {high_risk_pct:.0f}% dari cluster High Risk yang
        di-label hazardous oleh NASA — menunjukkan ketidakselarasan antara pola alami
        data dengan klasifikasi NASA.<br><br>
        <b>2. Classification:</b> Model {best_model_name} memberikan performa terbaik
        dengan F1-Score {results_df.sort_values('F1-Score', ascending=False).iloc[0]['F1-Score']:.3f}.
        Fitur paling berpengaruh adalah <b>{top_feature}</b>.<br><br>
        <b>3. Implikasi:</b> Label hazardous NASA merupakan klasifikasi berbasis threshold
        orbital yang deterministik, namun tidak selalu mencerminkan tingkat ancaman dinamis
        pada pendekatan spesifik. Composite Risk Score yang dikembangkan di Page 2,
        dikombinasikan dengan audit ML ini, menyediakan perspektif yang lebih komprehensif
        untuk menilai ancaman asteroid.
    </div>
</div>
""", unsafe_allow_html=True)