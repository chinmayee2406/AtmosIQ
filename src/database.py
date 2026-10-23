"""
SQLite Database Management for AtmosIQ
Handles database initialization, schema creation, data ingestion, indexing, and reusable analytical queries.
"""

import os
import sqlite3
import logging
from typing import Dict, Any, List, Optional
import pandas as pd

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = "data/atmosiq.db"

CITY_METADATA_SEED = [
    {"city": "Hyderabad", "latitude": 17.3850, "longitude": 78.4867, "elevation": 542.0, "state": "Telangana", "climate_zone": "Semi-Arid (Tropical Savanna)"},
    {"city": "Bengaluru", "latitude": 12.9716, "longitude": 77.5946, "elevation": 920.0, "state": "Karnataka", "climate_zone": "Tropical Savanna (Moderate Elevation)"},
    {"city": "Chennai", "latitude": 13.0827, "longitude": 80.2707, "elevation": 6.0, "state": "Tamil Nadu", "climate_zone": "Tropical Wet & Dry (Coastal Maritime)"},
    {"city": "Mumbai", "latitude": 19.0760, "longitude": 72.8777, "elevation": 14.0, "state": "Maharashtra", "climate_zone": "Tropical Monsoon (Coastal West)"},
    {"city": "Delhi", "latitude": 28.6139, "longitude": 77.2090, "elevation": 216.0, "state": "Delhi NCR", "climate_zone": "Monsoon-Influenced Humid Subtropical / Semi-Arid"},
]


def get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Create and return a SQLite connection."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Initialize tables and indexes in SQLite."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        # City Metadata Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS city_metadata (
                city TEXT PRIMARY KEY,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                elevation REAL,
                state TEXT,
                climate_zone TEXT
            )
        """)

        # Daily Weather Records Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weather_daily (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city TEXT NOT NULL,
                date TEXT NOT NULL,
                temp_mean REAL,
                temp_max REAL,
                temp_min REAL,
                precipitation REAL,
                wind_speed_max REAL,
                temp_range REAL,
                season TEXT,
                is_rain_day INTEGER,
                is_heavy_rain INTEGER,
                FOREIGN KEY (city) REFERENCES city_metadata (city),
                UNIQUE(city, date)
            )
        """)

        # Climate Anomalies Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS climate_anomalies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city TEXT NOT NULL,
                date TEXT NOT NULL,
                anomaly_type TEXT NOT NULL,
                metric_value REAL,
                baseline_mean REAL,
                deviation REAL,
                z_score REAL,
                severity TEXT,
                FOREIGN KEY (city) REFERENCES city_metadata (city)
            )
        """)

        # Indexes for fast querying
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_weather_city_date ON weather_daily(city, date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_weather_date ON weather_daily(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_weather_season ON weather_daily(season)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_anomalies_city ON climate_anomalies(city)")

        # Seed city metadata
        for meta in CITY_METADATA_SEED:
            cursor.execute("""
                INSERT INTO city_metadata (city, latitude, longitude, elevation, state, climate_zone)
                VALUES (:city, :latitude, :longitude, :elevation, :state, :climate_zone)
                ON CONFLICT(city) DO UPDATE SET
                    latitude=excluded.latitude,
                    longitude=excluded.longitude,
                    elevation=excluded.elevation,
                    state=excluded.state,
                    climate_zone=excluded.climate_zone
            """, meta)

        conn.commit()
    logger.info("Database schema initialized at %s", db_path)


def load_weather_data(df: pd.DataFrame, db_path: str = DEFAULT_DB_PATH) -> int:
    """
    Load cleaned DataFrame into weather_daily table using UPSERT.
    Returns count of loaded records.
    """
    init_db(db_path)
    clean_df = df.copy()

    # Ensure date is string formatted YYYY-MM-DD
    if pd.api.types.is_datetime64_any_dtype(clean_df["date"]):
        clean_df["date"] = clean_df["date"].dt.strftime("%Y-%m-%d")

    records = clean_df[[
        "city", "date", "temp_mean", "temp_max", "temp_min",
        "precipitation", "wind_speed_max", "temp_range", "season",
        "is_rain_day", "is_heavy_rain"
    ]].to_dict(orient="records")

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT INTO weather_daily (
                city, date, temp_mean, temp_max, temp_min,
                precipitation, wind_speed_max, temp_range, season,
                is_rain_day, is_heavy_rain
            ) VALUES (
                :city, :date, :temp_mean, :temp_max, :temp_min,
                :precipitation, :wind_speed_max, :temp_range, :season,
                :is_rain_day, :is_heavy_rain
            )
            ON CONFLICT(city, date) DO UPDATE SET
                temp_mean=excluded.temp_mean,
                temp_max=excluded.temp_max,
                temp_min=excluded.temp_min,
                precipitation=excluded.precipitation,
                wind_speed_max=excluded.wind_speed_max,
                temp_range=excluded.temp_range,
                season=excluded.season,
                is_rain_day=excluded.is_rain_day,
                is_heavy_rain=excluded.is_heavy_rain
        """, records)
        conn.commit()

    logger.info("Loaded %d daily records into SQLite (%s)", len(records), db_path)
    return len(records)


