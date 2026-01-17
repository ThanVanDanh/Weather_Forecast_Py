import os
import json
import time
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.statespace.sarimax import SARIMAX
import warnings

warnings.filterwarnings("ignore")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models_sarimax_future"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

TARGET_COLUMN = 'shortwave_radiation'

EXOG_COLUMNS = [
    'cloudcover',
    'temperature_2m',
    'relative_humidity_2m',
    'wind_speed_10m',
    'precipitation',
    'rain'
]

DEFAULT_ORDER = (1, 1, 1)
DEFAULT_SEASONAL_ORDER = (1, 0, 1, 24)

WET_MONTHS = {5, 6, 7, 8, 9, 10}

PROVINCE_COORDINATES = {
    "Tuyen_Quang": (21.82356, 105.21424),
    "Lao_Cai": (21.72000, 104.91000),
    "Thai_Nguyen": (21.59000, 105.85000),
    "Phu_Tho": (21.32000, 105.40000),
    "Bac_Ninh": (21.27000, 106.20000),
    "Hung_Yen": (20.64637, 106.05112),
    "Hai_Phong": (20.86000, 106.68000),
    "Ninh_Binh": (20.25809, 105.97965),
    "Quang_Tri": (17.46594, 106.59840),
    "Da_Nang": (16.07000, 108.22000),
    "Quang_Ngai": (15.12047, 108.79232),
    "Gia_Lai": (13.78297, 109.21966),
    "Khanh_Hoa": (12.24510, 109.19400),
    "Lam_Dong": (11.95000, 108.44000),
    "Dak_Lak": (12.67000, 108.04000),
    "TP_Ho_Chi_Minh": (10.82000, 106.63000),
    "Dong_Nai": (10.94000, 106.82000),
    "Tay_Ninh": (10.54000, 106.41000),
    "Can_Tho": (10.04000, 105.79000),
    "Vinh_Long": (10.25000, 105.97000),
    "Dong_Thap": (10.36000, 106.36000),
    "Ca_Mau": (9.18000, 105.15000),
    "An_Giang": (10.01000, 105.08000),
    "Ha_Noi": (21.02000, 105.84000),
    "Hue": (16.46000, 107.60000),
    "Lai_Chau": (22.39922, 103.44532),
    "Dien_Bien": (21.38602, 103.02301),
    "Son_La": (21.32725, 103.90918),
    "Lang_Son": (21.85000, 106.76000),
    "Quang_Ninh": (20.95050, 107.07300),
    "Thanh_Hoa": (19.80669, 105.78518),
    "Nghe_An": (18.67958, 105.68133),
    "Ha_Tinh": (18.35595, 105.88775),
    "Cao_Bang": (22.66556, 106.26067),
}


def calculate_solar_elevation(times, lat, lon):
    """Tinh goc cao mat troi."""
    lat_rad = np.radians(lat)
    doy = times.dt.dayofyear
    declination = np.radians(23.45 * np.sin(np.radians(360 / 365 * (doy - 81))))
    time_correction = 4 * (lon - 105)
    solar_time = times.dt.hour + times.dt.minute / 60 + time_correction / 60
    hour_angle = np.radians(15 * (solar_time - 12))

    sin_elevation = np.sin(lat_rad) * np.sin(declination) + \
                    np.cos(lat_rad) * np.cos(declination) * np.cos(hour_angle)
    elevation = np.degrees(np.arcsin(np.clip(sin_elevation, -1, 1)))
    return elevation


def create_features(df, province_name):
    """Tao features cho SARIMAX."""
    df = df.copy()
    time_col = df.columns[0]
    df[time_col] = pd.to_datetime(df[time_col])
    df = df.sort_values(by=time_col).reset_index(drop=True)

    # Temporal features
    df['hour'] = df[time_col].dt.hour
    df['month'] = df[time_col].dt.month
    df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
    df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
    df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
    df['wet_season'] = df['month'].isin(WET_MONTHS).astype(np.float32)

    # Solar elevation
    if province_name in PROVINCE_COORDINATES:
        lat, lon = PROVINCE_COORDINATES[province_name]
        df['solar_elevation'] = calculate_solar_elevation(df[time_col], lat, lon)
    else:
        df['solar_elevation'] = 0.0

    return df


