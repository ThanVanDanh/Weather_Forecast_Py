
import argparse
import json
import logging
import pickle
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import adfuller, kpss


warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.figsize'] = (14, 6)
plt.rcParams['font.size'] = 10
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['axes.labelsize'] = 10


BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
ARTIFACTS_DIR = BASE_DIR / "artifacts_humidity"
PLOTS_DIR = ARTIFACTS_DIR / "plots"


DEFAULT_PROVINCE = "An_Giang"



def get_all_provinces() -> List[str]:
    """Get list of all provinces from CSV files in data folder."""
    csv_files = list(DATA_DIR.glob("*.csv"))
    provinces = [f.stem for f in csv_files if f.stem != "__pycache__"]
    return sorted(provinces)

TIME_COL = "time"
TARGET_COL = "relative_humidity_2m"


SEASONAL_PERIOD = 24


VALIDATION_DAYS = 7
TEST_DAYS = 7


FORECAST_HORIZON = 24


DRY_SEASON_MONTHS = [11, 12, 1, 2, 3, 4]
WET_SEASON_MONTHS = [5, 6, 7, 8, 9, 10]

SARIMA_PARAM_GRID = {
    'p': [0, 1, 2],
    'd': [0, 1],
    'q': [0, 1, 2],
    'P': [0, 1],
    'D': [0, 1],
    'Q': [0, 1],
    's': [SEASONAL_PERIOD]
}


MAX_GRID_SEARCH_ITER = 50


def load_data(filepath: Path) -> pd.DataFrame:

    logger.info(f"Loading data from {filepath}")

    df = pd.read_csv(filepath, parse_dates=[TIME_COL])
    df = df.sort_values(TIME_COL).reset_index(drop=True)
    df = df.set_index(TIME_COL)
    df.index = pd.DatetimeIndex(df.index)
    df = df.sort_index()

    full_idx = pd.date_range(start=df.index.min(), end=df.index.max(), freq='H')
    df = df.reindex(full_idx)
    df.index.name = TIME_COL

    logger.info(f"Loaded {len(df)} rows: {df.index.min()} to {df.index.max()}")

    return df


def handle_missing_values(df: pd.DataFrame, target_col: str) -> pd.DataFrame:

    logger.info("Handling missing values...")

    missing_before = df[target_col].isna().sum()
    missing_pct = (missing_before / len(df)) * 100

    logger.info(f"  Missing values before: {missing_before} ({missing_pct:.2f}%)")

    df[target_col] = df[target_col].interpolate(method='time', limit=6)


    df[target_col] = df[target_col].ffill().bfill()

    missing_after = df[target_col].isna().sum()
    logger.info(f"  Missing values after: {missing_after}")

    return df


def handle_outliers(df: pd.DataFrame, target_col: str,
                    method: str = 'iqr', threshold: float = 1.5) -> pd.DataFrame:

    logger.info(f"Handling outliers using {method} method...")

    series = df[target_col].copy()

    if method == 'iqr':
        Q1 = series.quantile(0.25)
        Q3 = series.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - threshold * IQR
        upper_bound = Q3 + threshold * IQR
    elif method == 'zscore':
        mean = series.mean()
        std = series.std()
        lower_bound = mean - threshold * std
        upper_bound = mean + threshold * std
    else:
        raise ValueError(f"Unknown method: {method}")

    lower_bound = max(lower_bound, 0)
    upper_bound = min(upper_bound, 100)

    outliers_mask = (series < lower_bound) | (series > upper_bound)
    n_outliers = outliers_mask.sum()

    logger.info(f"  Found {n_outliers} outliers ({n_outliers / len(df) * 100:.2f}%)")
    logger.info(f"  Bounds: [{lower_bound:.1f}, {upper_bound:.1f}]")


    df[target_col] = series.clip(lower=lower_bound, upper=upper_bound)

    return df


def add_temporal_features(df: pd.DataFrame) -> pd.DataFrame:

    logger.info("Adding temporal features...")

    df = df.copy()


    df['hour'] = df.index.hour
    df['day_of_week'] = df.index.dayofweek
    df['day_of_month'] = df.index.day
    df['month'] = df.index.month
    df['day_of_year'] = df.index.dayofyear
    df['week_of_year'] = df.index.isocalendar().week.astype(int)
    df['year'] = df.index.year


    df['is_dry_season'] = df['month'].isin(DRY_SEASON_MONTHS).astype(int)
    df['is_wet_season'] = df['month'].isin(WET_SEASON_MONTHS).astype(int)


    df['season'] = df['month'].apply(
        lambda m: 'Dry' if m in DRY_SEASON_MONTHS else 'Wet'
    )

    df['time_of_day'] = pd.cut(
        df['hour'],
        bins=[-1, 5, 11, 17, 23],
        labels=['Night', 'Morning', 'Afternoon', 'Evening']
    )

    return df