def load_anomalies(anomalies_df: pd.DataFrame, db_path: str = DEFAULT_DB_PATH) -> int:
    """Load detected anomalies into climate_anomalies table."""
    init_db(db_path)
    if anomalies_df.empty:
        return 0

    df = anomalies_df.copy()
    if pd.api.types.is_datetime64_any_dtype(df["date"]):
        df["date"] = df["date"].dt.strftime("%Y-%m-%d")

    records = df[[
        "city", "date", "anomaly_type", "metric_value",
        "baseline_mean", "deviation", "z_score", "severity"
    ]].to_dict(orient="records")

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM climate_anomalies")  # Refresh anomalies
        cursor.executemany("""
            INSERT INTO climate_anomalies (
                city, date, anomaly_type, metric_value,
                baseline_mean, deviation, z_score, severity
            ) VALUES (
                :city, :date, :anomaly_type, :metric_value,
                :baseline_mean, :deviation, :z_score, :severity
            )
        """, records)
        conn.commit()

    return len(records)


def query_weather(
    city: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> pd.DataFrame:
    """Query weather_daily with optional city and date range filters."""
    query = "SELECT * FROM weather_daily WHERE 1=1"
    params: List[Any] = []

    if city and city != "All":
        query += " AND city = ?"
        params.append(city)
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)

    query += " ORDER BY city, date"

    with get_connection(db_path) as conn:
        df = pd.read_sql_query(query, conn, params=params)

    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def get_city_summary(db_path: str = DEFAULT_DB_PATH) -> pd.DataFrame:
    """Compute high-level summary KPIs for each city from SQLite."""
    query = """
        SELECT
            w.city,
            m.state,
            m.climate_zone,
            m.elevation,
            COUNT(*) as record_count,
            MIN(w.date) as start_date,
            MAX(w.date) as end_date,
            ROUND(AVG(w.temp_mean), 2) as avg_temp_mean,
            ROUND(MAX(w.temp_max), 2) as record_high_temp,
            ROUND(MIN(w.temp_min), 2) as record_low_temp,
            ROUND(AVG(w.precipitation) * 365.25, 1) as avg_annual_rainfall,
            SUM(w.is_rain_day) as total_rain_days,
            SUM(w.is_heavy_rain) as total_heavy_rain_days
        FROM weather_daily w
        LEFT JOIN city_metadata m ON w.city = m.city
        GROUP BY w.city
        ORDER BY avg_temp_mean DESC
    """
    with get_connection(db_path) as conn:
        return pd.read_sql_query(query, conn)


def get_monthly_aggregates(city: Optional[str] = None, db_path: str = DEFAULT_DB_PATH) -> pd.DataFrame:
    """Compute monthly climatology averages across historical years."""
    query = """
        SELECT
            city,
            strftime('%m', date) as month,
            ROUND(AVG(temp_mean), 2) as avg_temp,
            ROUND(AVG(temp_max), 2) as avg_temp_max,
            ROUND(AVG(temp_min), 2) as avg_temp_min,
            ROUND(SUM(precipitation) / (COUNT(DISTINCT strftime('%Y', date))), 1) as avg_monthly_rainfall,
            ROUND(AVG(wind_speed_max), 1) as avg_wind_speed
        FROM weather_daily
    """
    params: List[Any] = []
    if city and city != "All":
        query += " WHERE city = ?"
        params.append(city)
    query += " GROUP BY city, strftime('%m', date) ORDER BY city, month"

    with get_connection(db_path) as conn:
        return pd.read_sql_query(query, conn, params=params)
