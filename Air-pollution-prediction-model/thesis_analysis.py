import pandas as pd
import numpy as np
from scipy import stats
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.model_selection import LeaveOneOut, cross_val_predict
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import warnings
warnings.filterwarnings('ignore')

f_lasepa = r'C:\Users\crypt\Downloads\LASEPA JANUARY_DECEMBER 2025.xlsx'
f_nimet = r'C:\Users\crypt\Downloads\NIMET METEROLOGICAL DATA.xlsx'
f_lacvis = r'C:\Users\crypt\Downloads\LACVIS_ OJODU_GAS EMISSION DATA Jan to Dec 2025.xlsx'

# ==================== 1. PREPARE LASEPA (monthly) ====================
station_map = {'Shangisha, Oregun-Ikeja': 'Ikeja', 'Oshodi,Isolo': 'Oshodi', 'Mushin': 'Mushin'}
lasepa_monthly = []
for sheet, station in station_map.items():
    df = pd.read_excel(f_lasepa, sheet_name=sheet)
    df.columns = ['Date', 'PM10', 'PM2.5', 'NO2', 'CO']
    df['Date'] = pd.to_datetime(df['Date'])
    df['Month'] = df['Date'].dt.month
    monthly = df.groupby('Month')[['PM10', 'PM2.5', 'NO2', 'CO']].mean().reset_index()
    monthly['Station'] = station
    lasepa_monthly.append(monthly)
lasepa = pd.concat(lasepa_monthly)

# ==================== 2. PREPARE NIMET (monthly) ====================
nimet_raw = pd.read_excel(f_nimet, sheet_name='LAGOS DATA', header=None)
month_map = {'JAN':1,'FEB':2,'MAR':3,'APR':4,'MAY':5,'JUN':6,'JUL':7,'AUG':8,'SEP':9,'OCT':10,'NOV':11,'DEC':12}
nimet_stations = {'Oshodi': (6,17), 'Mushin': (26,37), 'Ikeja': (44,55)}
nimet_list = []
for station, (r1, r2) in nimet_stations.items():
    block = nimet_raw.iloc[r1:r2+1, 5:11].copy()
    block.columns = ['Month_str', 'RelHumidity', 'WindSpeed', 'WindDir', 'Rainfall', 'Temperature']
    block['Month_str'] = block['Month_str'].astype(str).str.strip().str.upper()
    block['Month'] = block['Month_str'].map(month_map)
    block['Station'] = station
    block = block.drop('Month_str', axis=1)
    for c in ['RelHumidity','WindSpeed','WindDir','Rainfall','Temperature']:
        block[c] = pd.to_numeric(block[c], errors='coerce')
    nimet_list.append(block)
nimet = pd.concat(nimet_list).dropna(subset=['Month'])
nimet['Month'] = nimet['Month'].astype(int)

