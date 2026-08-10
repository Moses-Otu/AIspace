# Air Quality Prediction in Lagos State: Analyzing the Impact of Vehicle Emissions and Meteorological Conditions on Ambient Air Pollutant Concentrations (2025)

## Overview

This project investigates whether **vehicular emissions** (LACVIS data) and **meteorological conditions** (NIMET data) relate to and can predict **ambient air pollutant concentrations** (LASEPA data) across three monitoring stations in Lagos State, Nigeria, for the year 2025.

## Research Objectives

1. **Correlation Analysis**: Determine if LACVIS vehicle emission data and NIMET meteorological data are statistically related to LASEPA ambient air quality measurements for the same period.
2. **Predictive Modeling**: Build machine learning models that predict air pollutant concentrations (LASEPA) using meteorological parameters (NIMET) and vehicle emission data (LACVIS) as predictors.

## Data Sources

### 1. LASEPA Air Quality Data (Target Variable)
- **Source**: Lagos State Environmental Protection Agency
- **Coverage**: January 1 – December 31, 2025 (hourly readings)
- **Stations**: Shangisha/Oregun-Ikeja, Oshodi/Isolo, Mushin
- **Variables**: PM10, PM2.5, NO2, CO (all in ug/m3)
- **Total records**: ~8,400+ hourly readings per station

### 2. NIMET Meteorological Data (Predictor)
- **Source**: Nigerian Meteorological Agency
- **Coverage**: January – December 2025 (monthly averages)
- **Stations**: Ikeja, Oshodi, Mushin (matched to LASEPA stations)
- **Variables**: Relative Humidity (%), Wind Speed (knots), Wind Direction (degrees), Rainfall (mm), Average Temperature (°C)

### 3. LACVIS Vehicle Emission Data (Predictor)
- **Source**: Lagos Computerized Vehicle Inspection Service (Ojodu center)
- **Coverage**: January – December 2025 (no individual dates recorded)
- **Records**: 8,173 vehicles tested
- **Variables (idle)**: PM10, PM2.5, NO2, CO (ug/m3) — engine idling
- **Variables (revved)**: PM10, PM2.5, NO2, CO (ug/m3) — engine revved at high RPM

## Methodology

### Step 1: Data Preprocessing

#### LASEPA Data
- Hourly readings are aggregated to **monthly averages** per station to match NIMET's temporal resolution.
- Date column is parsed and month extracted for grouping.

#### NIMET Data
- Already at monthly resolution. Parsed from a multi-block Excel layout (one block per station).
- Station names mapped to match LASEPA station identifiers.

#### LACVIS Data
- **Critical limitation**: LACVIS has no date/timestamp column — only vehicle model, make, and emission readings.
- For modeling purposes, the 8,173 vehicles are distributed uniformly across 12 months (a proxy assumption), and monthly means are computed.
- This limitation is acknowledged throughout the analysis.

### Step 2: Data Merging
- All three datasets are merged on `Station` and `Month` keys.
- Final merged dataset: **36 observations** (12 months × 3 stations).
- Feature set: 5 meteorological + 4 vehicle emission (idle) + 2 station dummy variables = **11 predictors**.

### Step 3: Correlation Analysis

Three correlation methods are applied:

| Method | Purpose |
|--------|---------|
| **Pearson's r** | Measures linear correlation strength and direction |
| **Spearman's rho** | Non-parametric rank correlation (robust to outliers) |
| **Multiple Linear Regression** | Multivariate relationships with standardized coefficients |

Significance levels: * p < 0.05, ** p < 0.01, *** p < 0.001

### Step 4: Predictive Modeling

Four machine learning models are trained and compared:

| Model | Description | Why Used |
|-------|-------------|----------|
| **Linear Regression** | Ordinary Least Squares | Baseline benchmark |
| **Ridge Regression** | L2-regularized linear model (alpha=1.0) | Handles multicollinearity in small datasets |
| **Random Forest** | Ensemble of 100 decision trees (max_depth=4) | Captures non-linear relationships; provides feature importance |
| **Gradient Boosting** | Sequential ensemble of 100 trees (max_depth=3, lr=0.1) | Often best for structured/tabular data |

