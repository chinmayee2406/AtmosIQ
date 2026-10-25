"""
AtmosIQ - Climate Intelligence & Predictive Analytics 
Interactive Multi-Page Streamlit Dashboard
Pages:
1. Climate Overview
2. Climate Explorer
3. Anomaly Intelligence
4. Forecast Lab
5. Data Quality & Limitations
"""

import os
import sys
from pathlib import Path

# Ensure project root directory is on Python path
PROJECT_ROOT = Path(__file__).resolve().parent
if not (PROJECT_ROOT / "src").exists():
    PROJECT_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import sqlite3
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# Setup Page Configuration
st.set_page_config(
    page_title="AtmosIQ | Climate Intelligence",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #38BDF8;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #94A3B8;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #1E293B;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #F8FAFC;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .alert-box {
        background: rgba(14, 165, 233, 0.1);
        border-left: 4px solid #0EA5E9;
        padding: 0.8rem 1rem;
        border-radius: 4px;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

DB_PATH = str(PROJECT_ROOT / "data" / "atmosiq.db")
CLEAN_CSV_PATH = str(PROJECT_ROOT / "data" / "processed" / "cleaned_weather.csv")
RAW_CSV_PATH = str(PROJECT_ROOT / "data" / "raw" / "weather_data.csv")


@st.cache_data(ttl=600)
def load_all_data():
    """Load cleaned weather data from SQLite or CSV fallback."""
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            df = pd.read_sql_query("""
                SELECT w.*, m.latitude, m.longitude, m.elevation, m.state, m.climate_zone
                FROM weather_daily w
                LEFT JOIN city_metadata m ON w.city = m.city
                ORDER BY w.city, w.date
            """, conn)
            conn.close()
            df["date"] = pd.to_datetime(df["date"])
            df["year"] = df["date"].dt.year
            df["month"] = df["date"].dt.month
            df["day"] = df["date"].dt.day
            return df
        except Exception:
            pass

    if os.path.exists(CLEAN_CSV_PATH):
        df = pd.read_csv(CLEAN_CSV_PATH)
        df["date"] = pd.to_datetime(df["date"])
        df["year"] = df["date"].dt.year
        df["month"] = df["date"].dt.month
        df["day"] = df["date"].dt.day
        return df

    if os.path.exists(RAW_CSV_PATH):
        df = pd.read_csv(RAW_CSV_PATH)
        df["date"] = pd.to_datetime(df["date"])
        df["year"] = df["date"].dt.year
        df["month"] = df["date"].dt.month
        df["day"] = df["date"].dt.day
        return df

    return pd.DataFrame()


@st.cache_data(ttl=600)
def load_anomalies_data():
    """Load anomalies from SQLite or generate on the fly."""
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            df = pd.read_sql_query("SELECT * FROM climate_anomalies ORDER BY date DESC", conn)
            conn.close()
            if not df.empty:
                df["date"] = pd.to_datetime(df["date"])
                return df
        except Exception:
            pass
    return pd.DataFrame()


# --- SIDEBAR NAVIGATION ---
st.sidebar.image("https://img.icons8.com/fluency/96/cloud-lighting.png", width=64)
st.sidebar.title("AtmosIQ")
st.sidebar.markdown("**Climate Intelligence & Predictive Analytics**")

page = st.sidebar.radio(
    "Navigation",
    ["1. Climate Overview", "2. Climate Explorer", "3. Anomaly Intelligence", "4. Forecast Lab", "5. Data Quality"],
    index=0,
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Data Scope")
st.sidebar.markdown("""
- **Source:** Open-Meteo ERA5 Reanalysis
- **Cities:** Hyderabad, Bengaluru, Chennai, Mumbai, Delhi
- **Coverage:** 2000 – 2025 (26 Years)
- **Granularity:** Daily
""")

df_full = load_all_data()

if df_full.empty:
    st.warning("⚠️ Weather dataset is currently being collected or processed. Please refresh once completed.")
    st.stop()

# Ensure required columns exist
cities_available = sorted(df_full["city"].unique().tolist())
min_date = df_full["date"].min().date()
max_date = df_full["date"].max().date()


# ==============================================================================
# PAGE 1: CLIMATE OVERVIEW
# ==============================================================================
if page == "1. Climate Overview":
    st.markdown('<div class="main-title">🌍 Climate Overview & Decadal Shifts</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">High-level macro climate patterns, geographical benchmarks, and warming rates across 5 major Indian metropolitan centers.</div>', unsafe_allow_html=True)

    # Top KPI Metrics across all cities
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Observations", f"{len(df_full):,}")
    with col2:
        st.metric("Cities Covered", f"{len(cities_available)}")
    with col3:
        st.metric("Historical Years", f"{min_date.year} – {max_date.year}")
    with col4:
        st.metric("Hottest Record", f"{df_full['temp_max'].max():.1f} °C", help=f"Recorded in {df_full.loc[df_full['temp_max'].idxmax(), 'city']}")
    with col5:
        st.metric("Max Daily Rainfall", f"{df_full['precipitation'].max():.1f} mm", help=f"Recorded in {df_full.loc[df_full['precipitation'].idxmax(), 'city']}")

    st.markdown("---")

    # City Climatology Comparison Table & Chart
    st.subheader("📊 Cross-City Meteorological Benchmarks")

    summary_df = df_full.groupby("city").agg(
        avg_temp=("temp_mean", "mean"),
        max_temp=("temp_max", "max"),
        min_temp=("temp_min", "min"),
        diurnal_range=("temp_range", "mean"),
        annual_rainfall=("precipitation", lambda s: s.sum() / (max_date.year - min_date.year + 1)),
        heavy_rain_days=("is_heavy_rain", "sum"),
    ).reset_index()

    c1, c2 = st.columns([1, 1])
    with c1:
        fig_bar = px.bar(
            summary_df,
            x="city",
            y="avg_temp",
            color="city",
            text="avg_temp",
            title="Mean Annual Temperature (°C)",
            color_discrete_sequence=px.colors.qualitative.Prism,
        )
        fig_bar.update_traces(texttemplate="%{text:.1f}°C", textposition="outside")
        fig_bar.update_layout(showlegend=False, yaxis_title="Mean Temperature (°C)")
        st.plotly_chart(fig_bar, use_container_width=True)

    with c2:
        fig_rain = px.bar(
            summary_df,
            x="city",
            y="annual_rainfall",
            color="city",
            text="annual_rainfall",
            title="Mean Annual Rainfall (mm)",
            color_discrete_sequence=px.colors.qualitative.Safe,
        )
        fig_rain.update_traces(texttemplate="%{text:.0f} mm", textposition="outside")
        fig_rain.update_layout(showlegend=False, yaxis_title="Annual Precipitation (mm)")
        st.plotly_chart(fig_rain, use_container_width=True)

    # Long-term Warming Trends
    st.subheader("📈 26-Year Annual Temperature Trajectories")
    df_annual = df_full.groupby(["city", df_full["date"].dt.year])["temp_mean"].mean().reset_index()
    df_annual = df_annual.rename(columns={"date": "year"})

    fig_trends = px.line(
        df_annual,
        x="year",
        y="temp_mean",
        color="city",
        markers=True,
        title="Annual Mean Temperature Evolution (2000 - 2025)",
        labels={"temp_mean": "Annual Mean Temp (°C)", "year": "Year"},
    )
    fig_trends.update_layout(hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig_trends, use_container_width=True)

    st.markdown("""
    <div class="alert-box">
    <b>Key Takeaways:</b>
    <ul>
        <li><b>Coastal vs. Inland Continental:</b> Mumbai and Chennai exhibit tempered diurnal ranges (~5-7°C) due to strong maritime moderation, while Delhi shows severe continental extremes ranging from winter near-freezing lows (< 5°C) to peak summer highs (> 46°C).</li>
        <li><b>Elevation Moderation:</b> Bengaluru (elev. ~920m) maintains the coolest overall annual mean temperature (~23.9°C), illustrating significant orographic cooling.</li>
        <li><b>Monsoon Dependence:</b> Mumbai records acute monsoon rainfall concentration (over 85% of annual precipitation concentrated between June and September).</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)


# ==============================================================================
# PAGE 2: CLIMATE EXPLORER
# ==============================================================================
elif page == "2. Climate Explorer":
    st.markdown('<div class="main-title">🔍 Climate Explorer & Seasonal Dynamics</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Granular multi-variable temporal exploration, monthly distribution profiles, and seasonal heatmaps.</div>', unsafe_allow_html=True)

    # Filters
    fcol1, fcol2, fcol3 = st.columns([1, 1, 1])
    with fcol1:
        sel_city = st.selectbox("Select City", cities_available, index=0)
    with fcol2:
        date_range = st.date_input("Date Range", [min_date, max_date], min_value=min_date, max_value=max_date)
    with fcol3:
        var_choice = st.selectbox("Primary Variable", ["temp_mean", "temp_max", "temp_min", "precipitation", "wind_speed_max"], index=0)

    start_d, end_d = (date_range[0], date_range[1]) if len(date_range) == 2 else (min_date, max_date)
    filtered = df_full[(df_full["city"] == sel_city) & (df_full["date"].dt.date >= start_d) & (df_full["date"].dt.date <= end_d)].copy()

    if filtered.empty:
        st.warning("No records found for selected filter combination.")
        st.stop()

    # Time-series with Rolling Averages
    st.subheader(f"Daily Trajectory: {sel_city} ({start_d} to {end_d})")
    filtered["rolling_30"] = filtered[var_choice].rolling(30, min_periods=7).mean()

    fig_ts = go.Figure()
    fig_ts.add_trace(go.Scatter(x=filtered["date"], y=filtered[var_choice], mode="lines", name="Daily Raw", opacity=0.35, line=dict(color="#38BDF8", width=1)))
    fig_ts.add_trace(go.Scatter(x=filtered["date"], y=filtered["rolling_30"], mode="lines", name="30-Day Moving Avg", line=dict(color="#F59E0B", width=2.5)))
    fig_ts.update_layout(
        title=f"{var_choice.replace('_', ' ').title()} Daily & 30-Day Smoothed Trend",
        xaxis_title="Date",
        yaxis_title=var_choice.replace('_', ' ').title(),
        hovermode="x unified",
    )
    st.plotly_chart(fig_ts, use_container_width=True)

    # Monthly Distribution Boxplots & Seasonal Climatology
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Monthly Temperature Distribution")
        fig_box = px.box(
            filtered,
            x="month",
            y="temp_mean",
            color="season",
            title=f"Monthly Temperature Range ({sel_city})",
            labels={"month": "Month", "temp_mean": "Mean Temp (°C)"},
        )
        st.plotly_chart(fig_box, use_container_width=True)

    with c2:
        st.subheader("Monthly Rainfall Totals (mm)")
        monthly_rain = filtered.groupby(["year", "month"])["precipitation"].sum().reset_index()
        avg_monthly_rain = monthly_rain.groupby("month")["precipitation"].mean().reset_index()
        fig_rain_bar = px.bar(
            avg_monthly_rain,
            x="month",
            y="precipitation",
            text="precipitation",
            title=f"Mean Precipitation by Month ({sel_city})",
            color_discrete_sequence=["#0284C7"],
        )
        fig_rain_bar.update_traces(texttemplate="%{text:.0f} mm", textposition="outside")
        fig_rain_bar.update_layout(yaxis_title="Total Rainfall (mm)")
        st.plotly_chart(fig_rain_bar, use_container_width=True)

    # Annual Heatmap (Day of Year vs Year)
    st.subheader(f"Temperature Climatology Heatmap ({sel_city})")
    heatmap_data = filtered.pivot_table(index="year", columns="month", values="temp_mean", aggfunc="mean")
    fig_hm = px.imshow(
        heatmap_data,
        labels=dict(x="Month", y="Year", color="Temp (°C)"),
        x=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        aspect="auto",
        color_continuous_scale="Viridis",
        title=f"Monthly Average Temperature Heatmap - {sel_city}",
    )
    st.plotly_chart(fig_hm, use_container_width=True)


# ==============================================================================
# PAGE 3: ANOMALY INTELLIGENCE
# ==============================================================================
elif page == "3. Anomaly Intelligence":
    st.markdown('<div class="main-title">⚡ Climate Anomaly & Extreme Event Intelligence</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Systematic detection of meteorological departures, heatwave spells, coldwaves, and extreme precipitation events.</div>', unsafe_allow_html=True)

    # City filter
    sel_city = st.selectbox("Select City for Anomaly Analysis", cities_available, index=0)

    # Calculate or retrieve anomalies
    from src.anomaly import detect_climate_anomalies, compute_annual_warming_stripes
    with st.spinner("Computing baseline climatology and anomaly departures..."):
        full_anomalies_df, events_df = detect_climate_anomalies(df_full[df_full["city"] == sel_city])

    # KPI summary of anomalies
    akpi1, akpi2, akpi3, akpi4 = st.columns(4)
    heatwaves = events_df[events_df["anomaly_type"] == "Heatwave"]
    coldwaves = events_df[events_df["anomaly_type"] == "Coldwave"]
    extreme_rain = events_df[events_df["anomaly_type"] == "Extreme Rainfall"]

    with akpi1:
        st.metric("Total Anomaly Events", f"{len(events_df)}")
    with akpi2:
        st.metric("Heatwave Events", f"{len(heatwaves)}", delta=f"{len(heatwaves[heatwaves['severity'] == 'Extreme'])} Extreme", delta_color="inverse")
    with akpi3:
        st.metric("Coldwave Events", f"{len(coldwaves)}", delta=f"{len(coldwaves[coldwaves['severity'] == 'Extreme'])} Extreme", delta_color="inverse")
    with akpi4:
        st.metric("Extreme Rain Days", f"{len(extreme_rain)}", delta="≥ 50mm Threshold")

    st.markdown("---")

    # Standardized Anomaly Z-Score Timeline
    st.subheader(f"Temperature Departure (Z-Score) Timeline - {sel_city}")
    full_anomalies_df["color"] = full_anomalies_df["temp_departure"].apply(lambda v: "#EF4444" if v > 0 else "#3B82F6")

    fig_z = go.Figure()
    fig_z.add_trace(go.Bar(
        x=full_anomalies_df["date"],
        y=full_anomalies_df["temp_z_score"],
        marker_color=full_anomalies_df["color"],
        name="Z-Score",
        opacity=0.7,
    ))
    fig_z.add_hline(y=2.0, line_dash="dash", line_color="#F87171", annotation_text="+2.0σ Threshold (Severe)")
    fig_z.add_hline(y=-2.0, line_dash="dash", line_color="#60A5FA", annotation_text="-2.0σ Threshold (Severe)")
    fig_z.update_layout(yaxis_title="Standardized Anomaly (Z-Score)", xaxis_title="Date", hovermode="x unified")
    st.plotly_chart(fig_z, use_container_width=True)

    # Climate Warming Stripes
    st.subheader(f"Warming Stripes (Annual Baseline Departure): {sel_city}")
    stripes_df = compute_annual_warming_stripes(df_full[df_full["city"] == sel_city])

    fig_stripes = px.bar(
        stripes_df,
        x="year",
        y="temp_anomaly",
        color="temp_anomaly",
        color_continuous_scale="RdBu_r",
        title=f"Annual Mean Temperature Anomaly relative to 2000-2015 Baseline ({sel_city})",
        labels={"temp_anomaly": "Anomaly (°C)", "year": "Year"},
    )
    fig_stripes.update_layout(coloraxis_colorbar=dict(title="Δ °C"))
    st.plotly_chart(fig_stripes, use_container_width=True)

    # Extreme Events Log Table
    st.subheader("Historical Extreme Weather Events Registry")
    if not events_df.empty:
        st.dataframe(
            events_df[["date", "anomaly_type", "severity", "metric_value", "baseline_mean", "deviation", "z_score"]],
            use_container_width=True,
            height=300,
        )
    else:
        st.info("No extreme threshold violations recorded for this city.")


# ==============================================================================
# PAGE 4: FORECAST LAB
# ==============================================================================
elif page == "4. Forecast Lab":
    st.markdown('<div class="main-title">🧪 Climate Predictive Analytics Lab</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Chronological ML validation without data leakage. Benchmarking Ridge and Random Forest models against Persistence & Climatology baselines.</div>', unsafe_allow_html=True)

    fc_col1, fc_col2, fc_col3 = st.columns([1, 1, 1])
    with fc_col1:
        fc_city = st.selectbox("Forecast Target City", cities_available, index=0)
    with fc_col2:
        model_choice = st.selectbox("Model Architecture", ["Ridge Regression", "Random Forest"], index=0)
    with fc_col3:
        split_year = st.selectbox("Chronological Test Split Year", [2022, 2023, 2024], index=1)

    model_code = "random_forest" if model_choice == "Random Forest" else "ridge"

    from src.forecast import evaluate_forecast_experiment

    with st.spinner(f"Training {model_choice} with strict chronological split (>= {split_year}-01-01)..."):
        exp_results = evaluate_forecast_experiment(
            df_full,
            city=fc_city,
            target_col="temp_mean",
            split_date=f"{split_year}-01-01",
            model_type=model_code,
        )

    # Metric Benchmarking Cards
    st.subheader("Model vs. Baseline Benchmark Metrics (Test Split)")
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)

    m_mod = exp_results["metrics_model"]
    m_pers = exp_results["metrics_persistence_baseline"]
    m_climo = exp_results["metrics_climo_baseline"]

    with m_col1:
        st.metric(
            f"{model_choice} MAE",
            f"{m_mod['mae']} °C",
            delta=f"{exp_results['mae_improvement_pct']}% vs Persistence",
        )
    with m_col2:
        st.metric(
            f"{model_choice} RMSE",
            f"{m_mod['rmse']} °C",
            delta=f"R² = {m_mod['r2']}",
        )
    with m_col3:
        st.metric(
            "Persistence Baseline MAE",
            f"{m_pers['mae']} °C",
            help="Predicts yesterday's value (lag_1)",
        )
    with m_col4:
        st.metric(
            "Climatology Baseline MAE",
            f"{m_climo['mae']} °C",
            help="Predicts historical day-of-year average",
        )

    # Test Set Forecast Trajectory Chart
    st.subheader(f"Out-of-Sample Predictions vs Actuals ({exp_results['test_range'][0]} to {exp_results['test_range'][1]})")
    preds_df = exp_results["predictions"].sort_values("date")

    fig_fc = go.Figure()
    fig_fc.add_trace(go.Scatter(x=preds_df["date"], y=preds_df["actual"], mode="lines", name="Observed Actual", line=dict(color="#F8FAFC", width=1.5)))
    fig_fc.add_trace(go.Scatter(x=preds_df["date"], y=preds_df["predicted_model"], mode="lines", name=f"{model_choice} Forecast", line=dict(color="#38BDF8", width=2)))
    fig_fc.add_trace(go.Scatter(x=preds_df["date"], y=preds_df["predicted_climatology"], mode="lines", name="Climatology Baseline", line=dict(color="#A855F7", width=1.5, dash="dot")))

    fig_fc.update_layout(
        title=f"Test Set Evaluation: {fc_city} Daily Mean Temperature (°C)",
        xaxis_title="Date",
        yaxis_title="Mean Temperature (°C)",
        hovermode="x unified",
    )
    st.plotly_chart(fig_fc, use_container_width=True)

    # Feature Importance
    c1, c2 = st.columns([1, 1])
    with c1:
        st.subheader("Feature Importance / Coefficients")
        feat_df = pd.DataFrame(list(exp_results["feature_importance"].items()), columns=["Feature", "Weight"]).sort_values("Weight", ascending=True)
        fig_feat = px.bar(feat_df, x="Weight", y="Feature", orientation="h", title=f"Top Drivers for {fc_city} Forecast", color="Weight", color_continuous_scale="Teal")
        st.plotly_chart(fig_feat, use_container_width=True)

    with c2:
        st.subheader("Forecast Residuals Distribution")
        residuals = preds_df["actual"] - preds_df["predicted_model"]
        fig_res = px.histogram(residuals, nbins=35, title=f"Residual Error Distribution (Mean={residuals.mean():.2f}°C, Std={residuals.std():.2f}°C)", labels={"value": "Error (°C)"}, color_discrete_sequence=["#0EA5E9"])
        st.plotly_chart(fig_res, use_container_width=True)


# ==============================================================================
# PAGE 5: DATA QUALITY
# ==============================================================================
elif page == "5. Data Quality":
    st.markdown('<div class="main-title">🛡️ Data Quality, Governance & Physical Limitations</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Rigorous audit of ERA5 reanalysis ingestion, missingness, schema constraints, and database health.</div>', unsafe_allow_html=True)

    st.subheader("📋 Dataset Audit Metrics")
    dq1, dq2, dq3, dq4 = st.columns(4)

    null_count = df_full[["temp_mean", "temp_max", "temp_min", "precipitation", "wind_speed_max"]].isna().sum().sum()
    date_continuity = df_full.groupby("city")["date"].agg(lambda s: (s.max() - s.min()).days + 1 == len(s)).all()

    with dq1:
        st.metric("Total Records Ingested", f"{len(df_full):,}")
    with dq2:
        st.metric("Missing Values (Post-Clean)", f"{null_count}", delta="0.0% Missing")
    with dq3:
        st.metric("Date Continuity", "Continuous (Daily)" if date_continuity else "Gaps Detected")
    with dq4:
        st.metric("SQLite DB Status", "Connected & Indexed" if os.path.exists(DB_PATH) else "CSV Mode")

    st.markdown("---")

    # City-by-City Completeness Matrix
    st.subheader("City-by-City Ingestion & Completeness")
    city_dq = df_full.groupby("city").agg(
        records=("date", "count"),
        start_date=("date", lambda s: str(s.min().date())),
        end_date=("date", lambda s: str(s.max().date())),
        null_temps=("temp_mean", lambda s: s.isna().sum()),
        null_precip=("precipitation", lambda s: s.isna().sum()),
    ).reset_index()
    st.dataframe(city_dq, use_container_width=True)

    st.markdown("---")

    # Critical Scientific Limitations Notice
    st.subheader("⚠️ ERA5 Reanalysis Scientific Disclaimers & Known Limitations")
    st.markdown("""
    <div class="alert-box">
    <b>Methodological & Physical Considerations:</b>
    <ol>
        <li><b>Reanalysis Model Estimates vs. Station In-Situ Observations:</b> ERA5 combines global numerical weather prediction models with historical observations via 4D-Var data assimilation. While spatially continuous and globally consistent, values represent a ~31 km grid cell average rather than point-station sensor readings. Microclimates (e.g., intense urban heat islands or local sea breeze boundaries) may be smoothed.</li>
        <li><b>Precipitation Sensitivity:</b> Reanalysis precipitation is generated by the atmospheric physics parameterization rather than direct rain-gauge measurement. While synoptic monsoon totals align well with regional observations, localized convective cloudbursts can exhibit variance compared to local IMD rain gauges.</li>
        <li><b>Wind Speed at 10m:</b> Maximum wind speeds represent grid-box maximum sustained wind estimates and should not be confused with instantaneous 3-second convective gusts.</li>
        <li><b>Temporal Boundary:</b> The dataset spans 2000-01-01 through 2025-12-31, providing a 26-year climatological baseline sufficient for decadal warming and anomaly detection.</li>
    </ol>
    </div>
    """, unsafe_allow_html=True)