def prepare_data(filepath: Path) -> Tuple[pd.DataFrame, pd.Series]:


    df = load_data(filepath)


    df = handle_missing_values(df, TARGET_COL)


    df = handle_outliers(df, TARGET_COL)


    df = add_temporal_features(df)


    df = df.dropna(subset=[TARGET_COL])


    target = df[TARGET_COL].copy()

    logger.info(f"Prepared data: {len(df)} samples")
    logger.info(f"Target stats: mean={target.mean():.2f}, std={target.std():.2f}")
    logger.info(f"Target range: [{target.min():.1f}, {target.max():.1f}]")

    return df, target



def plot_time_series_with_seasons(df: pd.DataFrame, target_col: str,
                                  province: str = "Province",
                                  save_path: Optional[Path] = None):

    fig, ax = plt.subplots(figsize=(16, 6))


    ax.plot(df.index, df[target_col], linewidth=0.5, alpha=0.7, label='Humidity')


    wet_mask = df['is_wet_season'] == 1
    ax.fill_between(df.index, df[target_col].min(), df[target_col].max(),
                    where=wet_mask, alpha=0.2, color='blue', label='Wet Season')

    ax.set_xlabel('Date')
    ax.set_ylabel('Relative Humidity (%)')
    ax.set_title(f'Relative Humidity Time Series - {province}\n(Blue shaded = Wet Season)')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"Saved: {save_path}")
    plt.close()


def plot_seasonal_decomposition(series: pd.Series, period: int = 24,
                                save_path: Optional[Path] = None):


    subset = series.tail(30 * 24)

    decomposition = seasonal_decompose(subset, model='additive', period=period)

    fig, axes = plt.subplots(4, 1, figsize=(14, 12))

    axes[0].plot(decomposition.observed, linewidth=0.8)
    axes[0].set_ylabel('Observed')
    axes[0].set_title('Seasonal Decomposition of Humidity (Last 30 Days)')

    axes[1].plot(decomposition.trend, linewidth=1, color='orange')
    axes[1].set_ylabel('Trend')

    axes[2].plot(decomposition.seasonal, linewidth=0.8, color='green')
    axes[2].set_ylabel('Seasonal')

    axes[3].plot(decomposition.resid, linewidth=0.5, color='red', alpha=0.7)
    axes[3].set_ylabel('Residual')
    axes[3].set_xlabel('Date')

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"Saved: {save_path}")
    plt.close()

    return decomposition


def test_stationarity(series: pd.Series) -> Dict[str, Any]:

    logger.info("Performing stationarity tests...")

    results = {}


    adf_result = adfuller(series.dropna(), autolag='AIC')
    results['adf'] = {
        'statistic': adf_result[0],
        'p_value': adf_result[1],
        'critical_values': adf_result[4],
        'is_stationary': adf_result[1] < 0.05
    }

    logger.info(f"  ADF Test: statistic={adf_result[0]:.4f}, p-value={adf_result[1]:.4f}")
    logger.info(f"    -> {'Stationary' if results['adf']['is_stationary'] else 'Non-stationary'}")


    try:
        kpss_result = kpss(series.dropna(), regression='c', nlags='auto')
        results['kpss'] = {
            'statistic': kpss_result[0],
            'p_value': kpss_result[1],
            'critical_values': kpss_result[3],
            'is_stationary': kpss_result[1] > 0.05
        }
        logger.info(f"  KPSS Test: statistic={kpss_result[0]:.4f}, p-value={kpss_result[1]:.4f}")
        logger.info(f"    -> {'Stationary' if results['kpss']['is_stationary'] else 'Non-stationary'}")
    except Exception as e:
        logger.warning(f"  KPSS Test failed: {e}")
        results['kpss'] = None

    return results


def plot_acf_pacf(series: pd.Series, lags: int = 72,
                  save_path: Optional[Path] = None):

    fig, axes = plt.subplots(2, 1, figsize=(14, 8))


    plot_acf(series.dropna(), lags=lags, ax=axes[0], alpha=0.05)
    axes[0].set_title('Autocorrelation Function (ACF)')
    axes[0].axvline(x=24, color='red', linestyle='--', alpha=0.5, label='24h lag')
    axes[0].axvline(x=48, color='red', linestyle='--', alpha=0.5)
    axes[0].legend()


    plot_pacf(series.dropna(), lags=lags, ax=axes[1], alpha=0.05, method='ywm')
    axes[1].set_title('Partial Autocorrelation Function (PACF)')
    axes[1].axvline(x=24, color='red', linestyle='--', alpha=0.5, label='24h lag')
    axes[1].legend()

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"Saved: {save_path}")
    plt.close()


