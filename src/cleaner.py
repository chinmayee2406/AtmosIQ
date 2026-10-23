"""
Data Cleaning and Validation Pipeline for AtmosIQ
Handles schema enforcement, safe datetime conversion, physical bounds checks,
missing value imputation, duplicate removal, and derived meteorological features.
"""

import os
import logging
from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def assign_indian_season(month: int) -> str:
    """
    Classify calendar month into standard Indian meteorological seasons:
    - Winter: December to February
    - Pre-Monsoon (Summer): March to May
    - Monsoon (Southwest): June to September
    - Post-Monsoon: October to November
    """
    if month in (12, 1, 2):
        return "Winter"
    elif month in (3, 4, 5):
        return "Pre-Monsoon"
    elif month in (6, 7, 8, 9):
        return "Monsoon"
    else:
        return "Post-Monsoon"


def clean_weather_data(
    input_path: str = "data/raw/weather_data.csv",
    output_path: str = "data/processed/cleaned_weather.csv",
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Load raw weather records, apply validation and cleaning rules,
    engineer derived temporal/meteorological features, and export clean dataset.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Raw data file not found at {input_path}")

    raw_df = pd.read_csv(input_path)
    initial_count = len(raw_df)

    # 1. Consistent and safe datetime conversion (avoids .dt accessor issues)
    df = raw_df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    null_dates = df["date"].isna().sum()
    df = df.dropna(subset=["date", "city"])

    # 2. Duplicate detection and deduplication
    duplicate_count = df.duplicated(subset=["city", "date"]).sum()
    df = df.drop_duplicates(subset=["city", "date"], keep="first")

    # 3. Numeric conversion and physical bounds enforcement
    numeric_cols = ["temp_mean", "temp_max", "temp_min", "precipitation", "wind_speed_max"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Invert temp_min / temp_max if physically inverted
    inverted_mask = df["temp_min"] > df["temp_max"]
    if inverted_mask.any():
        logger.warning("Found %d records with temp_min > temp_max; correcting...", inverted_mask.sum())
        real_min = np.minimum(df.loc[inverted_mask, "temp_min"], df.loc[inverted_mask, "temp_max"])
        real_max = np.maximum(df.loc[inverted_mask, "temp_min"], df.loc[inverted_mask, "temp_max"])
        df.loc[inverted_mask, "temp_min"] = real_min
        df.loc[inverted_mask, "temp_max"] = real_max

    # Non-negative precipitation and wind speed
    if "precipitation" in df.columns:
        df["precipitation"] = df["precipitation"].clip(lower=0.0)
    if "wind_speed_max" in df.columns:
        df["wind_speed_max"] = df["wind_speed_max"].clip(lower=0.0)

    # 4. Missing value handling per city using forward/backward fill for short gaps
    cleaned_city_dfs = []
    total_interpolated = 0
    for city, city_df in df.groupby("city"):
        city_sorted = city_df.sort_values("date").set_index("date")

        # Reindex to full expected daily date range to identify missing dates
        if not city_sorted.empty:
            full_idx = pd.date_range(start=city_sorted.index.min(), end=city_sorted.index.max(), freq="D")
            city_reindexed = city_sorted.reindex(full_idx)
            city_reindexed["city"] = city
            if "latitude" in city_sorted.columns:
                city_reindexed["latitude"] = city_sorted["latitude"].iloc[0]
            if "longitude" in city_sorted.columns:
                city_reindexed["longitude"] = city_sorted["longitude"].iloc[0]
            if "elevation" in city_sorted.columns:
                city_reindexed["elevation"] = city_sorted["elevation"].iloc[0]

            # Interpolate small gaps up to 3 days
            missing_before = city_reindexed[numeric_cols].isna().sum().sum()
            city_reindexed[numeric_cols] = city_reindexed[numeric_cols].interpolate(method="time", limit=3)
            # Fill any remaining edge NaNs with bfill/ffill
            city_reindexed[numeric_cols] = city_reindexed[numeric_cols].bfill().ffill()
            missing_after = city_reindexed[numeric_cols].isna().sum().sum()
            total_interpolated += (missing_before - missing_after)

            city_reindexed = city_reindexed.reset_index().rename(columns={"index": "date"})
            cleaned_city_dfs.append(city_reindexed)

    if cleaned_city_dfs:
        df = pd.concat(cleaned_city_dfs, ignore_index=True)
    else:
        df = df.sort_values(["city", "date"]).reset_index(drop=True)

    # 5. Derived temporal & meteorological features
    # Ensure date is strictly datetime64
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["day"] = df["date"].dt.day
    df["day_of_year"] = df["date"].dt.day_of_year
    df["season"] = df["month"].apply(assign_indian_season)
    df["temp_range"] = (df["temp_max"] - df["temp_min"]).round(2)
    df["is_rain_day"] = (df["precipitation"] >= 1.0).astype(int)
    df["is_heavy_rain"] = (df["precipitation"] >= 50.0).astype(int)

    # 6. Save clean dataset
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)

    summary = {
        "initial_raw_records": initial_count,
        "final_clean_records": len(df),
        "null_dates_dropped": int(null_dates),
        "duplicates_removed": int(duplicate_count),
        "values_interpolated": int(total_interpolated),
        "cities": sorted(df["city"].unique().tolist()),
        "date_range": [str(df["date"].min().date()), str(df["date"].max().date())],
        "output_path": output_path,
    }
    logger.info("Cleaning complete. Processed %d records across %d cities.", len(df), len(summary["cities"]))
    return df, summary


if __name__ == "__main__":
    clean_weather_data()
