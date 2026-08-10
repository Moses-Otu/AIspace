"""
Load saved models and predict air pollutant concentrations.

HOW TO USE:
  1. Run train_and_save_models.py first (creates the .pkl files)
  2. Edit the input values below OR call predict_pollutants() from your own code
  3. Run: python predict.py

INPUTS REQUIRED:
  - RelHumidity: Relative humidity (%)
  - WindSpeed: Wind speed (knots)
  - WindDir: Wind direction (degrees)
  - Rainfall: Monthly rainfall (mm)
  - Temperature: Average temperature (C)
  - idl_PM10: Mean vehicle idle PM10 (ug/m3)
  - idl_PM25: Mean vehicle idle PM2.5 (ug/m3)
  - idl_NO2: Mean vehicle idle NO2 (ug/m3)
  - idl_CO: Mean vehicle idle CO (ug/m3)
  - Station: 'Ikeja', 'Oshodi', or 'Mushin'
"""

import pickle
import numpy as np
import os

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')

def load_model(target):
    fname = f'{target.replace(".", "").lower()}_model.pkl'
    fpath = os.path.join(MODEL_DIR, fname)
    with open(fpath, 'rb') as f:
        return pickle.load(f)


def predict_pollutants(rel_humidity, wind_speed, wind_dir, rainfall, temperature,
                       idl_pm10, idl_pm25, idl_no2, idl_co,
                       station='Ikeja'):
    """
    Predict PM10, PM2.5, NO2, CO concentrations from weather + vehicle emission inputs.

    Parameters
    ----------
    rel_humidity : float  — Relative humidity (%)
    wind_speed   : float  — Wind speed (knots)
    wind_dir     : float  — Wind direction (degrees)
    rainfall     : float  — Monthly rainfall (mm)
    temperature  : float  — Average temperature (C)
    idl_pm10     : float  — Mean vehicle idle PM10 (ug/m3)
    idl_pm25     : float  — Mean vehicle idle PM2.5 (ug/m3)
    idl_no2      : float  — Mean vehicle idle NO2 (ug/m3)
    idl_co       : float  — Mean vehicle idle CO (ug/m3)
    station      : str    — 'Ikeja', 'Oshodi', or 'Mushin'

    Returns
    -------
    dict : {'PM10': value, 'PM2.5': value, 'NO2': value, 'CO': value}
    """
    station_mushin = 1 if station == 'Mushin' else 0
    station_oshodi = 1 if station == 'Oshodi' else 0

    input_values = {
        'RelHumidity': rel_humidity,
        'WindSpeed': wind_speed,
        'WindDir': wind_dir,
        'Rainfall': rainfall,
        'Temperature': temperature,
        'idl_PM10': idl_pm10,
        'idl_PM25': idl_pm25,
        'idl_NO2': idl_no2,
        'idl_CO': idl_co,
        'Station_Mushin': station_mushin,
        'Station_Oshodi': station_oshodi
    }

    results = {}
    for target in ['PM10', 'PM2.5', 'NO2', 'CO']:
        bundle = load_model(target)
        X = np.array([[input_values[f] for f in bundle['features']]])
        X_scaled = bundle['scaler'].transform(X)
        results[target] = round(bundle['model'].predict(X_scaled)[0], 2)

    return results


def print_model_info():
    """Print details about each saved model."""
    print('=' * 60)
    print('SAVED MODEL INFORMATION')
    print('=' * 60)
    for target in ['PM10', 'PM2.5', 'NO2', 'CO']:
        bundle = load_model(target)
        print(f'\n{target}:')
        print(f'  Model type:    {bundle["model_name"]}')
        print(f'  LOO-CV R²:     {bundle["r2_cv"]}')
        print(f'  Training R²:   {bundle["r2_train"]}')
        print(f'  LOO-CV MAE:    {bundle["mae_cv"]} ug/m3')
        print(f'  Features:      {bundle["features"]}')
        stats = bundle['training_data_stats']
        print(f'  Training mean: {stats["y_mean"]} ug/m3')
        print(f'  Training std:  {stats["y_std"]} ug/m3')


if __name__ == '__main__':
    print_model_info()

    # ===== EXAMPLE: Predict for Oshodi in a wet-season month =====
    print('\n' + '=' * 60)
    print('SAMPLE PREDICTION')
    print('=' * 60)

    predictions = predict_pollutants(
        rel_humidity=78.0,
        wind_speed=5.2,
        wind_dir=210.0,
        rainfall=150.0,
        temperature=28.5,
        idl_pm10=45.0,
        idl_pm25=30.0,
        idl_no2=15.0,
        idl_co=200.0,
        station='Oshodi'
    )

    print('\nInput: Oshodi, wet season (high humidity, moderate wind, heavy rain)')
    print('\nPredicted ambient pollutant concentrations:')
    for pollutant, value in predictions.items():
        print(f'  {pollutant:8s}: {value:8.2f} ug/m3')

    # ===== EXAMPLE: Predict for Ikeja in a dry-season month =====
    print('\n' + '-' * 60)

    predictions_dry = predict_pollutants(
        rel_humidity=55.0,
        wind_speed=3.0,
        wind_dir=30.0,
        rainfall=5.0,
        temperature=32.0,
        idl_pm10=45.0,
        idl_pm25=30.0,
        idl_no2=15.0,
        idl_co=200.0,
        station='Ikeja'
    )

    print('\nInput: Ikeja, dry season (low humidity, light wind, no rain)')
    print('\nPredicted ambient pollutant concentrations:')
    for pollutant, value in predictions_dry.items():
        print(f'  {pollutant:8s}: {value:8.2f} ug/m3')

    print('\n' + '=' * 60)
    print('Notice: dry season predicts HIGHER concentrations — less')
    print('wind and rain means less pollutant dispersion.')
    print('=' * 60)