def plot_hourly_pattern(df: pd.DataFrame, target_col: str,
                        save_path: Optional[Path] = None):

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))


    hourly_stats = df.groupby('hour')[target_col].agg(['mean', 'std'])
    axes[0].errorbar(hourly_stats.index, hourly_stats['mean'],
                     yerr=hourly_stats['std'], capsize=3, marker='o')
    axes[0].set_xlabel('Hour of Day')
    axes[0].set_ylabel('Relative Humidity (%)')
    axes[0].set_title('Hourly Humidity Pattern (Mean ± Std)')
    axes[0].set_xticks(range(0, 24, 2))
    axes[0].grid(True, alpha=0.3)


    for season in ['Dry', 'Wet']:
        season_data = df[df['season'] == season]
        hourly_mean = season_data.groupby('hour')[target_col].mean()
        axes[1].plot(hourly_mean.index, hourly_mean.values,
                     marker='o', label=f'{season} Season', linewidth=2)

    axes[1].set_xlabel('Hour of Day')
    axes[1].set_ylabel('Relative Humidity (%)')
    axes[1].set_title('Hourly Pattern by Season')
    axes[1].set_xticks(range(0, 24, 2))
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"Saved: {save_path}")
    plt.close()


def plot_monthly_pattern(df: pd.DataFrame, target_col: str,
                         save_path: Optional[Path] = None):

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))


    month_order = list(range(1, 13))
    df_plot = df.copy()
    df_plot['month'] = pd.Categorical(df_plot['month'], categories=month_order, ordered=True)

    monthly_data = [df[df['month'] == m][target_col].dropna().values for m in month_order]
    bp = axes[0].boxplot(monthly_data, patch_artist=True)


    colors = ['lightcoral' if m in DRY_SEASON_MONTHS else 'lightblue' for m in month_order]
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)

    axes[0].set_xticklabels(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                             'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])
    axes[0].set_xlabel('Month')
    axes[0].set_ylabel('Relative Humidity (%)')
    axes[0].set_title('Monthly Humidity Distribution\n(Red=Dry, Blue=Wet)')
    axes[0].grid(True, alpha=0.3, axis='y')


    season_data = [
        df[df['season'] == 'Dry'][target_col].dropna().values,
        df[df['season'] == 'Wet'][target_col].dropna().values
    ]
    bp2 = axes[1].boxplot(season_data, patch_artist=True)
    bp2['boxes'][0].set_facecolor('lightcoral')
    bp2['boxes'][1].set_facecolor('lightblue')
    axes[1].set_xticklabels(['Dry Season\n(Nov-Apr)', 'Wet Season\n(May-Oct)'])
    axes[1].set_ylabel('Relative Humidity (%)')
    axes[1].set_title('Humidity: Dry vs Wet Season')
    axes[1].grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"Saved: {save_path}")
    plt.close()


def run_eda(df: pd.DataFrame, target: pd.Series) -> Dict[str, Any]:

    logger.info("\n" + "=" * 60)
    logger.info("EXPLORATORY DATA ANALYSIS")
    logger.info("=" * 60)

    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    results = {}


    logger.info("\n[1] Time series visualization...")
    plot_time_series_with_seasons(
        df, TARGET_COL,
        save_path=PLOTS_DIR / "01_timeseries_seasonal.png"
    )


    logger.info("\n[2] Seasonal decomposition...")
    decomposition = plot_seasonal_decomposition(
        target, period=SEASONAL_PERIOD,
        save_path=PLOTS_DIR / "02_seasonal_decomposition.png"
    )


    logger.info("\n[3] Stationarity tests...")
    results['stationarity'] = test_stationarity(target)


    logger.info("\n[4] ACF/PACF analysis...")
    plot_acf_pacf(
        target, lags=72,
        save_path=PLOTS_DIR / "03_acf_pacf.png"
    )


    logger.info("\n[5] Hourly pattern analysis...")
    plot_hourly_pattern(
        df, TARGET_COL,
        save_path=PLOTS_DIR / "04_hourly_pattern.png"
    )


    logger.info("\n[6] Monthly/Seasonal pattern...")
    plot_monthly_pattern(
        df, TARGET_COL,
        save_path=PLOTS_DIR / "05_monthly_seasonal_pattern.png"
    )


    results['statistics'] = {
        'mean': float(target.mean()),
        'std': float(target.std()),
        'min': float(target.min()),
        'max': float(target.max()),
        'median': float(target.median()),
        'skewness': float(target.skew()),
        'kurtosis': float(target.kurtosis())
    }


    dry_humidity = df[df['season'] == 'Dry'][TARGET_COL]
    wet_humidity = df[df['season'] == 'Wet'][TARGET_COL]

    results['seasonal_stats'] = {
        'dry_season': {
            'mean': float(dry_humidity.mean()),
            'std': float(dry_humidity.std())
        },
        'wet_season': {
            'mean': float(wet_humidity.mean()),
            'std': float(wet_humidity.std())
        }
    }

    logger.info(f"\nDry Season: mean={dry_humidity.mean():.2f}%, std={dry_humidity.std():.2f}")
    logger.info(f"Wet Season: mean={wet_humidity.mean():.2f}%, std={wet_humidity.std():.2f}")

    return results




