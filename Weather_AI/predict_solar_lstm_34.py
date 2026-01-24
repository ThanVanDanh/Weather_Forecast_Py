import os
import sys
import argparse
import numpy as np
import pandas as pd
import joblib
import requests
import time
from pathlib import Path
from tensorflow.keras.models import load_model
from datetime import datetime as py_datetime

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
FUTURE_DIR = BASE_DIR / "data_future"
MODEL_DIR = BASE_DIR / "models_solar_multi_provinces"
RESULT_DIR = BASE_DIR / "results_train_shortwave_radiation_lstm"

FUTURE_DIR.mkdir(exist_ok=True)
RESULT_DIR.mkdir(exist_ok=True)

SEQ_LENGTH = 72
FORECAST_HORIZON = 24
WET_MONTHS = {5, 6, 7, 8, 9, 10}

EXOG_COLUMNS = [
    'temperature_2m', 'relative_humidity_2m',
    'cloud_cover', 'cloudcover',
    'precipitation', 'rain', 'wind_speed_10m'
]

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


def process_features_for_prediction(df, province_name):
    df = df.copy()
    time_col = df.columns[0]
    df[time_col] = pd.to_datetime(df[time_col])
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

    avail_exog = [c for c in EXOG_COLUMNS if c in df.columns]
    return df, avail_exog


def fetch_weather_forecast(lat, lon, start_date, end_date):
    url = "https://api.open-meteo.com/v1/forecast"
    fields = ["temperature_2m", "relative_humidity_2m", "cloudcover", "precipitation", "rain", "wind_speed_10m"]
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "hourly": ",".join(fields),
        "timezone": "Asia/Ho_Chi_Minh"
    }
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        if "hourly" not in data: return pd.DataFrame()
        df = pd.DataFrame(data["hourly"])
        if "time" in df.columns: df.rename(columns={"time": "Time"}, inplace=True)
        df["Time"] = pd.to_datetime(df["Time"])
        if 'cloudcover' in df.columns: df['cloud_cover'] = df['cloudcover']
        return df
    except:
        return pd.DataFrame()


def predict_dual(province_name):
    past_csv = DATA_DIR / f"{province_name}.csv"
    future_csv = FUTURE_DIR / f"{province_name}.csv"
    model_path = MODEL_DIR / f"{province_name}.keras"
    scaler_x_path = MODEL_DIR / f"scaler_X_{province_name}.pkl"
    scaler_y_path = MODEL_DIR / f"scaler_Y_{province_name}.pkl"

    if not past_csv.exists() or not model_path.exists():
        print(f"Loi: Thieu file cho {province_name}")
        return

    try:
        model = load_model(model_path)
        scaler_X = joblib.load(scaler_x_path)
        scaler_Y = joblib.load(scaler_y_path)

        df_past_raw = pd.read_csv(past_csv)
        df_past, exog_cols = process_features_for_prediction(df_past_raw, province_name)
        if len(df_past) < SEQ_LENGTH: return

        last_past_time = df_past.iloc[-1, 0]
        start_pred_time = last_past_time + pd.Timedelta(hours=1)
        end_pred_time = last_past_time + pd.Timedelta(hours=FORECAST_HORIZON)

        df_future_raw = pd.DataFrame()
        if future_csv.exists():
            df_future_raw = pd.read_csv(future_csv)
            t_col = df_future_raw.columns[0]
            df_future_raw[t_col] = pd.to_datetime(df_future_raw[t_col])
            if df_future_raw.empty or df_future_raw[t_col].min() > start_pred_time or df_future_raw[
                t_col].max() < end_pred_time:
                df_future_raw = pd.DataFrame()

        if df_future_raw.empty:
            lat, lon = PROVINCE_COORDINATES[province_name]
            df_future_raw = fetch_weather_forecast(lat, lon, start_pred_time.date(),
                                                   (end_pred_time + pd.Timedelta(days=1)).date())
            if not df_future_raw.empty: df_future_raw.to_csv(future_csv, index=False)

        if df_future_raw.empty: return

        t_col = df_future_raw.columns[0]
        df_future_raw[t_col] = pd.to_datetime(df_future_raw[t_col])
        mask = (df_future_raw[t_col] >= start_pred_time) & (df_future_raw[t_col] <= end_pred_time)
        df_future_target = df_future_raw.loc[mask].head(FORECAST_HORIZON).copy()

        if len(df_future_target) < FORECAST_HORIZON: return

        future_timeline = df_future_target[t_col].reset_index(drop=True)
        feature_cols = ['shortwave_radiation'] + exog_cols + ['hour_sin', 'hour_cos', 'month_sin', 'month_cos',
                                                              'wet_season', 'solar_elevation']

        last_seq = df_past.tail(SEQ_LENGTH)[feature_cols].values.astype('float32')
        input_past = np.expand_dims(scaler_X.transform(last_seq), axis=0)

        df_future_processed, _ = process_features_for_prediction(df_future_target, province_name)
        future_req_cols = exog_cols + ['hour_sin', 'hour_cos', 'month_sin', 'month_cos', 'wet_season',
                                       'solar_elevation']
        future_vals = df_future_processed[future_req_cols].values.astype('float32')

        future_full_scaled = scaler_X.transform(np.hstack([np.zeros((FORECAST_HORIZON, 1)), future_vals]))
        input_future = np.expand_dims(future_full_scaled[:, 1:], axis=0)

        pred_scaled = model.predict([input_past, input_future], verbose=0)
        pred_values = scaler_Y.inverse_transform(pred_scaled.reshape(-1, 1)).flatten()
        pred_values = np.maximum(pred_values, 0)

        night_mask = df_future_processed['solar_elevation'].values <= 0
        pred_values[night_mask] = 0.0

        result_df = pd.DataFrame(
            {'Time': future_timeline, 'Radiation_Forecast': pred_values, 'Province': province_name})
        result_df.to_csv(RESULT_DIR / f"forecast_{province_name}.csv", index=False)
        print(f"Hoan tat: {province_name}")

    except Exception as e:
        print(f"Loi {province_name}: {e}")


