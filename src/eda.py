"""
Exploratory Data Analysis and Statistical Trend Analysis for AtmosIQ
Computes long-term warming trends, seasonal decompositions, rainfall distribution,
and city-to-city comparative statistics with rigorous p-values and confidence intervals.
Note: ERA5 values are reanalysis model estimates, not direct station observations.
"""

import logging
from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


def compute_temperature_trends(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate annual temperature trend slope (°C per decade), R-squared, and p-value
    for each city using ordinary least squares regression over annual means.
    """
    clean_df = df.copy()
    clean_df["date"] = pd.to_datetime(clean_df["date"])
    clean_df["year"] = clean_df["date"].dt.year

    annual = clean_df.groupby(["city", "year"]).agg(
        temp_mean=("temp_mean", "mean"),
        temp_max=("temp_max", "mean"),
        temp_min=("temp_min", "mean"),
        precipitation=("precipitation", "sum"),
    ).reset_index()

    trend_results = []
    for city, city_data in annual.groupby("city"):
        city_data = city_data.sort_values("year")
        x = city_data["year"].values
        y = city_data["temp_mean"].values

        if len(x) < 3:
            continue

        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        decadal_rate = slope * 10.0  # °C change per decade

        # Rainfall trend
        y_rain = city_data["precipitation"].values
        slope_rain, _, r_rain, p_rain, _ = stats.linregress(x, y_rain)

        trend_results.append({
            "city": city,
            "years_analyzed": f"{int(x.min())}-{int(x.max())}",
            "temp_mean_baseline": round(float(y.mean()), 2),
            "temp_trend_per_decade_degC": round(float(decadal_rate), 3),
            "temp_trend_r2": round(float(r_value ** 2), 4),
            "temp_trend_p_value": round(float(p_value), 4),
            "is_statistically_significant": bool(p_value < 0.05),
            "rain_trend_per_decade_mm": round(float(slope_rain * 10.0), 1),
            "rain_trend_p_value": round(float(p_rain), 4),
        })

    return pd.DataFrame(trend_results)


def compute_seasonal_profiles(df: pd.DataFrame) -> pd.DataFrame:
    """
    Summarize temperature and rainfall metrics by city and season.
    """
    clean_df = df.copy()
    clean_df["date"] = pd.to_datetime(clean_df["date"])

    profiles = clean_df.groupby(["city", "season"]).agg(
        avg_temp=("temp_mean", "mean"),
        avg_max_temp=("temp_max", "mean"),
        avg_min_temp=("temp_min", "mean"),
        daily_rainfall_avg=("precipitation", "mean"),
        total_heavy_rain_days=("is_heavy_rain", "sum"),
        avg_wind_speed=("wind_speed_max", "mean"),
    ).reset_index()

    for col in ["avg_temp", "avg_max_temp", "avg_min_temp", "daily_rainfall_avg", "avg_wind_speed"]:
        profiles[col] = profiles[col].round(2)

    return profiles


def compute_city_comparisons(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Generate city-to-city comparison metrics including diurnal range,
    monsoon concentration index, and climate extremes.
    """
    clean_df = df.copy()
    clean_df["date"] = pd.to_datetime(clean_df["date"])

    city_stats = {}
    for city, cdf in clean_df.groupby("city"):
        annual_rain = cdf.groupby(cdf["date"].dt.year)["precipitation"].sum()
        monsoon_rain = cdf[cdf["season"] == "Monsoon"].groupby(cdf["date"].dt.year)["precipitation"].sum()
        monsoon_pct = ((monsoon_rain / annual_rain) * 100).mean()

        city_stats[city] = {
            "mean_temp": round(float(cdf["temp_mean"].mean()), 2),
            "diurnal_range": round(float(cdf["temp_range"].mean()), 2),
            "annual_rainfall_mm": round(float(annual_rain.mean()), 1),
            "monsoon_rainfall_pct": round(float(monsoon_pct), 1) if not np.isnan(monsoon_pct) else 0.0,
            "record_high_temp": round(float(cdf["temp_max"].max()), 2),
            "record_low_temp": round(float(cdf["temp_min"].min()), 2),
            "max_single_day_rain_mm": round(float(cdf["precipitation"].max()), 1),
            "annual_rain_days": round(float(cdf.groupby(cdf["date"].dt.year)["is_rain_day"].sum().mean()), 1),
        }

    return city_stats