def train_test_split_temporal(
        series: pd.Series,
        validation_days: int = VALIDATION_DAYS,
        test_days: int = TEST_DAYS
) -> Tuple[pd.Series, pd.Series, pd.Series]:

    test_size = test_days * 24
    val_size = validation_days * 24

    train = series[:-test_size - val_size]
    validation = series[-test_size - val_size:-test_size]
    test = series[-test_size:]

    logger.info(f"Train set: {len(train)} samples ({len(train) // 24} days)")
    logger.info(f"Validation set: {len(validation)} samples ({len(validation) // 24} days)")
    logger.info(f"Test set: {len(test)} samples ({len(test) // 24} days)")

    return train, validation, test


def calculate_mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:

    y_true, y_pred = np.array(y_true), np.array(y_pred)

    mask = y_true != 0
    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100


def calculate_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:

    mape = calculate_mape(y_true, y_pred)
    return max(0, 100 - mape)


def fit_sarima(train: pd.Series, order: Tuple, seasonal_order: Tuple,
               enforce_stationarity: bool = False,
               enforce_invertibility: bool = False) -> Any:

    model = SARIMAX(
        train,
        order=order,
        seasonal_order=seasonal_order,
        enforce_stationarity=enforce_stationarity,
        enforce_invertibility=enforce_invertibility,
        initialization='approximate_diffuse'
    )

    results = model.fit(disp=False, maxiter=200, method='lbfgs')
    return results


def grid_search_sarima(
        train: pd.Series,
        validation: pd.Series,
        param_grid: Dict,
        max_iterations: int = MAX_GRID_SEARCH_ITER
) -> Tuple[Tuple, Tuple, Dict]:

    logger.info("\n" + "=" * 60)
    logger.info("GRID SEARCH FOR SARIMA PARAMETERS")
    logger.info("=" * 60)

    results = []
    best_mape = float('inf')
    best_order = None
    best_seasonal_order = None


    from itertools import product

    param_combinations = list(product(
        param_grid['p'], param_grid['d'], param_grid['q'],
        param_grid['P'], param_grid['D'], param_grid['Q'], param_grid['s']
    ))


    if len(param_combinations) > max_iterations:
        np.random.seed(42)
        indices = np.random.choice(len(param_combinations), max_iterations, replace=False)
        param_combinations = [param_combinations[i] for i in sorted(indices)]

    logger.info(f"Testing {len(param_combinations)} parameter combinations...")

    for i, (p, d, q, P, D, Q, s) in enumerate(param_combinations, 1):
        order = (p, d, q)
        seasonal_order = (P, D, Q, s)

        try:

            model_fit = fit_sarima(train, order, seasonal_order)


            forecast = model_fit.get_forecast(steps=len(validation))
            y_pred = forecast.predicted_mean


            mape = calculate_mape(validation.values, y_pred.values)
            mae = mean_absolute_error(validation.values, y_pred.values)
            rmse = np.sqrt(mean_squared_error(validation.values, y_pred.values))
            aic = model_fit.aic

            result = {
                'order': order,
                'seasonal_order': seasonal_order,
                'mape': mape,
                'mae': mae,
                'rmse': rmse,
                'aic': aic
            }
            results.append(result)

            if mape < best_mape:
                best_mape = mape
                best_order = order
                best_seasonal_order = seasonal_order
                logger.info(f"  [{i}/{len(param_combinations)}] NEW BEST: "
                            f"order={order}, seasonal={seasonal_order}, "
                            f"MAPE={mape:.2f}%, AIC={aic:.1f}")

        except Exception as e:
            logger.debug(f"  [{i}/{len(param_combinations)}] Failed: order={order}, "
                         f"seasonal={seasonal_order} - {str(e)[:50]}")
            continue

    if best_order is None:
        raise RuntimeError("All SARIMA configurations failed!")

    logger.info(f"\nBest parameters found:")
    logger.info(f"  Order (p,d,q): {best_order}")
    logger.info(f"  Seasonal order (P,D,Q,s): {best_seasonal_order}")
    logger.info(f"  Validation MAPE: {best_mape:.2f}%")
    logger.info(f"  Validation Accuracy: {100 - best_mape:.2f}%")

    return best_order, best_seasonal_order, {
        'all_results': results,
        'best_mape': best_mape,
        'n_tested': len(results)
    }


def train_final_model(train: pd.Series, validation: pd.Series,
                      order: Tuple, seasonal_order: Tuple) -> Any:

    logger.info("\nTraining final model on train + validation data...")


    full_train = pd.concat([train, validation])

    logger.info(f"Training on {len(full_train)} samples ({len(full_train) // 24} days)")


    model_fit = fit_sarima(full_train, order, seasonal_order)

    logger.info(f"Final model AIC: {model_fit.aic:.2f}")
    logger.info(f"Final model BIC: {model_fit.bic:.2f}")

    return model_fit