def get_exog_columns(df):
    """Lay danh sach cac cot exog co san."""
    base_exog = [col for col in EXOG_COLUMNS if col in df.columns]
    extra_features = ['hour_sin', 'hour_cos', 'month_sin', 'month_cos',
                      'wet_season', 'solar_elevation']
    available_extra = [col for col in extra_features if col in df.columns]
    return base_exog + available_extra


def evaluate_model(y_true, y_pred, solar_elevation=None):
    """Tinh cac metrics danh gia."""
    if solar_elevation is not None:
        daylight_mask = (solar_elevation > 5) & (y_true > 10)
    else:
        daylight_mask = y_true > 10

    metrics = {}

    mae_all = np.mean(np.abs(y_true - y_pred))
    rmse_all = np.sqrt(np.mean((y_true - y_pred) ** 2))
    metrics['mae_all'] = float(mae_all)
    metrics['rmse_all'] = float(rmse_all)

    # Daylight hours only
    if daylight_mask.sum() > 10:
        y_true_day = y_true[daylight_mask]
        y_pred_day = y_pred[daylight_mask]

        mae_day = np.mean(np.abs(y_true_day - y_pred_day))
        rmse_day = np.sqrt(np.mean((y_true_day - y_pred_day) ** 2))

        valid_mask = y_true_day > 10
        if valid_mask.sum() > 0:
            mape_day = np.mean(np.abs((y_true_day[valid_mask] - y_pred_day[valid_mask]) /
                                      y_true_day[valid_mask])) * 100
        else:
            mape_day = 0

        metrics['mae_daylight'] = float(mae_day)
        metrics['rmse_daylight'] = float(rmse_day)
        metrics['mape_daylight'] = float(mape_day)
        metrics['accuracy_daylight'] = float(100 - mape_day)
        metrics['n_daylight_samples'] = int(daylight_mask.sum())

    return metrics


