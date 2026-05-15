import pandas as pd
import numpy as np


def compute_risk_score(
    diameter_km: float,
    velocity_kms: float,
    miss_distance_au: float,
) -> float:
    """
    Simple composite risk score.
    Higher = more threatening.
    """
    return (diameter_km * velocity_kms) / (miss_distance_au + 1e-9)


def add_risk_score(df: pd.DataFrame) -> pd.DataFrame:
    """Append a risk_score column to the DataFrame."""
    df = df.copy()
    df["risk_score"] = df.apply(
        lambda r: compute_risk_score(
            r["diameter_km"], r["velocity_kms"], r["miss_distance_au"]
        ),
        axis=1,
    )
    return df


def risk_label(score: float, q75: float, q25: float) -> str:
    if score >= q75:
        return "High"
    if score >= q25:
        return "Medium"
    return "Low"


def add_risk_label(df: pd.DataFrame) -> pd.DataFrame:
    """Append a risk_label column based on quartile thresholds."""
    if "risk_score" not in df.columns:
        df = add_risk_score(df)
    q75 = df["risk_score"].quantile(0.75)
    q25 = df["risk_score"].quantile(0.25)
    df = df.copy()
    df["risk_label"] = df["risk_score"].apply(
        lambda s: risk_label(s, q75, q25)
    )
    return df