def evaluate_model(model_fit: Any, test: pd.Series,
                   forecast_horizon: int = FORECAST_HORIZON) -> Dict[str, float]:

    logger.info("\n" + "=" * 60)
    logger.info("MODEL EVALUATION ON TEST SET")
    logger.info("=" * 60)


    forecast = model_fit.get_forecast(steps=len(test))
    y_pred = forecast.predicted_mean
    conf_int = forecast.conf_int(alpha=0.05)


    y_true = test.values
    y_hat = y_pred.values


    y_hat = np.clip(y_hat, 0, 100)

    metrics = {
        'mae': mean_absolute_error(y_true, y_hat),
        'rmse': np.sqrt(mean_squared_error(y_true, y_hat)),
        'mape': calculate_mape(y_true, y_hat),
        'r2': r2_score(y_true, y_hat),
        'accuracy': calculate_accuracy(y_true, y_hat)
    }

    logger.info(f"Test Set Performance:")
    logger.info(f"  MAE:      {metrics['mae']:.2f}%")
    logger.info(f"  RMSE:     {metrics['rmse']:.2f}%")
    logger.info(f"  MAPE:     {metrics['mape']:.2f}%")
    logger.info(f"  R²:       {metrics['r2']:.4f}")
    logger.info(f"  Accuracy: {metrics['accuracy']:.2f}%")

    return metrics, y_pred, conf_int


def plot_forecast_vs_actual(test: pd.Series, y_pred: pd.Series,
                            conf_int: pd.DataFrame,
                            save_path: Optional[Path] = None):

    fig, ax = plt.subplots(figsize=(14, 6))


    ax.plot(test.index, test.values, 'b-', linewidth=1.5, label='Actual', marker='o', markersize=3)


    ax.plot(test.index, y_pred.values, 'r--', linewidth=1.5, label='Forecast', marker='s', markersize=3)


    ax.fill_between(test.index,
                    conf_int.iloc[:, 0].values,
                    conf_int.iloc[:, 1].values,
                    color='red', alpha=0.2, label='95% CI')

    ax.set_xlabel('Date')
    ax.set_ylabel('Relative Humidity (%)')
    ax.set_title(f'Humidity Forecast vs Actual (Test Period: {TEST_DAYS} days)')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)


    plt.xticks(rotation=45)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"Saved: {save_path}")
    plt.close()


def plot_residual_analysis(test: pd.Series, y_pred: pd.Series,
                           save_path: Optional[Path] = None):

    residuals = test.values - y_pred.values

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))


    axes[0, 0].plot(test.index, residuals, linewidth=0.8)
    axes[0, 0].axhline(y=0, color='r', linestyle='--')
    axes[0, 0].set_xlabel('Date')
    axes[0, 0].set_ylabel('Residual (%)')
    axes[0, 0].set_title('Residuals Over Time')
    axes[0, 0].tick_params(axis='x', rotation=45)


    axes[0, 1].hist(residuals, bins=30, edgecolor='black', alpha=0.7)
    axes[0, 1].axvline(x=0, color='r', linestyle='--')
    axes[0, 1].axvline(x=residuals.mean(), color='g', linestyle='--', label=f'Mean: {residuals.mean():.2f}')
    axes[0, 1].set_xlabel('Residual (%)')
    axes[0, 1].set_ylabel('Frequency')
    axes[0, 1].set_title('Residual Distribution')
    axes[0, 1].legend()


    stats.probplot(residuals, dist="norm", plot=axes[1, 0])
    axes[1, 0].set_title('Q-Q Plot')


    plot_acf(residuals, lags=48, ax=axes[1, 1], alpha=0.05)
    axes[1, 1].set_title('ACF of Residuals')

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"Saved: {save_path}")
    plt.close()


    lb_test = acorr_ljungbox(residuals, lags=[24, 48], return_df=True)
    logger.info(f"\nLjung-Box Test for Residuals:")
    logger.info(f"  Lag 24: statistic={lb_test['lb_stat'].iloc[0]:.2f}, p-value={lb_test['lb_pvalue'].iloc[0]:.4f}")
    logger.info(f"  Lag 48: statistic={lb_test['lb_stat'].iloc[1]:.2f}, p-value={lb_test['lb_pvalue'].iloc[1]:.4f}")


def plot_error_distribution(test: pd.Series, y_pred: pd.Series,
                            save_path: Optional[Path] = None):

    errors = np.abs(test.values - y_pred.values)
    pct_errors = errors / test.values * 100

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))


    axes[0].hist(errors, bins=30, edgecolor='black', alpha=0.7, color='steelblue')
    axes[0].axvline(x=errors.mean(), color='r', linestyle='--',
                    label=f'Mean: {errors.mean():.2f}%')
    axes[0].axvline(x=np.percentile(errors, 90), color='orange', linestyle='--',
                    label=f'90th Pctl: {np.percentile(errors, 90):.2f}%')
    axes[0].set_xlabel('Absolute Error (%)')
    axes[0].set_ylabel('Frequency')
    axes[0].set_title('Absolute Error Distribution')
    axes[0].legend()


    test_df = pd.DataFrame({'error': errors, 'hour': test.index.hour})
    hourly_error = test_df.groupby('hour')['error'].mean()
    axes[1].bar(hourly_error.index, hourly_error.values, color='steelblue', alpha=0.7)
    axes[1].axhline(y=errors.mean(), color='r', linestyle='--', label=f'Mean: {errors.mean():.2f}%')
    axes[1].set_xlabel('Hour of Day')
    axes[1].set_ylabel('Mean Absolute Error (%)')
    axes[1].set_title('Error by Hour of Day')
    axes[1].set_xticks(range(0, 24, 2))
    axes[1].legend()

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"Saved: {save_path}")
    plt.close()




