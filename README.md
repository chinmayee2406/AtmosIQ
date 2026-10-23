# AtmosIQ — Climate Intelligence & Predictive Analytics

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.40+-FF4B4B.svg)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests: 14 Passed](https://img.shields.io/badge/tests-14%20passed-brightgreen.svg)]()

AtmosIQ is an end-to-end meteorological analytics and predictive intelligence platform covering 26 years (2000–2025) of daily climate data across five major Indian metropolitan centers: **Hyderabad, Bengaluru, Chennai, Mumbai, and Delhi**.

The platform combines automated data collection from the **Open-Meteo ERA5 Reanalysis API**, robust data cleaning and anomaly detection, an indexed **SQLite database**, chronological machine learning forecasting without data leakage, an interactive multi-page **Streamlit dashboard**, and **Tableau Public** visualization exports.

---

## 🌟 Key Features

1. **Automated Resumable Data Pipeline**:
   - Collects 26 years of continuous daily weather metrics (Mean, Max, Min Temp, Precipitation, Wind Speed).
   - Built-in exponential backoff, rate-limit (HTTP 429) recovery, and chunk-level checkpointing.
   - Robust datetime parsing avoiding Pandas `.dt` accessor errors.
2. **Meteorological Feature Engineering**:
   - Standard Indian meteorological season classification (Winter, Pre-Monsoon, Monsoon, Post-Monsoon).
   - Diurnal temperature range, rain-day indicators, and physical consistency bounds enforcement.
3. **Statistical Trend & Anomaly Detection**:
   - Rolling baseline climatology (2000–2015 reference period).
   - Standardized anomaly Z-scores and Indian Meteorological Department (IMD) aligned threshold detection for heatwaves, coldwaves, and extreme precipitation.
   - Decadal warming rates with ordinary least squares p-values and R² metrics.
4. **Leakage-Free Predictive Analytics Lab**:
   - Strict chronological train/test split.
   - Causal lag and rolling features shifted by $\ge 1$ day.
   - Benchmarking Ridge Regression and Random Forest models against Persistence and Climatological baselines with MAE, RMSE, MAPE, and R².
5. **Interactive Streamlit Dashboard (5 Pages)**:
   - **Climate Overview**: Cross-city KPIs, decadal shifts, and geographic benchmarks.
   - **Climate Explorer**: Granular daily time-series, monthly boxplots, and climatology heatmaps.
   - **Anomaly Intelligence**: Standardized Z-score timelines, Ed Hawkins warming stripes, and extreme event registry.
   - **Forecast Lab**: Interactive model training, residual error distributions, and feature importance.
   - **Data Quality**: Ingestion completeness matrices, schema audit, and ERA5 scientific limitations.
6. **Tableau Public Ready**:
   - Clean, normalized CSV exports in `data/tableau/`.
   - Comprehensive dashboard creation guide in `docs/TABLEAU_GUIDE.md`.

---

## 🏗️ Project Architecture

```
AtmosIQ/
├── .gitignore                     # Git ignore rules for venv, caches, credentials
├── .streamlit/
│   ├── config.toml                # Headless theme and server settings
│   └── credentials.toml           # Streamlit onboarding bypass
├── README.md                      # Comprehensive project documentation
├── requirements.txt               # Locked production dependencies
├── run_atmosiq.command            # macOS 1-click executable launcher
├── data/
│   ├── raw/
│   │   └── weather_data.csv       # Raw validated Open-Meteo API records (47,485 rows)
│   ├── processed/
│   │   └── cleaned_weather.csv    # Cleaned, feature-engineered dataset
│   ├── tableau/
│   │   ├── tableau_daily_weather.csv
│   │   ├── tableau_monthly_trends.csv
│   │   └── tableau_city_anomalies.csv
│   └── atmosiq.db                 # SQLite relational database with indexes
├── docs/
│   ├── TABLEAU_GUIDE.md           # Tableau Public 3-dashboard building instructions
│   └── DEPLOYMENT.md              # GitHub and Streamlit Cloud deployment guide
├── src/
│   ├── __init__.py
│   ├── collector.py               # Resumable API fetcher with exponential backoff
│   ├── cleaner.py                 # Data validation and feature engineering
│   ├── eda.py                     # Statistical trends and city comparisons
│   ├── database.py                # SQLite schema, indexing, and analytical queries
│   ├── anomaly.py                 # Baseline climatology, Z-scores, extreme events
│   ├── forecast.py                # Chronological ML models with baseline benchmarking
│   └── tableau_export.py          # Tableau CSV generation pipeline
├── app/
│   └── main.py                    # 5-Page Streamlit application
└── tests/
    ├── __init__.py
    ├── test_collector.py          # Collector unit tests (mocked API responses)
    ├── test_cleaner.py            # Cleaner and feature engineering tests
    ├── test_database.py           # SQLite database and query tests
    ├── test_anomaly.py            # Anomaly detection tests
    └── test_forecast.py           # Zero-leakage ML tests
```

---

## ⚡ Quick Start & Execution

### 1. 1-Click Launch (macOS)
Double-click `run_atmosiq.command` in the project root directory. It automatically verifies `.venv`, sets environment variables, starts Streamlit, and launches the browser to:
`http://127.0.0.1:8501`

### 2. Manual Terminal Launch
```bash
# Navigate to project directory
cd ~/Desktop/AtmosIQ

# Activate virtual environment
source .venv/bin/activate

# Launch Streamlit dashboard
streamlit run app/main.py --server.port 8501
```

### 3. Running the Data Pipeline Manually
```bash
# 1. Run Resumable Data Collector
.venv/bin/python3 -m src.collector

# 2. Run Cleaner and Feature Engineering
.venv/bin/python3 -m src.cleaner

# 3. Ingest into SQLite Database
.venv/bin/python3 -c "from src.database import load_weather_data; import pandas as pd; load_weather_data(pd.read_csv('data/processed/cleaned_weather.csv'))"

# 4. Generate Tableau CSVs
.venv/bin/python3 -m src.tableau_export
```

### 4. Running Automated Tests
```bash
.venv/bin/pytest -v tests
```
*Current test suite status:* **14 Passed, 0 Failed, 0 Warnings**.

---

## 🔬 Data Sources & Methodology

### Data Source
- **Provider**: [Open-Meteo Historical Weather API](https://archive-api.open-meteo.com)
- **Model**: ECMWF ERA5 Reanalysis
- **Variables**:
  - `temperature_2m_mean`: Daily mean 2m air temperature (°C)
  - `temperature_2m_max`: Daily maximum 2m air temperature (°C)
  - `temperature_2m_min`: Daily minimum 2m air temperature (°C)
  - `precipitation_sum`: Daily accumulated liquid precipitation (mm)
  - `wind_speed_10m_max`: Maximum sustained 10m wind speed (km/h)
- **Temporal Bounds**: 2000-01-01 to 2025-12-31 (9,497 days per city; 47,485 records total).

### Anomaly Detection Methodology
- **Reference Baseline**: 2000–2015 daily climatology per city and day-of-year, smoothed with a 7-day circular rolling window.
- **Departure Metric**: $T_{\text{departure}} = T_{\text{mean}} - \mu_{\text{baseline}}(doy)$
- **Standardized Anomaly (Z-Score)**: $Z = \frac{T_{\text{departure}}}{\sigma_{\text{baseline}}(doy)}$
- **Heatwave Threshold**: $T_{\text{max}} \ge 95\text{th percentile}$ and departure $\ge 3.0^\circ\text{C}$ (Moderate: $2.0 \le Z < 2.5$, Severe: $2.5 \le Z < 3.0$, Extreme: $Z \ge 3.0$).
- **Extreme Rainfall Threshold**: Precipitation $\ge \max(50\text{mm}, P_{99})$.

### Forecasting Methodology
- **Strict Chronological Splitting**: Chronological cutoff date (e.g., 2023-01-01). Training uses strictly dates prior to split; testing uses strictly dates on or after split. Zero shuffling, zero future leakage.
- **Feature Engineering**:
  - Lag features: $t-1, t-2, t-3, t-7, t-14$
  - Rolling features: 7-day, 30-day moving averages and standard deviations computed exclusively on `shift(1)` past observations.
  - Cyclic features: $\sin(2\pi \cdot doy / 365.25)$ and $\cos(2\pi \cdot doy / 365.25)$.
- **Benchmarks**:
  1. *Persistence Baseline*: $\hat{y}_t = y_{t-1}$ (yesterday's observed temperature).
  2. *Climatological Baseline*: $\hat{y}_t = \mu_{\text{train}}(doy)$ (historical day-of-year mean from training split).
- **Evaluation Metrics**: MAE, RMSE, MAPE, $R^2$, and relative percentage improvement over baseline.

---

## ⚠️ Scientific Disclaimers & Known Limitations

1. **Reanalysis Model Estimates vs. Station Sensors**: ERA5 blends numerical weather prediction models with historical observations via 4D-Var data assimilation. It represents a ~31 km grid cell average rather than point sensor observations. Highly localized microclimates (such as specific urban canyons or localized sea-breeze convergence lines) may appear smoothed.
2. **Precipitation Representation**: Reanalysis precipitation is parameterized by atmospheric convection models. While seasonal totals and synoptic monsoon depressions show high fidelity, localized cloudbursts may diverge from point IMD rain gauges.
3. **ERA5 Archive Availability**: Open-Meteo archive data for 2000–2025 is fully available and collected.

---

## 📊 Tableau Dashboards

See [TABLEAU_GUIDE.md](docs/TABLEAU_GUIDE.md) for full instructions on building:
1. **Climate Overview**: Geospatial bubble map, benchmark bars, and climate zone breakdown.
2. **Temperature & Rainfall Trends**: Dual-axis monthly climographs and annual warming lines.
3. **Climate Anomaly Intelligence**: Standardized Z-score departures and Ed Hawkins warming stripes.

---

## 🚀 GitHub & Cloud Deployment

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for step-by-step instructions on pushing to GitHub and deploying to Streamlit Community Cloud.
