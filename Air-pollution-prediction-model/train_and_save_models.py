"""
Train the best model for each pollutant on the FULL dataset and save as pickle files.

What gets saved per pollutant:
  - The trained model (Ridge or GradientBoosting)
  - The StandardScaler (so new inputs get scaled the same way)
  - The feature names (so you know what inputs to provide)

Usage after saving:
  import pickle
  with open('models/pm10_model.pkl', 'rb') as f:
      bundle = pickle.load(f)
  model = bundle['model']
  scaler = bundle['scaler']
  features = bundle['features']
  # Scale your new data the same way, then: model.predict(scaled_data)
"""

import pandas as pd
import numpy as np
import pickle
import os
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import LeaveOneOut, cross_val_predict
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import warnings
warnings.filterwarnings('ignore')

# ==================== 1. LOAD AND PREPARE DATA ====================
f_lasepa = r'C:\Users\crypt\Downloads\LASEPA JANUARY_DECEMBER 2025.xlsx'
f_nimet = r'C:\Users\crypt\Downloads\NIMET METEROLOGICAL DATA.xlsx'
f_lacvis = r'C:\Users\crypt\Downloads\LACVIS_ OJODU_GAS EMISSION DATA Jan to Dec 2025.xlsx'

# LASEPA
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

# NIMET
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

# LACVIS
lacvis = pd.read_excel(f_lacvis)
lacvis.columns = ['Model','Make','idl_PM10','idl_PM25','idl_NO2','idl_CO','hgh_PM10','hgh_PM25','hgh_NO2','hgh_CO']
n = len(lacvis)
lacvis['Month'] = np.repeat(range(1,13), n//12 + 1)[:n]
lacvis_monthly = lacvis.groupby('Month')[['idl_PM10','idl_PM25','idl_NO2','idl_CO']].mean().reset_index()

# MERGE
merged = lasepa.merge(nimet, on=['Station','Month'], how='inner')
merged = merged.merge(lacvis_monthly, on='Month', how='left')
merged_model = pd.get_dummies(merged, columns=['Station'], drop_first=True)

# ==================== 2. DEFINE FEATURES AND MODELS ====================
met_features = ['RelHumidity', 'WindSpeed', 'WindDir', 'Rainfall', 'Temperature']
lacvis_features = ['idl_PM10', 'idl_PM25', 'idl_NO2', 'idl_CO']
station_features = [c for c in merged_model.columns if c.startswith('Station_')]
all_features = met_features + lacvis_features + station_features

best_model_configs = {
    'PM10':  ('Ridge Regression',  Ridge(alpha=1.0)),
    'PM2.5': ('Ridge Regression',  Ridge(alpha=1.0)),
    'NO2':   ('Ridge Regression',  Ridge(alpha=1.0)),
    'CO':    ('Gradient Boosting', GradientBoostingRegressor(n_estimators=100, max_depth=3, learning_rate=0.1, random_state=42))
}

# ==================== 3. TRAIN AND SAVE ====================
output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')
os.makedirs(output_dir, exist_ok=True)

print('=' * 70)
print('TRAINING BEST MODELS AND SAVING AS PICKLE FILES')
print('=' * 70)

for target, (model_name, model) in best_model_configs.items():
    X = merged_model[all_features].values
    y = merged_model[target].values

    # Fit scaler on full data
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Cross-validated score (for reporting)
    loo = LeaveOneOut()
    y_pred_cv = cross_val_predict(model, X_scaled, y, cv=loo)
    r2_cv = r2_score(y, y_pred_cv)
    mae_cv = mean_absolute_error(y, y_pred_cv)

    # Train on FULL data for deployment
    model.fit(X_scaled, y)
    r2_train = model.score(X_scaled, y)

    # Save bundle
    bundle = {
        'model': model,
        'scaler': scaler,
        'features': all_features,
        'target': target,
        'model_name': model_name,
        'r2_cv': round(r2_cv, 4),
        'r2_train': round(r2_train, 4),
        'mae_cv': round(mae_cv, 2),
        'training_data_stats': {
            'n_samples': len(y),
            'y_mean': round(y.mean(), 2),
            'y_std': round(y.std(), 2),
            'feature_means': dict(zip(all_features, scaler.mean_.round(4))),
            'feature_stds': dict(zip(all_features, scaler.scale_.round(4)))
        }
    }

    fname = f'{target.replace(".", "").lower()}_model.pkl'
    fpath = os.path.join(output_dir, fname)
    with open(fpath, 'wb') as f:
        pickle.dump(bundle, f)

    print(f'\n{target}:')
    print(f'  Model:          {model_name}')
    print(f'  LOO-CV R²:      {r2_cv:.4f}')
    print(f'  Training R²:    {r2_train:.4f}')
    print(f'  LOO-CV MAE:     {mae_cv:.2f} ug/m3')
    print(f'  Saved to:       {fpath}')

print(f'\n{"=" * 70}')
print(f'All models saved to: {output_dir}')
print(f'{"=" * 70}')

# ==================== 4. VERIFY BY LOADING BACK ====================
print('\n\nVERIFICATION — Loading models back and making a sample prediction:')
print('-' * 70)

sample_input = {
    'RelHumidity': 78.0,
    'WindSpeed': 5.2,
    'WindDir': 210.0,
    'Rainfall': 150.0,
    'Temperature': 28.5,
    'idl_PM10': 45.0,
    'idl_PM25': 30.0,
    'idl_NO2': 15.0,
    'idl_CO': 200.0,
    'Station_Mushin': 0,
    'Station_Oshodi': 1
}

print(f'\nSample input (Oshodi station, wet season conditions):')
for k, v in sample_input.items():
    print(f'  {k:20s}: {v}')

print(f'\nPredictions:')
for target in ['PM10', 'PM2.5', 'NO2', 'CO']:
    fname = f'{target.replace(".", "").lower()}_model.pkl'
    fpath = os.path.join(output_dir, fname)
    with open(fpath, 'rb') as f:
        bundle = pickle.load(f)

    X_new = np.array([[sample_input[feat] for feat in bundle['features']]])
    X_new_scaled = bundle['scaler'].transform(X_new)
    prediction = bundle['model'].predict(X_new_scaled)[0]

    print(f'  {target:8s}: {prediction:.2f} ug/m3  (model: {bundle["model_name"]}, CV R²: {bundle["r2_cv"]})')