def train_province(province_name, months=6):
    """Train SARIMAX cho mot tinh."""

    data_file = DATA_DIR / f"{province_name}.csv"
    if not data_file.exists():
        return f"[X] {province_name}: File khong ton tai"

    print(f"\n{'=' * 60}")
    print(f"Training SARIMAX: {province_name}")
    print(f"{'=' * 60}")

    try:
        # 1. Load va xu ly du lieu
        df = pd.read_csv(data_file)

        if TARGET_COLUMN not in df.columns:
            return f"[X] {province_name}: Thieu cot {TARGET_COLUMN}"

        df = create_features(df, province_name)
        time_col = df.columns[0]

        # Chi dung n thang gan nhat
        if months > 0:
            cutoff = df[time_col].max() - pd.Timedelta(days=months * 30)
            df = df[df[time_col] >= cutoff].reset_index(drop=True)
            print(f"Su dung {months} thang gan nhat: {len(df)} samples")

        df = df.ffill().bfill()
        exog_cols = get_exog_columns(df)
        print(f"Exog features: {len(exog_cols)}")

        # 2. Chuan bi du lieu
        y = df[TARGET_COLUMN].values.astype('float32')
        X_exog = df[exog_cols].values.astype('float32')
        solar_elevation = df['solar_elevation'].values if 'solar_elevation' in df.columns else None

        # Train/Test split (90/10)
        train_size = int(len(y) * 0.9)
        y_train, y_test = y[:train_size], y[train_size:]
        X_train, X_test = X_exog[:train_size], X_exog[train_size:]
        solar_elev_test = solar_elevation[train_size:] if solar_elevation is not None else None

        print(f"Train: {len(y_train)}, Test: {len(y_test)}")

        # 3. Scale exogenous variables
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # 4. Train SARIMAX
        print(f"Training SARIMAX: order={DEFAULT_ORDER}, seasonal={DEFAULT_SEASONAL_ORDER}")

        start_time = time.time()

        model = SARIMAX(
            y_train,
            exog=X_train_scaled,
            order=DEFAULT_ORDER,
            seasonal_order=DEFAULT_SEASONAL_ORDER,
            enforce_stationarity=False,
            enforce_invertibility=False
        )

        fitted_model = model.fit(disp=False, maxiter=200, method='lbfgs')

        train_time = time.time() - start_time
        print(f"Training time: {train_time:.1f}s")

        # 5. Evaluate tren test set
        y_pred = fitted_model.get_forecast(
            steps=len(y_test),
            exog=X_test_scaled
        ).predicted_mean

        y_pred = np.array(y_pred)
        y_pred = np.maximum(y_pred, 0)
        y_pred = np.minimum(y_pred, 1200)

        if solar_elev_test is not None:
            night_mask = solar_elev_test <= 0
            y_pred[night_mask] = 0

        metrics = evaluate_model(y_test, y_pred, solar_elev_test)

        print(f"\nTEST RESULTS:")
        print(f"   MAE (all):      {metrics['mae_all']:.2f} W/m2")
        print(f"   RMSE (all):     {metrics['rmse_all']:.2f} W/m2")
        if 'mae_daylight' in metrics:
            print(f"   MAE (daylight): {metrics['mae_daylight']:.2f} W/m2")
            print(f"   MAPE (daylight): {metrics['mape_daylight']:.2f}%")
            print(f"   ACCURACY:       {metrics['accuracy_daylight']:.2f}%")

        # 6. Luu model va artifacts
        model_file = MODEL_DIR / f"{province_name}_model.pkl"
        scaler_file = MODEL_DIR / f"{province_name}_scaler.pkl"
        metadata_file = MODEL_DIR / f"{province_name}_metadata.json"

        # Xoa du lieu training, residuals
        fitted_model.remove_data()
        # Dung joblib voi nen gzip de giam dung luong (compress=3)
        joblib.dump(fitted_model, model_file, compress=3)
        joblib.dump(scaler, scaler_file, compress=3)

        metadata = {
            'province': province_name,
            'order': DEFAULT_ORDER,
            'seasonal_order': DEFAULT_SEASONAL_ORDER,
            'exog_cols': exog_cols,
            'metrics': metrics,
            'train_samples': len(y_train),
            'test_samples': len(y_test),
            'training_time': train_time,
            'coordinates': PROVINCE_COORDINATES.get(province_name, (0, 0)),
            'data_range': {
                'start': str(df[time_col].min()),
                'end': str(df[time_col].max())
            }
        }

        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        accuracy = metrics.get('accuracy_daylight', 0)
        status = "[OK]" if accuracy >= 70 else "[!!]"

        print(f"\nSaved: {model_file.name}")

        return f"{status} {province_name}: Accuracy={accuracy:.2f}%"

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"[X] {province_name}: {str(e)}"


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Train SARIMAX voi Future Exogenous")
    parser.add_argument("--province", type=str, default=None, help="Ten tinh")
    parser.add_argument("--months", type=int, default=6, help="So thang du lieu")
    parser.add_argument("--all", action="store_true", help="Train tat ca cac tinh")

    args = parser.parse_args()

    if args.all:
        files = list(DATA_DIR.glob("*.csv"))
        print(f"Training SARIMAX cho {len(files)} tinh...")

        results = []
        for f in files:
            result = train_province(f.stem, args.months)
            results.append(result)
            print(result)

        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        for r in results:
            print(r)

    elif args.province:
        result = train_province(args.province, args.months)
        print(result)

    else:
        result = train_province("An_Giang", args.months)
        print(result)


if __name__ == "__main__":
    main()