#### Validation Strategy
- **Leave-One-Out Cross-Validation (LOO-CV)** is used because the dataset is small (n=36).
- Each observation is held out once while the model trains on the remaining 35.
- This provides an unbiased estimate of generalization performance.

#### Evaluation Metrics
- **R² (Coefficient of Determination)**: Proportion of variance explained (1.0 = perfect, 0.0 = no better than mean)
- **MAE (Mean Absolute Error)**: Average absolute prediction error in ug/m3
- **RMSE (Root Mean Squared Error)**: Penalizes larger errors more than MAE

### Step 5: Feature Importance & Model Comparison
- Random Forest feature importances identify which predictors matter most.
- A NIMET-only model is compared against a NIMET+LACVIS model to quantify the added value of vehicle emission data.

## Key Results

### Correlation Findings
- **Wind Speed** is the strongest meteorological predictor of PM10 (r = -0.55, p < 0.001) and PM2.5 (r = -0.55, p < 0.001).
- Higher wind speeds disperse pollutants, reducing ambient concentrations.
- LACVIS vehicle emissions show weak direct correlation with LASEPA readings (limited by absence of temporal data).

### Model Performance (LOO Cross-Validated R²)

| Pollutant | Linear Reg | Ridge | Random Forest | Gradient Boosting | Best |
|-----------|-----------|-------|---------------|-------------------|------|
| PM10 | 0.42 | **0.47** | 0.38 | 0.38 | Ridge |
| PM2.5 | 0.40 | **0.45** | 0.41 | 0.36 | Ridge |
| NO2 | 0.09 | **0.17** | 0.16 | 0.08 | Ridge |
| CO | 0.34 | 0.40 | 0.39 | **0.73** | Gradient Boosting |

### LACVIS Added Value

| Pollutant | NIMET-only R² | NIMET+LACVIS R² | Change |
|-----------|--------------|-----------------|--------|
| PM10 | 0.29 | 0.38 | +0.09 |
| PM2.5 | 0.31 | 0.41 | +0.10 |
| NO2 | 0.16 | 0.16 | -0.01 |
| CO | 0.44 | 0.39 | -0.05 |

## Limitations

1. **LACVIS has no temporal dimension** — without test dates, the monthly proxy is an assumption. True temporal correlation between vehicle testing patterns and ambient air quality cannot be established.
2. **Small sample size** (n=36) limits the complexity of models that can be reliably trained.
3. **NIMET data is monthly averaged**, which smooths out day-to-day and diurnal meteorological variability that strongly affects pollutant dispersion.
4. **Single LACVIS testing center** (Ojodu) — may not represent the full spatial distribution of vehicle emissions across Lagos.

## How to Run

### Google Colab (Recommended)
1. Upload `thesis_analysis.ipynb` to Google Colab
2. Upload the three Excel data files when prompted
3. Run all cells sequentially (Runtime > Run all)

### Local Environment
```bash
pip install pandas numpy scipy scikit-learn matplotlib seaborn openpyxl
python thesis_analysis.py
```

## File Structure

```
Thesis_Air_Quality_Analysis/
|-- README.md                    # This file
|-- thesis_analysis.ipynb        # Google Colab notebook (main analysis)
|-- thesis_analysis.py           # Standalone Python script (same analysis)
|-- data/                        # Place your Excel files here (for local runs)
|   |-- LASEPA JANUARY_DECEMBER 2025.xlsx
|   |-- NIMET METEROLOGICAL DATA.xlsx
|   |-- LACVIS_ OJODU_GAS EMISSION DATA Jan to Dec 2025.xlsx
```

## Dependencies

- Python 3.8+
- pandas, numpy, scipy, scikit-learn, matplotlib, seaborn, openpyxl