def save_model_artifacts(
        model_fit: Any,
        order: Tuple,
        seasonal_order: Tuple,
        metrics: Dict[str, float],
        eda_results: Dict[str, Any],
        grid_search_results: Dict[str, Any],
        training_info: Dict[str, Any],
        province: str
):

    logger.info("\n" + "=" * 60)
    logger.info("SAVING MODEL ARTIFACTS")
    logger.info("=" * 60)

    province_dir = ARTIFACTS_DIR / province
    province_dir.mkdir(parents=True, exist_ok=True)
    plots_dir = province_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)


    model_path = province_dir / f"{province}_humidity_sarima.pkl"


    lightweight_model = {
        'params': model_fit.params.tolist(),
        'order': order,
        'seasonal_order': seasonal_order,
        'nobs': model_fit.nobs,
        'loglikelihood': float(model_fit.llf),
        'aic': float(model_fit.aic),
        'bic': float(model_fit.bic),

        'specification': {
            'k_ar': model_fit.specification.k_ar,
            'k_diff': model_fit.specification.k_diff,
            'k_ma': model_fit.specification.k_ma,
            'k_seasonal_ar': model_fit.specification.k_seasonal_ar,
            'k_seasonal_diff': model_fit.specification.k_seasonal_diff,
            'k_seasonal_ma': model_fit.specification.k_seasonal_ma,
            'seasonal_periods': model_fit.specification.seasonal_periods,
        },

        'forecast_state': {
            'predicted_state': model_fit.predicted_state[:, -1].tolist() if hasattr(model_fit,
                                                                                    'predicted_state') else None,
            'predicted_state_cov': model_fit.predicted_state_cov[:, :, -1].tolist() if hasattr(model_fit,
                                                                                               'predicted_state_cov') else None,
        }
    }

    with open(model_path, 'wb') as f:
        pickle.dump(lightweight_model, f, protocol=pickle.HIGHEST_PROTOCOL)


    file_size_mb = model_path.stat().st_size / (1024 * 1024)
    logger.info(f"Saved lightweight model: {model_path} ({file_size_mb:.2f} MB)")


    params_path = province_dir / f"{province}_best_params.json"
    params = {
        'order': list(order),
        'seasonal_order': list(seasonal_order),
        'p': order[0],
        'd': order[1],
        'q': order[2],
        'P': seasonal_order[0],
        'D': seasonal_order[1],
        'Q': seasonal_order[2],
        's': seasonal_order[3]
    }
    with open(params_path, 'w', encoding='utf-8') as f:
        json.dump(params, f, indent=2)
    logger.info(f"Saved parameters: {params_path}")


    metadata_path = province_dir / f"{province}_metadata.json"
    metadata = {
        'province': province,
        'target_column': TARGET_COL,
        'model_type': 'SARIMA',
        'order': list(order),
        'seasonal_order': list(seasonal_order),
        'seasonal_period': SEASONAL_PERIOD,
        'forecast_horizon': FORECAST_HORIZON,
        'performance_metrics': {
            k: round(v, 4) if isinstance(v, float) else v
            for k, v in metrics.items()
        },
        'training_info': training_info,
        'eda_summary': {
            'statistics': eda_results.get('statistics', {}),
            'seasonal_stats': eda_results.get('seasonal_stats', {}),
            'stationarity': {
                'adf_stationary': eda_results.get('stationarity', {}).get('adf', {}).get('is_stationary', None),
                'kpss_stationary': eda_results.get('stationarity', {}).get('kpss', {}).get('is_stationary',
                                                                                           None) if eda_results.get(
                    'stationarity', {}).get('kpss') else None
            }
        },
        'grid_search_summary': {
            'best_mape': grid_search_results.get('best_mape', None),
            'n_configurations_tested': grid_search_results.get('n_tested', None)
        },
        'created_at': datetime.now().isoformat(),
        'model_file_size_mb': round(file_size_mb, 2)
    }

    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
    logger.info(f"Saved metadata: {metadata_path}")


    summary_path = province_dir / f"{province}_model_summary.txt"
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(str(model_fit.summary()))
    logger.info(f"Saved model summary: {summary_path}")

    logger.info(f"\nAll artifacts saved to: {province_dir}")