def predict_for_date(province_name, target_date):
    """Predict shortwave radiation for 00:00..23:00 of a specific date."""
    past_csv = DATA_DIR / f"{province_name}.csv"
    future_csv = FUTURE_DIR / f"{province_name}.csv"
    model_path = MODEL_DIR / f"{province_name}.keras"
    scaler_x_path = MODEL_DIR / f"scaler_X_{province_name}.pkl"
    scaler_y_path = MODEL_DIR / f"scaler_Y_{province_name}.pkl"

    if not past_csv.exists() or not model_path.exists():
        print(f"Loi: Thieu file cho {province_name}")
        return

    try:
        model = load_model(model_path)
        scaler_X = joblib.load(scaler_x_path)
        scaler_Y = joblib.load(scaler_y_path)

        df_past_raw = pd.read_csv(past_csv)
        df_past, exog_cols = process_features_for_prediction(df_past_raw, province_name)
        if len(df_past) < SEQ_LENGTH:
            return

        # Build target 24h timeline for the requested date
        start_pred_time = pd.Timestamp(target_date)  # 00:00
        end_pred_time = start_pred_time + pd.Timedelta(hours=23)

        df_future_raw = pd.DataFrame()
        if future_csv.exists():
            try:
                df_future_raw = pd.read_csv(future_csv)
                t_col = df_future_raw.columns[0]
                df_future_raw[t_col] = pd.to_datetime(df_future_raw[t_col])
                # Ensure cache contains the target date fully
                mask_date = df_future_raw[t_col].dt.date == target_date
                if mask_date.sum() < 24:
                    df_future_raw = pd.DataFrame()
            except Exception:
                df_future_raw = pd.DataFrame()

        if df_future_raw.empty:
            lat, lon = PROVINCE_COORDINATES[province_name]
            df_future_raw = fetch_weather_forecast(lat, lon, start_pred_time.date(), start_pred_time.date())
            if not df_future_raw.empty:
                df_future_raw.to_csv(future_csv, index=False)

        if df_future_raw.empty:
            return

        t_col = df_future_raw.columns[0]
        df_future_raw[t_col] = pd.to_datetime(df_future_raw[t_col])
        mask = (df_future_raw[t_col] >= start_pred_time) & (df_future_raw[t_col] <= end_pred_time)
        df_future_target = df_future_raw.loc[mask].copy()

        # Some APIs may include more than 24 rows due to DST/timezone quirks; force 24 hours
        df_future_target = df_future_target.sort_values(t_col).head(FORECAST_HORIZON)

        if len(df_future_target) < FORECAST_HORIZON:
            return

        future_timeline = df_future_target[t_col].reset_index(drop=True)

        feature_cols = ['shortwave_radiation'] + exog_cols + ['hour_sin', 'hour_cos', 'month_sin', 'month_cos',
                                                              'wet_season', 'solar_elevation']

        last_seq = df_past.tail(SEQ_LENGTH)[feature_cols].values.astype('float32')
        input_past = np.expand_dims(scaler_X.transform(last_seq), axis=0)

        df_future_processed, _ = process_features_for_prediction(df_future_target, province_name)
        future_req_cols = exog_cols + ['hour_sin', 'hour_cos', 'month_sin', 'month_cos', 'wet_season',
                                       'solar_elevation']
        future_vals = df_future_processed[future_req_cols].values.astype('float32')

        future_full_scaled = scaler_X.transform(np.hstack([np.zeros((FORECAST_HORIZON, 1)), future_vals]))
        input_future = np.expand_dims(future_full_scaled[:, 1:], axis=0)

        pred_scaled = model.predict([input_past, input_future], verbose=0)
        pred_values = scaler_Y.inverse_transform(pred_scaled.reshape(-1, 1)).flatten()
        pred_values = np.maximum(pred_values, 0)

        night_mask = df_future_processed['solar_elevation'].values <= 0
        pred_values[night_mask] = 0.0

        result_df = pd.DataFrame({'Time': future_timeline, 'Radiation_Forecast': pred_values, 'Province': province_name})
        result_df.to_csv(RESULT_DIR / f"forecast_{province_name}.csv", index=False)
        print(f"Hoan tat: {province_name} ({target_date})")

    except Exception as e:
        print(f"Loi {province_name}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('province', nargs='?', help='Ten tinh (vd: Ha_Noi)')
    parser.add_argument('--date', dest='date', help='YYYY-MM-DD (predict 00-23h of that day)')
    parser.add_argument(
        '--rolling',
        action='store_true',
        help='Predict next 24h starting from last past timestamp (old behavior)'
    )
    args = parser.parse_args()

    if not args.province:
        print("Cach dung: python predict_solar_lstm_34.py <Ten_Tinh> [--date YYYY-MM-DD] [--rolling]")
        raise SystemExit(1)

    if args.rolling:
        predict_dual(args.province)
    elif args.date:
        try:
            target_date = pd.to_datetime(args.date).date()
        except Exception:
            print("Sai dinh dang --date, dung YYYY-MM-DD")
            raise SystemExit(1)
        predict_for_date(args.province, target_date)
    else:
        # Default: forecast 00:00..23:00 of today in Vietnam time
        if ZoneInfo is not None:
            today_vn = py_datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()
        else:
            today_vn = py_datetime.now().date()
        predict_for_date(args.province, today_vn)