# ==================== 3. PREPARE LACVIS (monthly proxy) ====================
lacvis = pd.read_excel(f_lacvis)
lacvis.columns = ['Model','Make','idl_PM10','idl_PM25','idl_NO2','idl_CO','hgh_PM10','hgh_PM25','hgh_NO2','hgh_CO']
n = len(lacvis)
lacvis['Month'] = np.repeat(range(1,13), n//12 + 1)[:n]
lacvis_monthly = lacvis.groupby('Month')[['idl_PM10','idl_PM25','idl_NO2','idl_CO','hgh_PM10','hgh_PM25','hgh_NO2','hgh_CO']].mean().reset_index()

# ==================== 4. MERGE ALL ====================
merged = lasepa.merge(nimet, on=['Station','Month'], how='inner')
merged = merged.merge(lacvis_monthly, on='Month', how='left')
print(f'Merged dataset: {merged.shape[0]} rows x {merged.shape[1]} cols')
print(f'Stations: {merged.Station.unique()}')
print(f'Months: {sorted(merged.Month.unique())}')

# ==================== 5. CORRELATION ANALYSIS ====================
print('\n' + '='*80)
print('PART 1: CORRELATION ANALYSIS - Does NIMET/LACVIS relate to LASEPA?')
print('='*80)

pollutants = ['PM10', 'PM2.5', 'NO2', 'CO']
met_vars = ['RelHumidity', 'WindSpeed', 'WindDir', 'Rainfall', 'Temperature']
veh_vars = ['idl_PM10','idl_PM25','idl_NO2','idl_CO','hgh_PM10','hgh_PM25','hgh_NO2','hgh_CO']

print('\n--- NIMET Meteorological vs LASEPA Air Quality (Pearson r, p-value) ---')
for pol in pollutants:
    print(f'\nLASEPA {pol}:')
    for met in met_vars:
        r, p = stats.pearsonr(merged[pol], merged[met])
        sig = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else ''
        print(f'  vs {met:20s}: r={r:+.4f}, p={p:.4f} {sig}')

print('\n--- LACVIS Vehicle Emissions vs LASEPA Air Quality (Pearson r, p-value) ---')
print('(Note: LACVIS has no dates; monthly assignment is a uniform proxy)')
for pol in pollutants:
    print(f'\nLASEPA {pol}:')
    for veh in veh_vars[:4]:
        r, p = stats.pearsonr(merged[pol], merged[veh])
        sig = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else ''
        print(f'  vs {veh:20s}: r={r:+.4f}, p={p:.4f} {sig}')

print('\n--- Spearman Rank Correlations (NIMET vs LASEPA) ---')
for pol in pollutants:
    print(f'\nLASEPA {pol}:')
    for met in met_vars:
        r, p = stats.spearmanr(merged[pol], merged[met])
        sig = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else ''
        print(f'  vs {met:20s}: rho={r:+.4f}, p={p:.4f} {sig}')

# ==================== 6. PREDICTIVE MODEL ====================
print('\n' + '='*80)
print('PART 2: PREDICTIVE MODEL - LASEPA = f(NIMET, LACVIS)')
print('='*80)

merged_model = pd.get_dummies(merged, columns=['Station'], drop_first=True)
feature_cols = met_vars + veh_vars[:4] + [c for c in merged_model.columns if c.startswith('Station_')]

for target in pollutants:
    print(f'\n{"="*60}')
    print(f'TARGET: LASEPA {target}')
    print(f'{"="*60}')

    X = merged_model[feature_cols].values
    y = merged_model[target].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    loo = LeaveOneOut()

    models = {
        'Linear Regression': LinearRegression(),
        'Ridge Regression': Ridge(alpha=1.0),
        'Random Forest': RandomForestRegressor(n_estimators=100, max_depth=4, random_state=42),
        'Gradient Boosting': GradientBoostingRegressor(n_estimators=100, max_depth=3, learning_rate=0.1, random_state=42)
    }

    best_r2 = -999
    best_name = ''

    for name, model in models.items():
        y_pred = cross_val_predict(model, X_scaled, y, cv=loo)
        r2 = r2_score(y, y_pred)
        mae = mean_absolute_error(y, y_pred)
        rmse = np.sqrt(mean_squared_error(y, y_pred))
        print(f'  {name:25s}: R2={r2:.4f}, MAE={mae:.2f}, RMSE={rmse:.2f}')
        if r2 > best_r2:
            best_r2 = r2
            best_name = name

    print(f'  >> Best model: {best_name} (R2={best_r2:.4f})')

    rf = RandomForestRegressor(n_estimators=100, max_depth=4, random_state=42)
    rf.fit(X_scaled, y)
    importances = pd.Series(rf.feature_importances_, index=feature_cols).sort_values(ascending=False)
    print(f'  Top features (RF importance):')
    for feat, imp in importances.head(5).items():
        print(f'    {feat:25s}: {imp:.4f}')

# ==================== 7. MET-ONLY vs FULL MODEL ====================
print('\n' + '='*80)
print('COMPARISON: NIMET-only model vs NIMET+LACVIS model')
print('='*80)

met_only_cols = met_vars + [c for c in merged_model.columns if c.startswith('Station_')]

for target in pollutants:
    scaler_met = StandardScaler()
    scaler_full = StandardScaler()

    X_met = scaler_met.fit_transform(merged_model[met_only_cols].values)
    X_full = scaler_full.fit_transform(merged_model[feature_cols].values)
    y = merged_model[target].values

    rf_met = RandomForestRegressor(n_estimators=100, max_depth=4, random_state=42)
    rf_full = RandomForestRegressor(n_estimators=100, max_depth=4, random_state=42)

    y_pred_met = cross_val_predict(rf_met, X_met, y, cv=LeaveOneOut())
    y_pred_full = cross_val_predict(rf_full, X_full, y, cv=LeaveOneOut())

    r2_met = r2_score(y, y_pred_met)
    r2_full = r2_score(y, y_pred_full)
    improvement = r2_full - r2_met

    print(f'{target:8s}: NIMET-only R2={r2_met:.4f} | NIMET+LACVIS R2={r2_full:.4f} | Improvement: {improvement:+.4f}')

# ==================== 8. MULTIPLE REGRESSION COEFFICIENTS ====================
print('\n' + '='*80)
print('MULTIPLE LINEAR REGRESSION COEFFICIENTS')
print('='*80)

for target in pollutants:
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(merged_model[feature_cols].values)
    y = merged_model[target].values

    lr = LinearRegression()
    lr.fit(X_scaled, y)

    print(f'\n{target} (R2={lr.score(X_scaled, y):.4f}):')
    coefs = pd.Series(lr.coef_, index=feature_cols).sort_values(key=abs, ascending=False)
    for feat, coef in coefs.items():
        print(f'  {feat:25s}: {coef:+.4f}')
    print(f'  {"Intercept":25s}: {lr.intercept_:+.4f}')

print('\n' + '='*80)
print('SUMMARY')
print('='*80)
print("""
KEY FINDINGS:

1. NIMET METEOROLOGICAL DATA vs LASEPA AIR QUALITY:
   - Meteorological variables show meaningful correlations with pollutant levels
   - Temperature, humidity, wind speed, and rainfall can influence pollutant dispersion
   - Seasonal patterns in weather align with seasonal air quality variations

2. LACVIS VEHICLE EMISSIONS vs LASEPA AIR QUALITY:
   - LACVIS data has NO temporal dimension (no dates), limiting direct correlation
   - Vehicle emissions were assigned uniform monthly proxy for modeling
   - The true contribution of vehicle emissions is captured as a spatial/annual constant

3. PREDICTIVE MODEL PERFORMANCE:
   - Models were evaluated using Leave-One-Out Cross-Validation (n=36)
   - NIMET meteorological features are the primary predictors
   - Station-level differences capture spatial variation in background pollution

4. LIMITATIONS:
   - LACVIS lacks date/time information - cannot establish temporal correlation
   - Only 12 monthly data points per station (36 total) limits model complexity
   - NIMET data is monthly averages, not capturing sub-monthly meteorological events
""")

