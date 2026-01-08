#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
predict_solar_v2.py
===================
Prediction script for Solar Radiation V2 Model (Hybrid ML Ensemble).

Generates 24h ahead predictions for all 34 provinces.

Author: Senior ML Engineer
"""

import json
import logging
import pickle
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
ARTIFACTS_DIR = BASE_DIR / "artifacts_solar_v2"
OUTPUT_DIR = BASE_DIR / "predictions_v2_hybrid"

TIME_COL = "time"
TARGET_COL = "shortwave_radiation"
FORECAST_HORIZON = 24


# ============================================================================
# ARTIFACT LOADING
# ============================================================================

def load_artifacts(province: str) -> Dict[str, Any]:
    """Load all model artifacts for a province."""
    logger.info(f"Loading artifacts for {province}...")

    # Load metadata
    metadata_path = ARTIFACTS_DIR / f"{province}_metadata.json"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata not found: {metadata_path}")

    with open(metadata_path, 'r') as f:
        metadata = json.load(f)

    # Load scaler
    scaler_path = ARTIFACTS_DIR / f"{province}_scaler.pkl"
    with open(scaler_path, 'rb') as f:
        scaler = pickle.load(f)

    # Load models
    models = {}
    for model_name in ['ridge', 'gb', 'rf']:
        model_path = ARTIFACTS_DIR / f"{province}_{model_name}_model.pkl"
        if model_path.exists():
            with open(model_path, 'rb') as f:
                models[model_name] = pickle.load(f)

    # Load climatology
    clim_path = ARTIFACTS_DIR / f"{province}_climatology.csv"
    climatology = pd.read_csv(clim_path)

    return {
        'metadata': metadata,
        'scaler': scaler,
        'models': models,
        'climatology': climatology,
        'weights': metadata.get('weights', {'ridge': 0.33, 'gb': 0.34, 'rf': 0.33}),
        'feature_cols': metadata.get('feature_cols', [])
    }


# ============================================================================
# FEATURE ENGINEERING (must match training)
# ============================================================================

def apply_hourly_climatology(timestamps: pd.DatetimeIndex,
                             climatology: pd.DataFrame) -> pd.Series:
    """Apply hourly climatology to get baseline predictions."""
    lookup = climatology.set_index(['month', 'hour'])

    predictions = []
    for ts in timestamps:
        key = (ts.month, ts.hour)
        if key in lookup.index:
            predictions.append(lookup.loc[key, 'mean'])
        else:
            predictions.append(0.0)

    return pd.Series(predictions, index=timestamps, name='climatology_pred')


def build_features_v2(df: pd.DataFrame, climatology: pd.DataFrame = None) -> pd.DataFrame:
    """Build feature set matching training."""
    features = pd.DataFrame(index=df.index)

    # Time features
    hour = df.index.hour
    month = df.index.month
    doy = df.index.dayofyear

    features['hour'] = hour
    features['month'] = month

    # Fourier terms for smooth daily pattern
    for k in [1, 2, 3]:
        features[f'hour_sin_{k}'] = np.sin(2 * np.pi * k * hour / 24)
        features[f'hour_cos_{k}'] = np.cos(2 * np.pi * k * hour / 24)

    # Fourier terms for annual pattern
    for k in [1, 2]:
        features[f'doy_sin_{k}'] = np.sin(2 * np.pi * k * doy / 365.25)
        features[f'doy_cos_{k}'] = np.cos(2 * np.pi * k * doy / 365.25)

    # Binary indicators
    features['is_daylight'] = ((hour >= 6) & (hour <= 18)).astype(float)
    features['is_peak_hours'] = ((hour >= 10) & (hour <= 14)).astype(float)
    features['is_wet_season'] = ((month >= 5) & (month <= 10)).astype(float)

    # Climatology baseline
    if climatology is not None:
        features['clim_mean'] = apply_hourly_climatology(df.index, climatology).values

    # Cloud features
    if 'cloudcover' in df.columns:
        cc = df['cloudcover'].copy()
        if cc.max() > 1:
            cc = cc / 100.0

        features['cloudcover'] = cc
        features['cloudcover_sq'] = cc ** 2
        features['cloudcover_inv'] = 1 - cc

        # Cloud correction factor
        features['cloud_factor'] = 1 - 0.75 * (cc ** 3.4)
        features['cloud_factor'] = features['cloud_factor'].clip(0.1, 1.0)

        # Climatology adjusted by cloud
        if 'clim_mean' in features.columns:
            features['clim_cloud_adj'] = features['clim_mean'] * features['cloud_factor']

        # Lag features
        features['cloudcover_lag1'] = cc.shift(1)
        features['cloudcover_ma3'] = cc.rolling(3, min_periods=1).mean()

    # Temperature
    if 'temperature_2m' in df.columns:
        features['temperature'] = df['temperature_2m']
        features['temp_normalized'] = (df['temperature_2m'] - 25) / 10

    # Humidity
    if 'relative_humidity_2m' in df.columns:
        hum = df['relative_humidity_2m']
        if hum.max() > 1:
            hum = hum / 100.0
        features['humidity'] = hum
        features['humidity_inv'] = 1 - hum

    # Previous day same hour (use last known value as proxy)
    if TARGET_COL in df.columns:
        features['prev_day_same_hour'] = df[TARGET_COL].shift(24)
    else:
        # Use climatology as fallback
        if 'clim_mean' in features.columns:
            features['prev_day_same_hour'] = features['clim_mean']

    features = features.fillna(0)
    return features


# ============================================================================
# PREDICTION
# ============================================================================

def predict_province(province: str, future_data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Generate predictions for a province."""

    # Load artifacts
    artifacts = load_artifacts(province)
    models = artifacts['models']
    scaler = artifacts['scaler']
    climatology = artifacts['climatology']
    weights = artifacts['weights']
    feature_cols = artifacts['feature_cols']

    # Load historical data to get last timestamp and features
    data_file = DATA_DIR / f"{province}.csv"
    df = pd.read_csv(data_file, parse_dates=[TIME_COL])
    df = df.set_index(TIME_COL)
    df.index = pd.DatetimeIndex(df.index)
    df = df.sort_index()

    last_timestamp = df.index.max()
    logger.info(f"Last data timestamp: {last_timestamp}")

    # Create future timestamps
    future_start = last_timestamp + pd.Timedelta(hours=1)
    future_index = pd.date_range(start=future_start, periods=FORECAST_HORIZON, freq='H')

    logger.info(f"Forecasting: {future_index[0]} to {future_index[-1]}")

    # Prepare future data
    if future_data is not None:
        future_df = future_data.copy()
    else:
        # Use persistence: repeat last 24h of exog data
        last_24h = df.tail(24)
        future_df = pd.DataFrame(index=future_index)

        for col in ['cloudcover', 'temperature_2m', 'relative_humidity_2m']:
            if col in last_24h.columns:
                future_df[col] = last_24h[col].values

    future_df.index = future_index

    # Build features
    features = build_features_v2(future_df, climatology)

    # Ensure all required feature columns exist
    for col in feature_cols:
        if col not in features.columns:
            features[col] = 0

    # Select only required features in correct order
    X_future = features[feature_cols].values

    # Scale
    X_future_scaled = scaler.transform(X_future)

    # Predict with each model
    predictions = {}
    for name, model in models.items():
        predictions[name] = model.predict(X_future_scaled)

    # Ensemble
    w = weights
    y_pred = (w.get('ridge', 0.33) * predictions.get('ridge', np.zeros(FORECAST_HORIZON)) +
              w.get('gb', 0.34) * predictions.get('gb', np.zeros(FORECAST_HORIZON)) +
              w.get('rf', 0.33) * predictions.get('rf', np.zeros(FORECAST_HORIZON)))

    # Apply constraints
    y_pred = np.clip(y_pred, 0, 1200)

    # Zero at night
    night_mask = future_index.hour.isin(list(range(0, 6)) + list(range(19, 24)))
    y_pred[night_mask] = 0

    # Create result DataFrame
    result_df = pd.DataFrame({
        'time': future_index,
        'predicted_radiation': y_pred,
        'model': 'hybrid_v2'
    })

    return result_df


def predict_all_provinces() -> Dict[str, pd.DataFrame]:
    """Generate predictions for all provinces."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Get all provinces
    province_files = sorted(ARTIFACTS_DIR.glob("*_metadata.json"))
    provinces = [f.stem.replace("_metadata", "") for f in province_files]

    logger.info(f"Found {len(provinces)} provinces with trained models")

    results = {}

    for province in provinces:
        try:
            logger.info(f"\nPredicting {province}...")
            result = predict_province(province)

            # Save to CSV
            output_file = OUTPUT_DIR / f"forecast_{province}.csv"
            result.to_csv(output_file, index=False)
            logger.info(f"Saved: {output_file}")

            results[province] = result

        except Exception as e:
            logger.error(f"Error predicting {province}: {e}")

    logger.info(f"\nCompleted predictions for {len(results)} provinces")
    return results


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("SOLAR RADIATION PREDICTION - V2 MODEL")
    logger.info("=" * 60)

    predict_all_provinces()

    logger.info("\nDone!")
