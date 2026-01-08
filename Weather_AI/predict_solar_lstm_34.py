import os
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from tensorflow.keras.models import load_model

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
FUTURE_DIR = BASE_DIR / "data_future"
MODEL_DIR = BASE_DIR / "models_solar_multi_provinces"
RESULT_DIR = BASE_DIR / "results_train_shortwave_radiation_lstm"

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


def predict_dual(province_name):
    past_csv = DATA_DIR / f"{province_name}.csv"
    future_csv = FUTURE_DIR / f"{province_name}.csv"
    model_path = MODEL_DIR / f"{province_name}.keras"
    scaler_x_path = MODEL_DIR / f"scaler_X_{province_name}.pkl"
    scaler_y_path = MODEL_DIR / f"scaler_Y_{province_name}.pkl"

    if not past_csv.exists() or not future_csv.exists() or not model_path.exists():
        print(f"️ Thiếu file cho {province_name}")
        return

    print(f"Dự báo {province_name}...")

    try:
        model = load_model(model_path)
        scaler_X = joblib.load(scaler_x_path)
        scaler_Y = joblib.load(scaler_y_path)

        df_past_raw = pd.read_csv(past_csv)
        df_past, exog_cols = process_features_for_prediction(df_past_raw, province_name)

        if len(df_past) < SEQ_LENGTH:
            print(f" {province_name}: Dữ liệu quá khứ không đủ {SEQ_LENGTH} dòng.")
            return

        last_past_time = df_past.iloc[-1, 0]
        start_pred_time = last_past_time + pd.Timedelta(hours=1)
        end_pred_time = last_past_time + pd.Timedelta(hours=FORECAST_HORIZON)

        print(f" Data end: {last_past_time} -> Predict: {start_pred_time} đến {end_pred_time}")

        feature_cols = ['shortwave_radiation'] + exog_cols + [
            'hour_sin', 'hour_cos', 'month_sin', 'month_cos', 'wet_season',
            'solar_elevation'
        ]

        last_seq = df_past.tail(SEQ_LENGTH)[feature_cols].values.astype('float32')
        input_past_scaled = scaler_X.transform(last_seq)
        input_past = np.expand_dims(input_past_scaled, axis=0)

        # 3. Xử lý TƯƠNG LAI
        df_future_raw = pd.read_csv(future_csv)
        time_col_future = df_future_raw.columns[0]
        df_future_raw[time_col_future] = pd.to_datetime(df_future_raw[time_col_future])

        mask = (df_future_raw[time_col_future] >= start_pred_time) & (df_future_raw[time_col_future] <= end_pred_time)
        df_future_target = df_future_raw.loc[mask].copy()

        if len(df_future_target) < FORECAST_HORIZON:
            print(f" Thiếu dữ liệu tương lai. Tìm thấy {len(df_future_target)} dòng.")
            return

        df_future_target = df_future_target.head(FORECAST_HORIZON)
        future_timeline = df_future_target[time_col_future].reset_index(drop=True)

        df_future_processed, _ = process_features_for_prediction(df_future_target, province_name)

        future_vals = df_future_processed[exog_cols + [
            'hour_sin', 'hour_cos', 'month_sin', 'month_cos', 'wet_season',
            'solar_elevation'
        ]].values.astype('float32')


        dummy_target = np.zeros((FORECAST_HORIZON, 1))
        future_full_raw = np.hstack([dummy_target, future_vals])
        future_full_scaled = scaler_X.transform(future_full_raw)

        input_future_vals = future_full_scaled[:, 1:]
        input_future = np.expand_dims(input_future_vals, axis=0)

        pred_scaled = model.predict([input_past, input_future], verbose=0)
        pred_values = scaler_Y.inverse_transform(pred_scaled.reshape(-1, 1)).flatten()
        pred_values = np.maximum(pred_values, 0)


        future_elevations = df_future_processed['solar_elevation'].values

        night_mask = future_elevations <= 0

        pred_values[night_mask] = 0.0

        result_df = pd.DataFrame({
            'Time': future_timeline,
            'Radiation_Forecast': pred_values,
            'Province': province_name
        })

        output_path = RESULT_DIR / f"forecast_{province_name}.csv"
        result_df.to_csv(output_path, index=False)
        print(f"  Xong: {output_path.name}")

    except Exception as e:
        print(f" Lỗi {province_name}: {e}")


if __name__ == "__main__":
    files = list(DATA_DIR.glob("*.csv"))
    for f in files:
        predict_dual(f.stem)