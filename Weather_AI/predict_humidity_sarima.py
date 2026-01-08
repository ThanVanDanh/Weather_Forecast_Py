#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
predict_humidity_sarima.py
==========================
Production-ready SARIMA prediction script for 24h humidity forecasting.

Uses trained SARIMA model to predict relative humidity for the next 24 hours.

Author: Senior Python Developer (10+ years Time Series experience)
Usage:
    python predict_humidity_sarima.py
    python predict_humidity_sarima.py --province An_Giang --hours 24

Python: 3.10+
"""

import argparse
import json
import logging
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Configure logging
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
ARTIFACTS_DIR = BASE_DIR / "artifacts_humidity"
PREDICTIONS_DIR = BASE_DIR / "predictions_humidity"

PROVINCE = "Ha_Noi"
TIME_COL = "time"
TARGET_COL = "relative_humidity_2m"

# Default forecast horizon
FORECAST_HORIZON = 24


# ============================================================================
# DATA LOADING
# ============================================================================

def load_latest_data(filepath: Path, n_samples: int = 72) -> pd.Series:
    """
    Load latest data from CSV for model state update.

    Args:
        filepath: Path to data file
        n_samples: Number of recent samples to load

    Returns:
        Series with target variable
    """
    logger.info(f"Loading latest data from {filepath}")

    df = pd.read_csv(filepath, parse_dates=[TIME_COL])
    df = df.sort_values(TIME_COL).reset_index(drop=True)
    df = df.set_index(TIME_COL)

    # Get last n samples
    recent_data = df[TARGET_COL].tail(n_samples)

    logger.info(f"Loaded {len(recent_data)} recent samples")
    logger.info(f"Data range: {recent_data.index.min()} to {recent_data.index.max()}")

    return recent_data


def load_model_artifacts(province: str) -> Tuple:
    """
    Load trained model and metadata.

    Args:
        province: Province name

    Returns:
        Tuple of (model_data, metadata, params)
    """
    logger.info(f"Loading model artifacts for {province}")

    # Province-specific directory
    province_dir = ARTIFACTS_DIR / province

    # Load lightweight model
    model_path = province_dir / f"{province}_humidity_sarima.pkl"
    with open(model_path, 'rb') as f:
        model_data = pickle.load(f)

    # Load metadata
    metadata_path = province_dir / f"{province}_metadata.json"
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)

    # Load parameters
    params_path = province_dir / f"{province}_best_params.json"
    with open(params_path, 'r', encoding='utf-8') as f:
        params = json.load(f)

    logger.info(f"Model loaded: SARIMA{tuple(params['order'])}x{tuple(params['seasonal_order'])}")
    logger.info(f"Model performance: MAPE={metadata['performance_metrics']['mape']:.2f}%, "
                f"Accuracy={metadata['performance_metrics']['accuracy']:.2f}%")

    return model_data, metadata, params


# ============================================================================
# PREDICTION
# ============================================================================

def rebuild_model_for_forecast(model_data: dict, recent_data: pd.Series) -> Any:
    """
    Rebuild SARIMA model from saved parameters for forecasting.

    Args:
        model_data: Dictionary with model parameters
        recent_data: Recent data series for model fitting

    Returns:
        Fitted SARIMA model ready for forecasting
    """
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    order = tuple(model_data['order'])
    seasonal_order = tuple(model_data['seasonal_order'])

    logger.info(f"Rebuilding SARIMA{order}x{seasonal_order} with recent data...")

    # Fit model on recent data using saved parameters as initialization
    model = SARIMAX(
        recent_data,
        order=order,
        seasonal_order=seasonal_order,
        enforce_stationarity=False,
        enforce_invertibility=False,
        initialization='approximate_diffuse'
    )

    # Use saved params as start values if available
    try:
        start_params = model_data.get('params', None)
        if start_params:
            model_fit = model.fit(disp=False, start_params=start_params, maxiter=100)
        else:
            model_fit = model.fit(disp=False, maxiter=100)
    except Exception:
        # Fallback to standard fit
        model_fit = model.fit(disp=False, maxiter=200)

    logger.info("Model rebuilt successfully")
    return model_fit


def forecast_next_hours(model, n_hours: int = 24,
                        confidence: float = 0.95) -> Tuple[pd.Series, pd.DataFrame]:
    """
    Generate forecast for next n hours.

    Args:
        model: Fitted SARIMA model
        n_hours: Number of hours to forecast
        confidence: Confidence level for intervals

    Returns:
        Tuple of (predictions Series, confidence intervals DataFrame)
    """
    logger.info(f"Generating {n_hours}-hour forecast...")

    # Generate forecast
    forecast = model.get_forecast(steps=n_hours)

    # Get predictions and confidence intervals
    predictions = forecast.predicted_mean
    conf_int = forecast.conf_int(alpha=1 - confidence)

    # Clip to valid range (0-100%)
    predictions = predictions.clip(0, 100)
    conf_int = conf_int.clip(0, 100)

    return predictions, conf_int


def create_forecast_dataframe(predictions: pd.Series,
                              conf_int: pd.DataFrame,
                              last_timestamp: pd.Timestamp) -> pd.DataFrame:
    """
    Create a structured forecast DataFrame.

    Args:
        predictions: Predicted values
        conf_int: Confidence intervals
        last_timestamp: Last timestamp in training data

    Returns:
        DataFrame with forecasts
    """
    # Create future timestamps
    future_timestamps = pd.date_range(
        start=last_timestamp + timedelta(hours=1),
        periods=len(predictions),
        freq='H'
    )

    forecast_df = pd.DataFrame({
        'timestamp': future_timestamps,
        'predicted_humidity': predictions.values,
        'lower_bound': conf_int.iloc[:, 0].values,
        'upper_bound': conf_int.iloc[:, 1].values,
        'hour': future_timestamps.hour,
        'day_of_week': future_timestamps.dayofweek,
        'date': future_timestamps.date
    })

    return forecast_df


# ============================================================================
# VISUALIZATION
# ============================================================================

def plot_forecast(forecast_df: pd.DataFrame,
                  historical_data: pd.Series = None,
                  province: str = PROVINCE,
                  save_path: Path = None):
    """
    Plot forecast with confidence intervals.
    """
    fig, ax = plt.subplots(figsize=(14, 6))

    # Plot historical data if available
    if historical_data is not None:
        ax.plot(historical_data.index, historical_data.values,
                'b-', linewidth=1, alpha=0.7, label='Historical')

    # Plot forecast
    ax.plot(forecast_df['timestamp'], forecast_df['predicted_humidity'],
            'r-', linewidth=2, marker='o', markersize=4, label='Forecast')

    # Plot confidence intervals
    ax.fill_between(
        forecast_df['timestamp'],
        forecast_df['lower_bound'],
        forecast_df['upper_bound'],
        color='red', alpha=0.2, label='95% CI'
    )

    ax.set_xlabel('Time')
    ax.set_ylabel('Relative Humidity (%)')
    ax.set_title(f'24-Hour Humidity Forecast - {province}\n'
                 f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 100)

    plt.xticks(rotation=45)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"Saved forecast plot: {save_path}")
    plt.close()


def plot_hourly_forecast_bars(forecast_df: pd.DataFrame,
                              province: str = PROVINCE,
                              save_path: Path = None):
    """
    Plot forecast as bar chart by hour.
    """
    fig, ax = plt.subplots(figsize=(14, 6))

    x = range(len(forecast_df))

    # Create bars
    bars = ax.bar(x, forecast_df['predicted_humidity'],
                  color='steelblue', alpha=0.7, edgecolor='black')

    # Add error bars for confidence intervals
    yerr_lower = forecast_df['predicted_humidity'] - forecast_df['lower_bound']
    yerr_upper = forecast_df['upper_bound'] - forecast_df['predicted_humidity']
    ax.errorbar(x, forecast_df['predicted_humidity'],
                yerr=[yerr_lower, yerr_upper],
                fmt='none', color='red', capsize=3, capthick=1)

    # Labels
    ax.set_xticks(x)
    ax.set_xticklabels([f"{t.strftime('%H:%M')}\n{t.strftime('%d/%m')}"
                        for t in forecast_df['timestamp']],
                       rotation=45, fontsize=8)

    ax.set_xlabel('Time')
    ax.set_ylabel('Predicted Humidity (%)')
    ax.set_title(f'24-Hour Humidity Forecast - {province}')
    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.3, axis='y')

    # Add value labels on bars
    for bar, val in zip(bars, forecast_df['predicted_humidity']):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                f'{val:.0f}', ha='center', va='bottom', fontsize=7)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"Saved bar chart: {save_path}")
    plt.close()


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main prediction pipeline."""
    parser = argparse.ArgumentParser(
        description="Predict humidity for the next 24 hours using trained SARIMA model"
    )
    parser.add_argument(
        '--province', type=str, default=PROVINCE,
        help=f'Province name (default: {PROVINCE})'
    )
    parser.add_argument(
        '--hours', type=int, default=FORECAST_HORIZON,
        help=f'Number of hours to forecast (default: {FORECAST_HORIZON})'
    )
    parser.add_argument(
        '--confidence', type=float, default=0.95,
        help='Confidence level for prediction intervals (default: 0.95)'
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("SARIMA HUMIDITY FORECASTING - PREDICTION")
    logger.info("=" * 60)
    logger.info(f"Province: {args.province}")
    logger.info(f"Forecast Horizon: {args.hours} hours")
    logger.info(f"Confidence Level: {args.confidence * 100}%")
    logger.info("=" * 60)

    # Create output directory
    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)

    # Load model data
    try:
        model_data, metadata, params = load_model_artifacts(args.province)
    except FileNotFoundError as e:
        logger.error(f"Model artifacts not found. Please train the model first.")
        logger.error(f"Run: python train_humidity_sarima.py --province {args.province}")
        return

    # Load latest data for forecasting (need enough history for seasonal pattern)
    data_file = DATA_DIR / f"{args.province}.csv"
    if not data_file.exists():
        logger.error(f"Data file not found: {data_file}")
        return

    # Load more data for proper model fitting (at least 7 days for seasonal pattern)
    recent_data = load_latest_data(data_file, n_samples=24 * 30)  # Last 30 days
    last_timestamp = recent_data.index.max()

    # Rebuild model for forecasting using recent data
    model = rebuild_model_for_forecast(model_data, recent_data)

    # Generate forecast
    predictions, conf_int = forecast_next_hours(
        model,
        n_hours=args.hours,
        confidence=args.confidence
    )

    # Create forecast dataframe
    forecast_df = create_forecast_dataframe(predictions, conf_int, last_timestamp)

    # Save predictions to CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = PREDICTIONS_DIR / f"{args.province}_humidity_forecast_{timestamp}.csv"
    forecast_df.to_csv(output_file, index=False)
    logger.info(f"Saved forecast to: {output_file}")

    # Get last 48 hours for visualization
    display_data = recent_data.tail(48)

    # Generate visualizations
    plot_forecast(
        forecast_df,
        historical_data=display_data,
        province=args.province,
        save_path=PREDICTIONS_DIR / f"{args.province}_forecast_plot_{timestamp}.png"
    )

    plot_hourly_forecast_bars(
        forecast_df,
        province=args.province,
        save_path=PREDICTIONS_DIR / f"{args.province}_forecast_bars_{timestamp}.png"
    )

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("FORECAST SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Forecast Period: {forecast_df['timestamp'].min()} to {forecast_df['timestamp'].max()}")
    logger.info(f"\nPredicted Humidity Statistics:")
    logger.info(f"  Min:  {forecast_df['predicted_humidity'].min():.1f}%")
    logger.info(f"  Max:  {forecast_df['predicted_humidity'].max():.1f}%")
    logger.info(f"  Mean: {forecast_df['predicted_humidity'].mean():.1f}%")
    logger.info(f"\nHourly Forecast:")
    logger.info("-" * 50)

    for _, row in forecast_df.iterrows():
        logger.info(
            f"  {row['timestamp'].strftime('%Y-%m-%d %H:%M')}: "
            f"{row['predicted_humidity']:.1f}% "
            f"[{row['lower_bound']:.1f}% - {row['upper_bound']:.1f}%]"
        )

    logger.info("=" * 60)
    logger.info(f"Model Accuracy: {metadata['performance_metrics']['accuracy']:.2f}%")
    logger.info(f"Output saved to: {PREDICTIONS_DIR}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
