# AtmosIQ — Tableau Public Visualization Guide

This guide provides step-by-step instructions to build three professional climate dashboards on Tableau Public using the clean datasets exported by the AtmosIQ pipeline.

---

## Data Sources

The CSV exports are located in the `data/tableau/` directory:

1. **`tableau_daily_weather.csv`** (47,485 records): Daily observations across Hyderabad, Bengaluru, Chennai, Mumbai, and Delhi (2000–2025) with latitude, longitude, and elevation.
2. **`tableau_monthly_trends.csv`** (1,560 records): Monthly aggregations with average temperatures, cumulative rainfall, rain-day counts, and extreme thresholds.
3. **`tableau_city_anomalies.csv`** (1,627 records): Identified climate anomalies (Heatwaves, Coldwaves, Extreme Rainfall) with baseline departures, Z-scores, and severity tiers.

---

## Dashboard 1: Climate Overview & Regional Geography

### Objective
Provide executive stakeholders with a macro geographic overview of the 5 metropolitan centers, baseline climate zones, and decadal benchmarks.

### Data Source
Connect to `tableau_daily_weather.csv`.

### Step-by-Step Worksheet Creation

1. **Metropolitan Weather Map (Geographic Scatter)**:
   - Drag `Longitude` to **Columns** and `Latitude` to **Rows**.
   - Change Mark type to **Circle**.
   - Drag `City` to **Detail** and **Label**.
   - Drag `Avg Temp Mean` to **Color** (Palette: *Temperature Diverging* / *Orange-Blue*).
   - Drag `Total Precipitation` to **Size**.
   - In Map Layers, select **Dark** or **Outdoors** style.

2. **Cross-City Temperature & Precipitation Benchmarks (Horizontal Bar)**:
   - Drag `City` to **Rows**.
   - Drag `Measure Values` to **Columns**. Filter measures to `AVG(Temp Mean)` and `AVG(Precipitation) * 365.25`.
   - Separate into two side-by-side synchronized bars.
   - Sort descending by Mean Temperature (Chennai highest ~28.0°C, Bengaluru coolest ~23.0°C).

3. **Macro KPI Summary Cards**:
   - Total Observations: `COUNT([Date])` = 47,485.
   - Historical Span: `MIN(Year)` to `MAX(Year)` = 2000 – 2025.
   - Highest Peak Temperature: `MAX([Temp Max])` (Delhi > 46°C).
   - Maximum 24-hr Rainfall: `MAX([Precipitation])` (Mumbai > 250 mm).

### Dashboard Layout
- Size: Automatic (or 1366 × 768 px Desktop).
- Top: KPI cards.
- Left: Metropolitan Geographic Map.
- Right: Benchmark Bar Charts and Climate Zone breakdown.

---

## Dashboard 2: Temperature & Rainfall Multi-Decadal Trends

### Objective
Analyze 26-year seasonal shifts, annual warming rates, and precipitation concentration.

### Data Source
Connect to `tableau_monthly_trends.csv`.

### Step-by-Step Worksheet Creation

1. **Dual-Axis Climate Climograph (Monthly Temp & Rain)**:
   - Drag `Month` (Dimension 1–12) to **Columns**.
   - Drag `AVG(Avg Temp Mean)` to **Rows**.
   - Drag `SUM(Total Precipitation)` to **Rows** (Right-click -> **Dual Axis**, Synchronize Axes, change Mark to Bar for Precipitation and Line for Temperature).
   - Add `City` to the **Filters** shelf (Single Select Dropdown).
   - Color: Blue for rainfall bars, Red/Amber for temperature line.

2. **Annual Temperature Warming Trajectory (2000 – 2025)**:
   - Drag `Year` to **Columns**.
   - Drag `AVG(Avg Temp Mean)` to **Rows**.
   - Drag `City` to **Color**.
   - Add a Linear Trend Line: Right-click chart -> **Trend Lines** -> **Show Trend Lines**.
   - Review R-Squared and p-values to show statistically significant warming rates.

3. **Monsoon Concentration Distribution (Box & Whisker / Stacked Bar)**:
   - Drag `Season` to **Columns** (*Winter, Pre-Monsoon, Monsoon, Post-Monsoon*).
   - Drag `SUM(Total Precipitation)` to **Rows**.
   - Drag `City` to **Color**.
   - Highlights Mumbai's extreme monsoon concentration (> 85% rain in June–Sept) vs. Chennai's post-monsoon peak (Oct–Nov).

---

## Dashboard 3: Climate Anomaly & Extreme Event Intelligence

### Objective
Surface extreme heatwaves, coldwaves, severe rainfall events, and standardized departures (Z-scores) from the 2000–2015 reference baseline.

### Data Source
Connect to `tableau_city_anomalies.csv`.

### Step-by-Step Worksheet Creation

1. **Standardized Anomaly Z-Score Timeline**:
   - Drag `Date` (Continuous Day) to **Columns**.
   - Drag `Z-Score` to **Rows**.
   - Create a Calculated Field `Departure Type`:
     ```tableau
     IF [Z-Score] >= 2.0 THEN "Positive Anomaly (Heat/Rain)"
     ELSEIF [Z-Score] <= -2.0 THEN "Negative Anomaly (Cold)"
     ELSE "Normal Variance"
     END
     ```
   - Drag `Departure Type` to **Color** (Red for positive, Blue for negative).
   - Add Reference Lines at $Z = +2.0$, $+2.5$, $-2.0$, $-2.5$.

2. **Extreme Events Breakdown by Severity & Type**:
   - Drag `Anomaly Type` (*Heatwave, Coldwave, Extreme Rainfall*) to **Rows**.
   - Drag `Severity` (*Moderate, Severe, Extreme*) to **Columns**.
   - Drag `COUNT(Tableau City Anomalies)` to **Text** and **Color** (Heatmap view).
   - Filter by `City`.

3. **Annual Climate Warming Stripes (Ed Hawkins Style)**:
   - Connect to `tableau_monthly_trends.csv`.
   - Calculate annual temperature departure: `[AVG(Temp)] - [Baseline Mean]`.
   - Drag `Year` to **Columns**.
   - Change Mark type to **Gantt Bar** or **Square**.
   - Drag `Departure` to **Color** with diverging *Red-Blue (Reversed)* palette.

---

## Publication to Tableau Public

1. Open Tableau Desktop / Tableau Public.
2. Select **Text File** -> Navigate to `~/Desktop/AtmosIQ/data/tableau/`.
3. Build the worksheets and arrange into the 3 dashboard tabs.
4. Go to **Server** -> **Tableau Public** -> **Save to Tableau Public As...**.
5. Sign in to your Tableau Public account and assign the project title: `AtmosIQ: Climate Intelligence & Predictive Analytics`.
