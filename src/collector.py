"""
Data Collection Module for AtmosIQ
Fetches historical daily weather data from the Open-Meteo Historical Weather API.
Supports resumable, year-by-year collection with exponential backoff and rate limit handling.
"""

import os
import time
import logging
from typing import Dict, Any, List, Optional, Set, Tuple
import requests
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "https://archive-api.open-meteo.com/v1/archive"

CITIES: Dict[str, Dict[str, Any]] = {
    "Hyderabad": {"latitude": 17.3850, "longitude": 78.4867, "elevation": 542},
    "Bengaluru": {"latitude": 12.9716, "longitude": 77.5946, "elevation": 920},
    "Chennai": {"latitude": 13.0827, "longitude": 80.2707, "elevation": 6},
    "Mumbai": {"latitude": 19.0760, "longitude": 72.8777, "elevation": 14},
    "Delhi": {"latitude": 28.6139, "longitude": 77.2090, "elevation": 216},
}

API_VARIABLES = [
    "temperature_2m_mean",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "wind_speed_10m_max",
]

COLUMN_MAPPING = {
    "time": "date",
    "temperature_2m_mean": "temp_mean",
    "temperature_2m_max": "temp_max",
    "temperature_2m_min": "temp_min",
    "precipitation_sum": "precipitation",
    "wind_speed_10m_max": "wind_speed_max",
}


def fetch_city_year(
    city: str,
    coords: Dict[str, Any],
    year: int,
    session: Optional[requests.Session] = None,
    max_retries: int = 5,
    backoff_factor: float = 1.5,
    timeout: int = 20,
) -> Optional[pd.DataFrame]:
    """
    Fetch daily weather data for a single city and single year.
    Implements exponential backoff and rate-limit handling.
    """
    s = session or requests.Session()
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"

    params = {
        "latitude": coords["latitude"],
        "longitude": coords["longitude"],
        "start_date": start_date,
        "end_date": end_date,
        "daily": ",".join(API_VARIABLES),
        "timezone": "auto",
    }

    for attempt in range(1, max_retries + 1):
        try:
            resp = s.get(BASE_URL, params=params, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                if "daily" not in data or "time" not in data["daily"]:
                    logger.warning("No daily data in API response for %s %d", city, year)
                    return None

                daily_dict = data["daily"]
                df = pd.DataFrame(daily_dict)
                df = df.rename(columns=COLUMN_MAPPING)

                # Robust datetime conversion to prevent .dt accessor errors
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                df = df.dropna(subset=["date"])

                # Add metadata columns
                df["city"] = city
                df["latitude"] = coords["latitude"]
                df["longitude"] = coords["longitude"]
                df["elevation"] = coords.get("elevation", np.nan)

                return df

            elif resp.status_code == 429:
                sleep_time = backoff_factor ** attempt + 2.0
                logger.warning("Rate limited (429) for %s %d. Retrying in %.1fs (attempt %d/%d)...",
                               city, year, sleep_time, attempt, max_retries)
                time.sleep(sleep_time)

            elif resp.status_code == 400:
                # May occur if end_date is beyond available archive
                err_msg = resp.text
                logger.warning("API returned 400 for %s %d: %s", city, year, err_msg)
                return None

            else:
                sleep_time = backoff_factor ** attempt
                logger.warning("HTTP %d for %s %d. Retrying in %.1fs...",
                               resp.status_code, city, year, sleep_time)
                time.sleep(sleep_time)

        except (requests.RequestException, Exception) as exc:
            sleep_time = backoff_factor ** attempt
            logger.warning("Request error for %s %d: %s. Retrying in %.1fs...",
                           city, year, exc, sleep_time)
            time.sleep(sleep_time)

    logger.error("Failed to fetch data for %s %d after %d attempts", city, year, max_retries)
    return None


def get_existing_coverage(csv_path: str) -> Tuple[Set[Tuple[str, int]], Optional[pd.DataFrame]]:
    """
    Inspect existing CSV and determine which (city, year) pairs are already complete.
    Safely converts date column to datetime to avoid .dt errors.
    """
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
        return set(), None

    try:
        df = pd.read_csv(csv_path)
        if df.empty or "city" not in df.columns or "date" not in df.columns:
            return set(), None

        # Convert date safely to datetime
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        valid_df = df.dropna(subset=["date", "city"])

        # Count records per city-year
        valid_df = valid_df.copy()
        valid_df["year"] = valid_df["date"].dt.year
        counts = valid_df.groupby(["city", "year"]).size()

        # Consider a year complete if it has >= 350 valid daily records (allowing for leap years or minor missing days)
        complete_pairs = set()
        for (c, y), cnt in counts.items():
            if cnt >= 350:
                complete_pairs.add((c, int(y)))

        logger.info("Found %d completed (city, year) chunks in existing dataset (%s)",
                    len(complete_pairs), csv_path)
        return complete_pairs, df

    except Exception as exc:
        logger.warning("Could not parse existing CSV at %s: %s", csv_path, exc)
        return set(), None


def collect_historical_weather(
    output_path: str = "data/raw/weather_data.csv",
    start_year: int = 2000,
    end_year: int = 2025,
    delay_between_requests: float = 0.35,
) -> pd.DataFrame:
    """
    Resumable historical weather data collection for all target cities.
    Saves validated records to output_path.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    existing_pairs, existing_df = get_existing_coverage(output_path)

    dfs: List[pd.DataFrame] = []
    if existing_df is not None and not existing_df.empty:
        existing_df["date"] = pd.to_datetime(existing_df["date"], errors="coerce")
        dfs.append(existing_df.dropna(subset=["date", "city"]))

    session = requests.Session()
    total_chunks = len(CITIES) * (end_year - start_year + 1)
    current_chunk = 0
    new_chunks_collected = 0

    logger.info("Starting data collection for %d cities across %d-%d (%d total chunks)...",
                len(CITIES), start_year, end_year, total_chunks)

    for city, coords in CITIES.items():
        for year in range(start_year, end_year + 1):
            current_chunk += 1
            if (city, year) in existing_pairs:
                logger.debug("[%d/%d] Skipping %s %d (already collected)", current_chunk, total_chunks, city, year)
                continue

            logger.info("[%d/%d] Fetching %s %d...", current_chunk, total_chunks, city, year)
            chunk_df = fetch_city_year(city, coords, year, session=session)

            if chunk_df is not None and not chunk_df.empty:
                dfs.append(chunk_df)
                new_chunks_collected += 1

                # Incremental persistence every 5 new chunks to avoid data loss
                if new_chunks_collected % 5 == 0:
                    combined = pd.concat(dfs, ignore_index=True)
                    combined["date"] = pd.to_datetime(combined["date"], errors="coerce")
                    combined = combined.drop_duplicates(subset=["city", "date"]).sort_values(["city", "date"])
                    combined.to_csv(output_path, index=False)
                    logger.info("Progress saved: %d records in %s", len(combined), output_path)

            time.sleep(delay_between_requests)

    if not dfs:
        raise RuntimeError("No weather data collected and no existing data found.")

    final_df = pd.concat(dfs, ignore_index=True)
    final_df["date"] = pd.to_datetime(final_df["date"], errors="coerce")
    final_df = final_df.dropna(subset=["date", "city"])
    final_df = final_df.drop_duplicates(subset=["city", "date"]).sort_values(["city", "date"]).reset_index(drop=True)

    final_df.to_csv(output_path, index=False)
    logger.info("Collection complete. Saved %d validated records to %s", len(final_df), output_path)
    return final_df


if __name__ == "__main__":
    collect_historical_weather()