def train_province(province: str, skip_eda_plots: bool = False) -> Optional[Dict[str, Any]]:

    province_start_time = datetime.now()

    logger.info("\n" + "#" * 60)
    logger.info(f"# TRAINING: {province}")
    logger.info("#" * 60)


    province_plots_dir = ARTIFACTS_DIR / province / "plots"
    province_plots_dir.mkdir(parents=True, exist_ok=True)


    logger.info("\n[STEP 1] DATA PREPARATION")
    logger.info("-" * 40)

    data_file = DATA_DIR / f"{province}.csv"
    if not data_file.exists():
        logger.error(f"Data file not found: {data_file}")
        return None

    try:
        df, target = prepare_data(data_file)
    except Exception as e:
        logger.error(f"Failed to prepare data for {province}: {e}")
        return None


    logger.info("\n[STEP 2] EXPLORATORY DATA ANALYSIS")
    logger.info("-" * 40)


    global PLOTS_DIR
    original_plots_dir = PLOTS_DIR
    PLOTS_DIR = province_plots_dir

    try:
        eda_results = run_eda(df, target)
    except Exception as e:
        logger.warning(f"EDA failed for {province}: {e}")
        eda_results = {'statistics': {}, 'seasonal_stats': {}, 'stationarity': {}}
    finally:
        PLOTS_DIR = original_plots_dir


    logger.info("\n[STEP 3] DATA SPLITTING")
    logger.info("-" * 40)

    train, validation, test = train_test_split_temporal(target)


    logger.info("\n[STEP 4] HYPERPARAMETER TUNING")
    logger.info("-" * 40)

    try:
        best_order, best_seasonal_order, grid_results = grid_search_sarima(
            train, validation, SARIMA_PARAM_GRID
        )
    except Exception as e:
        logger.error(f"Grid search failed for {province}: {e}")
        return None


    logger.info("\n[STEP 5] FINAL MODEL TRAINING")
    logger.info("-" * 40)

    try:
        final_model = train_final_model(train, validation, best_order, best_seasonal_order)
    except Exception as e:
        logger.error(f"Final model training failed for {province}: {e}")
        return None


    logger.info("\n[STEP 6] MODEL EVALUATION")
    logger.info("-" * 40)

    try:
        metrics, y_pred, conf_int = evaluate_model(final_model, test)
    except Exception as e:
        logger.error(f"Model evaluation failed for {province}: {e}")
        return None


    try:
        plot_forecast_vs_actual(
            test, y_pred, conf_int,
            save_path=province_plots_dir / "06_forecast_vs_actual.png"
        )

        plot_residual_analysis(
            test, y_pred,
            save_path=province_plots_dir / "07_residual_analysis.png"
        )

        plot_error_distribution(
            test, y_pred,
            save_path=province_plots_dir / "08_error_distribution.png"
        )
    except Exception as e:
        logger.warning(f"Failed to save some plots for {province}: {e}")


    logger.info("\n[STEP 7] SAVING ARTIFACTS")
    logger.info("-" * 40)

    training_duration = datetime.now() - province_start_time

    training_info = {
        'province': province,
        'data_file': str(data_file),
        'training_samples': len(train),
        'validation_samples': len(validation),
        'test_samples': len(test),
        'training_period': f"{train.index.min()} to {train.index.max()}",
        'validation_period': f"{validation.index.min()} to {validation.index.max()}",
        'test_period': f"{test.index.min()} to {test.index.max()}",
        'training_duration': str(training_duration)
    }

    try:
        save_model_artifacts(
            final_model,
            best_order,
            best_seasonal_order,
            metrics,
            eda_results,
            grid_results,
            training_info,
            province
        )
    except Exception as e:
        logger.error(f"Failed to save artifacts for {province}: {e}")
        return None


    result = {
        'province': province,
        'order': best_order,
        'seasonal_order': best_seasonal_order,
        'metrics': metrics,
        'duration': training_duration,
        'status': 'SUCCESS'
    }

    logger.info(f"\n✓ {province} completed: SARIMA{best_order}x{best_seasonal_order}")
    logger.info(f"  Accuracy: {metrics['accuracy']:.2f}% | MAPE: {metrics['mape']:.2f}%")
    logger.info(f"  Duration: {training_duration}")

    return result

