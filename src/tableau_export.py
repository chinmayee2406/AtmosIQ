"""
Tableau Public Data Preparation Pipeline for AtmosIQ
Exports clean, structured, and aggregated CSV datasets tailored for Tableau Public dashboards:
1. tableau_daily_weather.csv (Granular daily weather records with geo-coordinates)
2. tableau_monthly_trends.csv (Aggregated monthly & seasonal trends)
3. tableau_city_anomalies.csv (Climate anomaly events and severity classifications)
"""

import os
import logging
from typing import Dict, Any
import pandas as pd
from src.database import query_weather, get_connection
from src.anomaly import detect_climate_anomalies

logger = logging.getLogger(__name__)


def generate_tableau_exports(
    db_path: str = "data/atmosiq.db",
    output_dir: str = "data/tableau",
) -> Dict[str, str]:
    """
    Generate three optimized CSV files for Tableau Public visualization.
    """
    os.makedirs(output_dir, exist_ok=True)

    # 1. Daily Weather Dataset with City Metadata
    with get_connection(db_path) as conn:
        daily_df = pd.read_sql_query("""
            SELECT
                w.city,
                w.date,
                w.temp_mean,
                w.temp_max,
                w.temp_min,
                w.precipitation,
                w.wind_speed_max,
                w.temp_range,
                w.season,
                w.is_rain_day,
                w.is_heavy_rain,
                m.latitude,
                m.longitude,
                m.elevation,
                m.state,
                m.climate_zone
            FROM weather_daily w
            LEFT JOIN city_metadata m ON w.city = m.city
            ORDER BY w.city, w.date
        """, conn)

    daily_path = os.path.join(output_dir, "tableau_daily_weather.csv")
    daily_df.to_csv(daily_path, index=False)
    logger.info("Exported %d daily records to %s", len(daily_df), daily_path)

    # 2. Monthly Trends Dataset
    daily_df["date"] = pd.to_datetime(daily_df["date"])
    daily_df["year"] = daily_df["date"].dt.year
    daily_df["month"] = daily_df["date"].dt.month
    daily_df["year_month"] = daily_df["date"].dt.strftime("%Y-%m-01")

    monthly_df = daily_df.groupby([
        "city", "state", "climate_zone", "latitude", "longitude",
        "year", "month", "year_month", "season"
    ]).agg(
        avg_temp_mean=("temp_mean", "mean"),
        avg_temp_max=("temp_max", "mean"),
        avg_temp_min=("temp_min", "mean"),
        total_precipitation=("precipitation", "sum"),
        rain_days=("is_rain_day", "sum"),
        heavy_rain_days=("is_heavy_rain", "sum"),
        max_wind_speed=("wind_speed_max", "max"),
        record_high_temp=("temp_max", "max"),
        record_low_temp=("temp_min", "min"),
    ).reset_index()

    for col in ["avg_temp_mean", "avg_temp_max", "avg_temp_min", "total_precipitation", "max_wind_speed"]:
        monthly_df[col] = monthly_df[col].round(2)

    monthly_path = os.path.join(output_dir, "tableau_monthly_trends.csv")
    monthly_df.to_csv(monthly_path, index=False)
    logger.info("Exported %d monthly records to %s", len(monthly_df), monthly_path)

    # 3. Climate Anomalies Dataset
    _, events_df = detect_climate_anomalies(daily_df)
    anomalies_path = os.path.join(output_dir, "tableau_city_anomalies.csv")
    events_df.to_csv(anomalies_path, index=False)
    logger.info("Exported %d anomaly records to %s", len(events_df), anomalies_path)

    return {
        "daily_weather": daily_path,
        "monthly_trends": monthly_path,
        "city_anomalies": anomalies_path,
    }


if __name__ == "__main__":
    generate_tableau_exports()
