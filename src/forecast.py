"""
Climate Predictive Analytics and Forecasting Lab for AtmosIQ
Implements strictly chronological train/test splitting to prevent data leakage,
computes non-leaking lag and cyclic features, compares Ridge/Random Forest models
against persistence and climatological baselines, and computes rigorous MAE, RMSE, and R2.
"""

import logging
from typing import Dict, Any, Tuple, Optional, List
import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


def build_forecasting_features(city_df: pd.DataFrame, target_col: str = "temp_mean") -> pd.DataFrame:
    """
    Construct strictly causal time-series features.
    CRITICAL: All rolling and lag features are shifted by at least 1 day
    to strictly prevent data leakage from the target day.
    """
    df = city_df.sort_values("date").copy()
    df["date"] = pd.to_datetime(df["date"])

    # Cyclic day of year features
    doy = df["date"].dt.day_of_year
    df["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
    df["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)

    # Historical lags (shifted strictly >= 1 day)
    df["lag_1"] = df[target_col].shift(1)
    df["lag_2"] = df[target_col].shift(2)
    df["lag_3"] = df[target_col].shift(3)
    df["lag_7"] = df[target_col].shift(7)
    df["lag_14"] = df[target_col].shift(14)

    # Rolling statistics shifted by 1 day (strictly using past days only)
    past_series = df[target_col].shift(1)
    df["roll_mean_7"] = past_series.rolling(window=7, min_periods=3).mean()
    df["roll_std_7"] = past_series.rolling(window=7, min_periods=3).std()
    df["roll_mean_30"] = past_series.rolling(window=30, min_periods=7).mean()

    # Weather covariates (strictly from previous day)
    if "precipitation" in df.columns:
        df["precip_lag_1"] = df["precipitation"].shift(1)
    if "wind_speed_max" in df.columns:
        df["wind_lag_1"] = df["wind_speed_max"].shift(1)
    if "temp_range" in df.columns:
        df["temp_range_lag_1"] = df["temp_range"].shift(1)

    # Drop warm-up rows containing NaNs from lags
    return df.dropna().reset_index(drop=True)


def evaluate_forecast_experiment(
    df: pd.DataFrame,
    city: str,
    target_col: str = "temp_mean",
    split_date: str = "2023-01-01",
    model_type: str = "ridge",
) -> Dict[str, Any]:
    """
    Execute a rigorous chronological forecasting experiment for a given city.
    Compares the trained model against both:
    1. Persistence baseline: y_hat = y_{t-1}
    2. Climatology baseline: y_hat = mean(y_{train} for same day-of-year)
    """
    city_data = df[df["city"] == city].copy()
    if city_data.empty:
        raise ValueError(f"No data available for city: {city}")

    feature_df = build_forecasting_features(city_data, target_col=target_col)

    # Strict Chronological Train/Test Split
    train_mask = feature_df["date"] < pd.to_datetime(split_date)
    test_mask = feature_df["date"] >= pd.to_datetime(split_date)

    train_df = feature_df[train_mask].copy()
    test_df = feature_df[test_mask].copy()

    if len(train_df) < 300 or len(test_df) < 30:
        # Fallback to 80/20 chronological split if fixed split date gives inadequate samples
        split_idx = int(len(feature_df) * 0.8)
        train_df = feature_df.iloc[:split_idx].copy()
        test_df = feature_df.iloc[split_idx].copy()
        split_date = str(test_df["date"].min().date())

    feature_cols = [
        "doy_sin", "doy_cos", "lag_1", "lag_2", "lag_3", "lag_7", "lag_14",
        "roll_mean_7", "roll_std_7", "roll_mean_30"
    ]
    for opt_col in ["precip_lag_1", "wind_lag_1", "temp_range_lag_1"]:
        if opt_col in feature_df.columns:
            feature_cols.append(opt_col)

    X_train = train_df[feature_cols].values
    y_train = train_df[target_col].values
    X_test = test_df[feature_cols].values
    y_test = test_df[target_col].values

    # Fit Scaler strictly on train set
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # 1. Baseline: Persistence (lag_1)
    y_pred_persistence = test_df["lag_1"].values

    # 2. Baseline: Climatological Mean per Day of Year (fit on train set only)
    train_df["doy"] = train_df["date"].dt.day_of_year
    test_df["doy"] = test_df["date"].dt.day_of_year
    climo_map = train_df.groupby("doy")[target_col].mean().to_dict()
    global_train_mean = float(y_train.mean())
    y_pred_climo = test_df["doy"].map(climo_map).fillna(global_train_mean).values

    # 3. Machine Learning Model
    if model_type.lower() == "random_forest":
        model = RandomForestRegressor(n_estimators=100, max_depth=12, random_state=42, n_jobs=-1)
        model.fit(X_train, y_train)
        y_pred_model = model.predict(X_test)
        importances = dict(zip(feature_cols, [round(float(v), 4) for v in model.feature_importances_]))
    else:
        model = Ridge(alpha=1.0)
        model.fit(X_train_scaled, y_train)
        y_pred_model = model.predict(X_test_scaled)
        importances = dict(zip(feature_cols, [round(float(v), 4) for v in np.abs(model.coef_)]))

    # Metrics Computation
    def compute_metrics(y_true, y_pred):
        mae = float(mean_absolute_error(y_true, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
        r2 = float(r2_score(y_true, y_pred))
        mape = float(np.mean(np.abs((y_true - y_pred) / np.maximum(np.abs(y_true), 1e-5))) * 100)
        return {"mae": round(mae, 3), "rmse": round(rmse, 3), "r2": round(r2, 3), "mape": round(mape, 2)}

    metrics_persistence = compute_metrics(y_test, y_pred_persistence)
    metrics_climo = compute_metrics(y_test, y_pred_climo)
    metrics_model = compute_metrics(y_test, y_pred_model)

    # Improvement over persistence baseline
    mae_improvement_pct = round(
        ((metrics_persistence["mae"] - metrics_model["mae"]) / metrics_persistence["mae"]) * 100, 2
    )

    test_predictions_df = pd.DataFrame({
        "date": test_df["date"],
        "actual": y_test,
        "predicted_model": np.round(y_pred_model, 2),
        "predicted_persistence": np.round(y_pred_persistence, 2),
        "predicted_climatology": np.round(y_pred_climo, 2),
    })

    return {
        "city": city,
        "model_type": model_type,
        "train_range": [str(train_df["date"].min().date()), str(train_df["date"].max().date())],
        "test_range": [str(test_df["date"].min().date()), str(test_df["date"].max().date())],
        "train_samples": len(train_df),
        "test_samples": len(test_df),
        "metrics_model": metrics_model,
        "metrics_persistence_baseline": metrics_persistence,
        "metrics_climo_baseline": metrics_climo,
        "mae_improvement_pct": mae_improvement_pct,
        "feature_importance": importances,
        "predictions": test_predictions_df,
    }
