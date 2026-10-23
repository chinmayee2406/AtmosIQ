"""
Automated unit tests for data collection and API response parsing.
All external API calls are mocked to ensure 100% offline test reliability.
"""

import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from src.collector import fetch_city_year, get_existing_coverage, CITIES


class TestCollector(unittest.TestCase):

    def setUp(self):
        self.mock_api_payload = {
            "daily": {
                "time": ["2023-01-01", "2023-01-02", "2023-01-03"],
                "temperature_2m_mean": [21.5, 22.0, 21.8],
                "temperature_2m_max": [28.2, 29.1, 28.5],
                "temperature_2m_min": [15.1, 15.4, 15.0],
                "precipitation_sum": [0.0, 2.5, 0.0],
                "wind_speed_10m_max": [12.4, 14.1, 11.2],
            }
        }

    @patch("requests.Session.get")
    def test_fetch_city_year_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self.mock_api_payload
        mock_get.return_value = mock_resp

        df = fetch_city_year("Hyderabad", CITIES["Hyderabad"], 2023)
        self.assertIsNotNone(df)
        self.assertEqual(len(df), 3)
        self.assertIn("date", df.columns)
        self.assertIn("temp_mean", df.columns)
        self.assertEqual(df["city"].iloc[0], "Hyderabad")

        # Crucial check: verify datetime type and safe .dt accessor access
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(df["date"]))
        self.assertEqual(int(df["date"].dt.year.iloc[0]), 2023)

    @patch("requests.Session.get")
    def test_fetch_city_year_retry_on_429(self, mock_get):
        resp_429 = MagicMock()
        resp_429.status_code = 429

        resp_200 = MagicMock()
        resp_200.status_code = 200
        resp_200.json.return_value = self.mock_api_payload

        # Return 429 first, then succeed on retry
        mock_get.side_effect = [resp_429, resp_200]

        df = fetch_city_year("Delhi", CITIES["Delhi"], 2023, max_retries=2, backoff_factor=0.01)
        self.assertIsNotNone(df)
        self.assertEqual(len(df), 3)
        self.assertEqual(mock_get.call_count, 2)

    def test_get_existing_coverage_with_valid_and_broken_dates(self):
        import tempfile
        import os

        # Create temporary CSV with mixed strings and test resumability
        test_df = pd.DataFrame({
            "city": ["Mumbai"] * 365 + ["Bengaluru"] * 10,
            "date": pd.date_range("2020-01-01", periods=365, freq="D").astype(str).tolist() + ["invalid-date"] * 10,
            "temp_mean": [27.0] * 375,
        })

        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as tf:
            test_df.to_csv(tf.name, index=False)
            temp_path = tf.name

        try:
            completed_pairs, loaded_df = get_existing_coverage(temp_path)
            # Mumbai 2020 should be recognized as complete (365 records >= 350)
            self.assertIn(("Mumbai", 2020), completed_pairs)
            # Bengaluru should not be marked complete
            self.assertNotIn(("Bengaluru", 2020), completed_pairs)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


if __name__ == "__main__":
    unittest.main()
