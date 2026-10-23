"""
Automated unit tests for SQLite database operations and analytical queries.
"""

import unittest
import tempfile
import os
import pandas as pd
from src.database import (
    init_db,
    load_weather_data,
    load_anomalies,
    query_weather,
    get_city_summary,
    get_connection,
)


class TestDatabase(unittest.TestCase):

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()

        # Seed sample weather dataframe
        self.sample_df = pd.DataFrame({
            "city": ["Delhi", "Delhi", "Bengaluru"],
            "date": ["2023-01-01", "2023-01-02", "2023-01-01"],
            "temp_mean": [14.5, 15.0, 21.0],
            "temp_max": [20.0, 21.0, 27.0],
            "temp_min": [9.0, 9.5, 15.0],
            "precipitation": [0.0, 0.0, 2.5],
            "wind_speed_max": [10.0, 12.0, 8.0],
            "temp_range": [11.0, 11.5, 12.0],
            "season": ["Winter", "Winter", "Winter"],
            "is_rain_day": [0, 0, 1],
            "is_heavy_rain": [0, 0, 0],
        })

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_init_and_seed_metadata(self):
        init_db(self.db_path)
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM city_metadata")
            count = cursor.fetchone()[0]
            self.assertEqual(count, 5)

    def test_load_and_query_weather(self):
        loaded_count = load_weather_data(self.sample_df, db_path=self.db_path)
        self.assertEqual(loaded_count, 3)

        # Query back Delhi records
        delhi_records = query_weather(city="Delhi", db_path=self.db_path)
        self.assertEqual(len(delhi_records), 2)
        self.assertEqual(delhi_records["city"].iloc[0], "Delhi")

        # Query with date filter
        date_records = query_weather(city="Delhi", start_date="2023-01-02", db_path=self.db_path)
        self.assertEqual(len(date_records), 1)

    def test_city_summary(self):
        load_weather_data(self.sample_df, db_path=self.db_path)
        summary = get_city_summary(db_path=self.db_path)
        self.assertFalse(summary.empty)
        cities = summary["city"].tolist()
        self.assertIn("Delhi", cities)
        self.assertIn("Bengaluru", cities)

    def test_load_anomalies(self):
        anom_df = pd.DataFrame([{
            "city": "Delhi",
            "date": "2023-06-15",
            "anomaly_type": "Heatwave",
            "metric_value": 45.5,
            "baseline_mean": 38.0,
            "deviation": 7.5,
            "z_score": 3.2,
            "severity": "Extreme",
        }])
        loaded = load_anomalies(anom_df, db_path=self.db_path)
        self.assertEqual(loaded, 1)

        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT city, anomaly_type, severity FROM climate_anomalies")
            row = cursor.fetchone()
            self.assertEqual(row["city"], "Delhi")
            self.assertEqual(row["severity"], "Extreme")


if __name__ == "__main__":
    unittest.main()
