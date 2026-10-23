"""
Climate Anomaly Detection Module for AtmosIQ
Computes baseline climatology, standardized anomalies (Z-scores),
and identifies extreme climate events (heatwaves, coldwaves, extreme rainfall)
following meteorological definitions (including IMD criteria where applicable).
"""

import logging
from typing import Tuple, Dict, Any
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def compute_baseline_climatology(
    df: pd.DataFrame,
    start_year: int = 2000,
    end_year: int = 2015,
    window: int = 7,
) -> pd.DataFrame:
    """
    Compute daily baseline climatology (mean and std) per city and day-of-year
    over a reference period (e.g., 2000-2015), smoothed over a centered rolling window.
    """
    clean_df = df.copy()
    clean_df["date"] = pd.to_datetime(clean_df["date"])
    clean_df["year"] = clean_df["date"].dt.year
    clean_df["doy"] = clean_df["date"].dt.day_of_year

    baseline_data = clean_df[(clean_df["year"] >= start_year) & (clean_df["year"] <= end_year)]
    if baseline_data.empty:
        baseline_data = clean_df  # Fallback if range unavailable

    # Group by city and day_of_year
    climo = (
        baseline_data.groupby(["city", "doy"])
        .agg(
            base_temp_mean=("temp_mean", "mean"),
            base_temp_std=("temp_mean", "std"),
            base_temp_max_p95=("temp_max", lambda s: np.percentile(s.dropna(), 95) if len(s.dropna()) else np.nan),
            base_temp_min_p05=("temp_min", lambda s: np.percentile(s.dropna(), 5) if len(s.dropna()) else np.nan),
            base_precip_p99=("precipitation", lambda s: np.percentile(s[s >= 1.0].dropna(), 99) if len(s[s >= 1.0].dropna()) > 5 else 50.0),
        )
        .reset_index()
    )

    # Smooth the daily baseline per city using a circular rolling average
    smoothed_climos = []
    for city, city_climo in climo.groupby("city"):
        city_climo = city_climo.sort_values("doy").copy()
        # Circular padding for seamless year-end transition
        padded = pd.concat([city_climo.tail(window), city_climo, city_climo.head(window)], ignore_index=True)
        for col in ["base_temp_mean", "base_temp_std", "base_temp_max_p95", "base_temp_min_p05"]:
            padded[col] = padded[col].rolling(window=window, center=True, min_periods=1).mean()
        smoothed = padded.iloc[window:-window].copy()
        smoothed_climos.append(smoothed)

    result = pd.concat(smoothed_climos, ignore_index=True)
    return result


def detect_climate_anomalies(
    df: pd.DataFrame,
    baseline_years: Tuple[int, int] = (2000, 2015),
    z_threshold: float = 2.0,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Detect temperature and precipitation anomalies against baseline climatology.
    Returns:
    1. full_anomalies_df: Original data merged with baseline departures and Z-scores
    2. events_df: Filtered high-severity events (heatwaves, coldwaves, extreme rain)
    """
    clean_df = df.copy()
    clean_df["date"] = pd.to_datetime(clean_df["date"])
    clean_df["doy"] = clean_df["date"].dt.day_of_year

    climo = compute_baseline_climatology(clean_df, start_year=baseline_years[0], end_year=baseline_years[1])
    merged = pd.merge(clean_df, climo, on=["city", "doy"], how="left")

    # Safe standard deviation fallback
    merged["base_temp_std"] = merged["base_temp_std"].replace(0, np.nan).fillna(1.5)

    # Temperature anomalies & Z-scores
    merged["temp_departure"] = merged["temp_mean"] - merged["base_temp_mean"]
    merged["temp_z_score"] = merged["temp_departure"] / merged["base_temp_std"]

    events = []

    for idx, row in merged.iterrows():
        # Heatwave check: T_max > 95th percentile and departure >= 3.0°C
        if row["temp_max"] >= row["base_temp_max_p95"] and row["temp_departure"] >= 3.0:
            severity = "Extreme" if row["temp_z_score"] >= 3.0 else "Severe" if row["temp_z_score"] >= 2.5 else "Moderate"
            events.append({
                "city": row["city"],
                "date": row["date"].strftime("%Y-%m-%d"),
                "anomaly_type": "Heatwave",
                "metric_value": round(float(row["temp_max"]), 2),
                "baseline_mean": round(float(row["base_temp_mean"]), 2),
                "deviation": round(float(row["temp_departure"]), 2),
                "z_score": round(float(row["temp_z_score"]), 2),
                "severity": severity,
            })

        # Coldwave check: T_min < 5th percentile and departure <= -3.0°C
        elif row["temp_min"] <= row["base_temp_min_p05"] and row["temp_departure"] <= -3.0:
            severity = "Extreme" if row["temp_z_score"] <= -3.0 else "Severe" if row["temp_z_score"] <= -2.5 else "Moderate"
            events.append({
                "city": row["city"],
                "date": row["date"].strftime("%Y-%m-%d"),
                "anomaly_type": "Coldwave",
                "metric_value": round(float(row["temp_min"]), 2),
                "baseline_mean": round(float(row["base_temp_mean"]), 2),
                "deviation": round(float(row["temp_departure"]), 2),
                "z_score": round(float(row["temp_z_score"]), 2),
                "severity": severity,
            })

        # Extreme precipitation: precipitation >= 50mm or > base_precip_p99
        if row["precipitation"] >= max(50.0, row["base_precip_p99"]):
            precip_dev = row["precipitation"] - row["base_precip_p99"]
            severity = "Extreme" if row["precipitation"] >= 100.0 else "Severe" if row["precipitation"] >= 75.0 else "Moderate"
            events.append({
                "city": row["city"],
                "date": row["date"].strftime("%Y-%m-%d"),
                "anomaly_type": "Extreme Rainfall",
                "metric_value": round(float(row["precipitation"]), 1),
                "baseline_mean": round(float(row["base_precip_p99"]), 1),
                "deviation": round(float(precip_dev), 1),
                "z_score": round(float(row["precipitation"] / 20.0), 2),  # Normalized index
                "severity": severity,
            })

    events_df = pd.DataFrame(events) if events else pd.DataFrame(columns=[
        "city", "date", "anomaly_type", "metric_value", "baseline_mean", "deviation", "z_score", "severity"
    ])

    return merged, events_df


def compute_annual_warming_stripes(df: pd.DataFrame, reference_years: Tuple[int, int] = (2000, 2015)) -> pd.DataFrame:
    """
    Compute annual mean temperature departure from the reference period
    for visualization as climate warming stripes.
    """
    clean_df = df.copy()
    clean_df["date"] = pd.to_datetime(clean_df["date"])
    clean_df["year"] = clean_df["date"].dt.year

    annual = clean_df.groupby(["city", "year"])["temp_mean"].mean().reset_index()

    # Calculate baseline mean per city
    ref = annual[(annual["year"] >= reference_years[0]) & (annual["year"] <= reference_years[1])]
    base_means = ref.groupby("city")["temp_mean"].mean().to_dict()

    annual["baseline_ref"] = annual["city"].map(base_means)
    annual["temp_anomaly"] = (annual["temp_mean"] - annual["baseline_ref"]).round(2)
    return annual
