
import json
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from statsmodels.tsa.statespace.sarimax import SARIMAX
import warnings
warnings.filterwarnings("ignore")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models_sarimax_future_exog"
FUTURE_DATA_DIR = BASE_DIR / "data_future"
RESULT_DIR = BASE_DIR / "predictions_sarimax_24h"
RESULT_DIR.mkdir(parents=True, exist_ok=True)

TARGET_COLUMN = 'shortwave_radiation'
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
    df = df.copy()
    time_col = df.columns[0]
    if not np.issubdtype(df[time_col].dtype, np.datetime64):
        df[time_col] = pd.to_datetime(df[time_col])

    df = df.sort_values(by=time_col).reset_index(drop=True)

    df['hour'] = df[time_col].dt.hour
    df['month'] = df[time_col].dt.month
    df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
    df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
    df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
    df['wet_season'] = df['month'].isin(WET_MONTHS).astype(np.float32)

    if province_name in PROVINCE_COORDINATES:
        lat, lon = PROVINCE_COORDINATES[province_name]
        df['solar_elevation'] = calculate_solar_elevation(df[time_col], lat, lon)
    else:
        df['solar_elevation'] = 0.0

    return df



def predict_province(province_name):
    print(f"Predicting for: {province_name}...")

    model_file = MODEL_DIR / f"{province_name}_model.pkl"
    scaler_file = MODEL_DIR / f"{province_name}_scaler.pkl"
    metadata_file = MODEL_DIR / f"{province_name}_metadata.json"
    future_file = FUTURE_DATA_DIR / f"{province_name}.csv"
    history_file = DATA_DIR / f"{province_name}.csv"

    if not (
            model_file.exists() and scaler_file.exists() and metadata_file.exists() and future_file.exists() and history_file.exists()):
        print(f"[X] Missing required files for {province_name}")
        return

    try:
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        scaler = joblib.load(scaler_file)
        saved_model = joblib.load(model_file)

        order = tuple(metadata['order'])
        seasonal_order = tuple(metadata['seasonal_order'])
        exog_cols = metadata['exog_cols']


        df_hist = pd.read_csv(history_file)
        df_hist_processed = create_features(df_hist, province_name)
        
        time_col_hist = df_hist_processed.columns[0]
        cutoff = df_hist_processed[time_col_hist].max() - pd.Timedelta(days=7)
        df_hist_processed = df_hist_processed[df_hist_processed[time_col_hist] >= cutoff].reset_index(drop=True)
        
        df_hist_processed = df_hist_processed.ffill().bfill()

        y_hist = df_hist_processed[TARGET_COLUMN].values.astype('float32')
        X_hist = df_hist_processed[exog_cols].values.astype('float32')
        X_hist_scaled = scaler.transform(X_hist)

        model_rebuilt = SARIMAX(
            y_hist,
            exog=X_hist_scaled,
            order=order,
            seasonal_order=seasonal_order,
            enforce_stationarity=False,
            enforce_invertibility=False
        )
        results_rebuilt = model_rebuilt.filter(saved_model.params)

        # xử lý dữ liệu tương lai
        df_future = pd.read_csv(future_file)

        time_col = df_future.columns[0]
        df_future[time_col] = pd.to_datetime(df_future[time_col])

        if df_future.empty:
            print(f"[X] Data future trống cho {province_name}")
            return

        first_date = df_future[time_col].dt.date.iloc[0]
        df_future_1day = df_future[df_future[time_col].dt.date == first_date].copy()

        df_future_processed = create_features(df_future_1day, province_name)

        # kiểm tra cột thiếu
        missing_cols = [col for col in exog_cols if col not in df_future_processed.columns]
        if missing_cols:
            print(f"[X] Missing columns in future data: {missing_cols}")
            return

        X_future = df_future_processed[exog_cols].values.astype('float32')
        X_future_scaled = scaler.transform(X_future)

        # dự báo
        y_pred = results_rebuilt.forecast(steps=len(df_future_1day), exog=X_future_scaled)

        y_pred = np.maximum(y_pred, 0)
        y_pred = np.minimum(y_pred, 1200)

        if 'solar_elevation' in df_future_processed.columns:
            elev = df_future_processed['solar_elevation'].values
            night_mask = elev <= 0
            y_pred[night_mask] = 0

        df_result = pd.DataFrame()
        df_result['time'] = df_future_1day[time_col]
        df_result['predicted_radiation'] = y_pred

        out_path = RESULT_DIR / f"{province_name}_predicted.csv"
        df_result.to_csv(out_path, index=False)
        print(f"[OK] {province_name}: Saved prediction for {first_date} ({len(y_pred)} samples)")

    except Exception as e:
        print(f"[X] Error predicting {province_name}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Predict solar radiation using re-hydrated SARIMAX.")
    parser.add_argument("--province", type=str, default=None, help="Province name")
    parser.add_argument("--all", action="store_true", help="Predict all provinces")
    args = parser.parse_args()

    if args.all:
        files = list(FUTURE_DATA_DIR.glob("*.csv"))
        if not files:
            print(f"No CSV files found in {FUTURE_DATA_DIR}")
        for f in files:
            predict_province(f.stem)
    elif args.province:
        predict_province(args.province)
    else:
        predict_province("An_Giang")