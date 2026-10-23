"""
Automated unit tests for predictive analytics and chronological forecast validation.
Verifies data leakage prevention and benchmarking against persistence and climatology baselines.
"""

import unittest
import pandas as pd
import numpy as np
from src.forecast import build_forecasting_features, evaluate_forecast_experiment


class TestForecast(unittest.TestCase):

    def setUp(self):
        # 4 years of daily synthetic temperature data for Hyderabad
        dates = pd.date_range("2020-01-01", "2023-12-31", freq="D")
        n = len(dates)
        np.random.seed(42)
        doy = dates.day_of_year
        base_temp = 26.0 + 7.0 * np.sin(2 * np.pi * (doy - 100) / 365.25)
        temps = base_temp + np.random.normal(0, 1.2, n)

        self.df = pd.DataFrame({
            "city": ["Hyderabad"] * n,
            "date": dates,
            "temp_mean": temps,
            "temp_max": temps + 6.0,
            "temp_min": temps - 6.0,
            "precipitation": np.random.exponential(1.5, n),
            "wind_speed_max": np.random.normal(12.0, 3.0, n),
            "temp_range": [12.0] * n,
        })

    def test_build_forecasting_features_no_data_leakage(self):
        features = build_forecasting_features(self.df, target_col="temp_mean")

        # Feature dataframe should be non-empty and sorted
        self.assertFalse(features.empty)

        # Critical: Verify lag_1 is exactly equal to target shifted by 1 day
        expected_lag_1 = self.df.sort_values("date")["temp_mean"].iloc[-2]
        actual_lag_1 = features["lag_1"].iloc[-1]
        self.assertAlmostEqual(actual_lag_1, expected_lag_1, places=4)

        # Critical: Verify 7-day rolling mean does NOT include the target day's value
        target_last = features["temp_mean"].iloc[-1]
        roll_mean_last = features["roll_mean_7"].iloc[-1]
        # Past 7 days prior to last row
        past_7_mean = features["temp_mean"].iloc[-8:-1].mean()
        self.assertAlmostEqual(roll_mean_last, past_7_mean, places=4)

    def test_evaluate_forecast_experiment_chronological_split(self):
        results = evaluate_forecast_experiment(
            self.df,
            city="Hyderabad",
            target_col="temp_mean",
            split_date="2023-01-01",
            model_type="ridge",
        )

        # Verify chronological split boundaries
        train_max = pd.to_datetime(results["train_range"][1])
        test_min = pd.to_datetime(results["test_range"][0])
        self.assertLess(train_max, test_min, "Data leakage detected: train date overlaps test date!")

        # Verify metrics returned
        for metric in ["mae", "rmse", "r2", "mape"]:
            self.assertIn(metric, results["metrics_model"])
            self.assertIn(metric, results["metrics_persistence_baseline"])
            self.assertIn(metric, results["metrics_climo_baseline"])

        # Check model MAE and RMSE are reasonable physical values
        self.assertGreater(results["metrics_model"]["mae"], 0.0)
        self.assertLess(results["metrics_model"]["mae"], 10.0)
        self.assertGreater(results["metrics_model"]["r2"], 0.0)

        # Check predictions dataframe
        preds = results["predictions"]
        self.assertEqual(len(preds), results["test_samples"])
        self.assertIn("predicted_model", preds.columns)
        self.assertIn("predicted_persistence", preds.columns)
        self.assertIn("predicted_climatology", preds.columns)


if __name__ == "__main__":
    unittest.main()
