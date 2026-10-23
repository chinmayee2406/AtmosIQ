"""
Automated unit tests for data cleaning, bounds verification, and feature engineering.
"""

import unittest
import pandas as pd
import numpy as np
from src.cleaner import clean_weather_data, assign_indian_season


class TestCleaner(unittest.TestCase):

    def test_assign_indian_season(self):
        self.assertEqual(assign_indian_season(1), "Winter")
        self.assertEqual(assign_indian_season(4), "Pre-Monsoon")
        self.assertEqual(assign_indian_season(7), "Monsoon")
        self.assertEqual(assign_indian_season(10), "Post-Monsoon")

    def test_clean_weather_data_pipeline(self):
        import tempfile
        import os

        # Synthetic messy dataframe
        messy_df = pd.DataFrame({
            "city": ["Delhi", "Delhi", "Delhi", "Delhi"],
            "date": ["2023-05-01", "2023-05-01", "2023-05-02", "not-a-date"],  # Duplicate & invalid date
            "temp_mean": [32.0, 32.0, 33.5, 30.0],
            "temp_max": [30.0, 30.0, 40.0, 35.0],  # Inverted min/max on row 0 & 1
            "temp_min": [38.0, 38.0, 25.0, 20.0],
            "precipitation": [-5.0, -5.0, 12.0, 0.0],  # Negative precipitation
            "wind_speed_max": [15.0, 15.0, 18.0, 10.0],
        })

        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as raw_file:
            messy_df.to_csv(raw_file.name, index=False)
            raw_path = raw_file.name

        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as clean_file:
            clean_path = clean_file.name

        try:
            df, summary = clean_weather_data(input_path=raw_path, output_path=clean_path)

            # Assert deduplicated & dropped invalid date
            self.assertEqual(len(df), 2)
            self.assertEqual(summary["duplicates_removed"], 1)
            self.assertEqual(summary["null_dates_dropped"], 1)

            # Assert inverted temp_min/max was corrected
            self.assertTrue((df["temp_min"] <= df["temp_max"]).all())

            # Assert negative precipitation clipped to 0
            self.assertTrue((df["precipitation"] >= 0.0).all())

            # Assert derived columns exist
            for col in ["year", "month", "day", "day_of_year", "season", "temp_range", "is_rain_day", "is_heavy_rain"]:
                self.assertIn(col, df.columns)

            # Safe .dt operations on cleaned date
            self.assertTrue(pd.api.types.is_datetime64_any_dtype(df["date"]))
            self.assertEqual(df["date"].dt.year.iloc[0], 2023)

        finally:
            if os.path.exists(raw_path):
                os.remove(raw_path)
            if os.path.exists(clean_path):
                os.remove(clean_path)


if __name__ == "__main__":
    unittest.main()
