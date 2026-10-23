"""
Automated unit tests for climate anomaly detection and extreme event classification.
"""

import unittest
import pandas as pd
import numpy as np
from src.anomaly import (
    compute_baseline_climatology,
    detect_climate_anomalies,
    compute_annual_warming_stripes,
)


class TestAnomaly(unittest.TestCase):

    def setUp(self):
        # Create 2 years of synthetic weather data for Delhi
        dates = pd.date_range("2010-01-01", "2011-12-31", freq="D")
        n = len(dates)
        np.random.seed(42)

        # Base temperature cycle
        doy = dates.day_of_year
        base_temp = 25.0 + 10.0 * np.sin(2 * np.pi * (doy - 100) / 365.25)
        temps = base_temp + np.random.normal(0, 1.0, n)

        self.df = pd.DataFrame({
            "city": ["Delhi"] * n,
            "date": dates,
            "temp_mean": temps,
            "temp_max": temps + 5.0,
            "temp_min": temps - 5.0,
            "precipitation": np.random.choice([0.0, 2.0, 15.0], size=n, p=[0.8, 0.15, 0.05]),
            "wind_speed_max": [12.0] * n,
        })

    def test_compute_baseline_climatology(self):
        climo = compute_baseline_climatology(self.df, start_year=2010, end_year=2011)
        self.assertFalse(climo.empty)
        self.assertEqual(climo["city"].iloc[0], "Delhi")
        self.assertIn("base_temp_mean", climo.columns)
        self.assertIn("base_temp_std", climo.columns)
        # Should have smooth values across days of year
        self.assertTrue(len(climo) >= 365)

    def test_detect_anomalies_and_events(self):
        # Inject an extreme heatwave
        self.df.loc[100, "temp_mean"] = 45.0
        self.df.loc[100, "temp_max"] = 49.0

        # Inject an extreme rainfall event
        self.df.loc[200, "precipitation"] = 120.0

        full_df, events_df = detect_climate_anomalies(self.df, baseline_years=(2010, 2011))

        self.assertIn("temp_z_score", full_df.columns)
        self.assertIn("temp_departure", full_df.columns)
        self.assertFalse(events_df.empty)

        # Check heatwave detected
        heatwaves = events_df[events_df["anomaly_type"] == "Heatwave"]
        self.assertTrue(len(heatwaves) > 0)
        self.assertEqual(heatwaves["severity"].iloc[0], "Extreme")

        # Check extreme rainfall detected
        extreme_rains = events_df[events_df["anomaly_type"] == "Extreme Rainfall"]
        self.assertTrue(len(extreme_rains) > 0)
        self.assertEqual(extreme_rains["severity"].iloc[0], "Extreme")

    def test_compute_annual_warming_stripes(self):
        stripes = compute_annual_warming_stripes(self.df, reference_years=(2010, 2010))
        self.assertEqual(len(stripes), 2)  # 2 years
        self.assertIn("temp_anomaly", stripes.columns)


if __name__ == "__main__":
    unittest.main()