def main():

    parser = argparse.ArgumentParser(
        description="Train SARIMA model for humidity forecasting (34 provinces of Vietnam)"
    )
    parser.add_argument(
        '--province', type=str, default=None,
        help='Province name (e.g., An_Giang). If not specified, trains all provinces.'
    )
    parser.add_argument(
        '--all', action='store_true',
        help='Train all 34 provinces'
    )
    parser.add_argument(
        '--forecast-horizon', type=int, default=FORECAST_HORIZON,
        help=f'Forecast horizon in hours (default: {FORECAST_HORIZON})'
    )
    parser.add_argument(
        '--list-provinces', action='store_true',
        help='List all available provinces and exit'
    )

    args = parser.parse_args()


    if args.list_provinces:
        provinces = get_all_provinces()
        print(f"\nAvailable provinces ({len(provinces)}):")
        for i, p in enumerate(provinces, 1):
            print(f"  {i:2d}. {p}")
        return


    if args.province:
        provinces_to_train = [args.province]
    else:

        provinces_to_train = get_all_provinces()

    total_start_time = datetime.now()

    logger.info("=" * 70)
    logger.info("SARIMA HUMIDITY FORECASTING - BATCH TRAINING PIPELINE")
    logger.info("=" * 70)
    logger.info(f"Provinces to train: {len(provinces_to_train)}")
    logger.info(f"Target: {TARGET_COL}")
    logger.info(f"Forecast Horizon: {args.forecast_horizon} hours")
    logger.info(f"Seasonal Period: {SEASONAL_PERIOD}")
    logger.info(f"Max Grid Search Iterations: {MAX_GRID_SEARCH_ITER}")
    logger.info("=" * 70)

    if len(provinces_to_train) > 1:
        logger.info("\nProvinces to train:")
        for i, p in enumerate(provinces_to_train, 1):
            logger.info(f"  {i:2d}. {p}")


    results = []
    successful = []
    failed = []


    for idx, province in enumerate(provinces_to_train, 1):
        logger.info(f"\n{'=' * 70}")
        logger.info(f"[{idx}/{len(provinces_to_train)}] Starting: {province}")
        logger.info(f"{'=' * 70}")

        result = train_province(province, skip_eda_plots=(len(provinces_to_train) > 5))

        if result:
            results.append(result)
            successful.append(province)
        else:
            failed.append(province)


        elapsed = datetime.now() - total_start_time
        avg_time = elapsed / idx
        remaining = avg_time * (len(provinces_to_train) - idx)

        logger.info(f"\n📊 Progress: {idx}/{len(provinces_to_train)} provinces")
        logger.info(f"   Elapsed: {elapsed} | Estimated remaining: {remaining}")


    total_duration = datetime.now() - total_start_time

    logger.info("\n" + "=" * 70)
    logger.info("BATCH TRAINING COMPLETE - FINAL SUMMARY")
    logger.info("=" * 70)

    logger.info(f"\nTotal provinces: {len(provinces_to_train)}")
    logger.info(f"Successful: {len(successful)}")
    logger.info(f"Failed: {len(failed)}")
    logger.info(f"Total duration: {total_duration}")

    if results:
        logger.info("\n" + "-" * 70)
        logger.info("RESULTS BY PROVINCE:")
        logger.info("-" * 70)
        logger.info(f"{'Province':<20} {'Order':<15} {'Seasonal':<20} {'MAPE':<10} {'Accuracy':<10}")
        logger.info("-" * 70)

        for r in sorted(results, key=lambda x: x['metrics']['accuracy'], reverse=True):
            logger.info(
                f"{r['province']:<20} "
                f"{str(r['order']):<15} "
                f"{str(r['seasonal_order']):<20} "
                f"{r['metrics']['mape']:.2f}%{' ':<5}"
                f"{r['metrics']['accuracy']:.2f}%"
            )


        accuracies = [r['metrics']['accuracy'] for r in results]
        mapes = [r['metrics']['mape'] for r in results]

        logger.info("\n" + "-" * 70)
        logger.info("OVERALL STATISTICS:")
        logger.info("-" * 70)
        logger.info(f"Average Accuracy: {np.mean(accuracies):.2f}%")
        logger.info(f"Min Accuracy: {np.min(accuracies):.2f}%")
        logger.info(f"Max Accuracy: {np.max(accuracies):.2f}%")
        logger.info(f"Average MAPE: {np.mean(mapes):.2f}%")


        target_met = sum(1 for a in accuracies if a >= 90)
        logger.info(f"\nProvinces with ≥90% accuracy: {target_met}/{len(results)}")

    if failed:
        logger.info("\n⚠️  Failed provinces:")
        for p in failed:
            logger.info(f"  - {p}")


    summary_path = ARTIFACTS_DIR / "training_summary.json"
    summary = {
        'total_provinces': len(provinces_to_train),
        'successful': len(successful),
        'failed': len(failed),
        'failed_list': failed,
        'total_duration': str(total_duration),
        'created_at': datetime.now().isoformat(),
        'results': [
            {
                'province': r['province'],
                'order': r['order'],
                'seasonal_order': r['seasonal_order'],
                'mape': r['metrics']['mape'],
                'accuracy': r['metrics']['accuracy'],
                'mae': r['metrics']['mae'],
                'rmse': r['metrics']['rmse'],
                'r2': r['metrics']['r2'],
                'duration': str(r['duration'])
            }
            for r in results
        ]
    }

    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    logger.info(f"\nSummary saved to: {summary_path}")

    logger.info("\n" + "=" * 70)
    logger.info(f"All artifacts saved to: {ARTIFACTS_DIR}")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
