import pandas as pd
import numpy as np
import statsmodels.api as sm
from pathlib import Path
from datetime import timedelta
from statsmodels.tsa.statespace.sarimax import SARIMAX
import warnings

warnings.filterwarnings("ignore")

# ================== CẤU HÌNH ==================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "model_solar_sarima_full"
OUTPUT_DIR = BASE_DIR / "predictions_full"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET_COL = "shortwave_radiation"

# CẤU HÌNH MODEL (PHẢI GIỐNG Y HỆT LÚC TRAIN)
ORDER = (3, 0, 3)
SEASONAL_ORDER = (1, 0, 1, 24)
FOURIER_K_DAY = 2
FOURIER_K_YEAR = 5


def add_fourier_terms(df, time_col_name='time'):
    """Hàm tạo Fourier y hệt lúc train để tái nạp dữ liệu"""
    df_exog = df.copy()
    if time_col_name in df_exog.columns:
        times = df_exog[time_col_name]
    else:
        times = df_exog.index

    # 1. Chu kỳ Ngày
    for k in range(1, FOURIER_K_DAY + 1):
        df_exog[f'sin_day_{k}'] = np.sin(2 * np.pi * k * times.hour / 24)
        df_exog[f'cos_day_{k}'] = np.cos(2 * np.pi * k * times.hour / 24)

    # 2. Chu kỳ Năm
    day_of_year = times.dayofyear
    for k in range(1, FOURIER_K_YEAR + 1):
        df_exog[f'sin_year_{k}'] = np.sin(2 * np.pi * k * day_of_year / 365.25)
        df_exog[f'cos_year_{k}'] = np.cos(2 * np.pi * k * day_of_year / 365.25)

    fourier_cols = [c for c in df_exog.columns if 'sin_' in c or 'cos_' in c]
    return df_exog[fourier_cols]


def load_and_prep_data(csv_path: Path):
    """Hàm load data để 'nhắc lại bộ nhớ' cho model"""
    df = pd.read_csv(csv_path)
    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").sort_index()

    # Resample & Clean giống hệt lúc train
    df_hourly = df[[TARGET_COL]].resample('h').mean().interpolate(method='linear')
    df_hourly[df_hourly < 0] = 0

    exog = add_fourier_terms(df_hourly, time_col_name=None)

    common_idx = df_hourly.index.intersection(exog.index)
    return df_hourly.loc[common_idx], exog.loc[common_idx]


def create_future_exog(start_date, periods=24):
    """Tạo biến Fourier cho tương lai"""
    future_dates = pd.date_range(start=start_date, periods=periods, freq='h')
    df_future = pd.DataFrame(index=future_dates)

    hours = df_future.index.hour
    day_of_year = df_future.index.dayofyear

    for k in range(1, FOURIER_K_DAY + 1):
        df_future[f'sin_day_{k}'] = np.sin(2 * np.pi * k * hours / 24)
        df_future[f'cos_day_{k}'] = np.cos(2 * np.pi * k * hours / 24)

    for k in range(1, FOURIER_K_YEAR + 1):
        df_future[f'sin_year_{k}'] = np.sin(2 * np.pi * k * day_of_year / 365.25)
        df_future[f'cos_year_{k}'] = np.cos(2 * np.pi * k * day_of_year / 365.25)

    return df_future


def predict_province(province_name, hours_to_predict=24):
    print(f"⌛ Đang dự báo cho: {province_name}...")

    model_path = MODELS_DIR / f"{province_name}_sarimax_full.pkl"
    csv_path = DATA_DIR / f"{province_name}.csv"

    if not model_path.exists():
        print(f"   ⚠️ Không tìm thấy model: {model_path}")
        return None

    try:
        # 1. Load Data Gốc để tái tạo trạng thái
        df, exog = load_and_prep_data(csv_path)

        # 2. Load Model đã lưu (Chỉ chứa tham số)
        saved_model = sm.load(str(model_path))
        params = saved_model.params

        # 3. Khởi tạo lại Model và Filter
        model = SARIMAX(
            endog=df[TARGET_COL],
            exog=exog,
            order=ORDER,
            seasonal_order=SEASONAL_ORDER,
            enforce_stationarity=False,
            enforce_invertibility=False
        )
        model_results = model.filter(params)

        # 4. Tạo biến tương lai & Dự báo
        last_time = df.index.max()
        start_forecast = last_time + timedelta(hours=1)
        exog_future = create_future_exog(start_forecast, periods=hours_to_predict)

        forecast = model_results.get_forecast(steps=hours_to_predict, exog=exog_future)
        predicted_values = forecast.predicted_mean

        # 5. Xử lý hậu kỳ
        predicted_values[predicted_values < 0] = 0
        is_night = (predicted_values.index.hour >= 19) | (predicted_values.index.hour <= 5)
        predicted_values.loc[is_night] = 0

        # 6. Lưu kết quả
        result_df = pd.DataFrame({
            "Time": predicted_values.index,
            "Province": province_name,
            "Solar_Radiation_Wh_m2": predicted_values.values.round(2)
        })

        return result_df

    except Exception as e:
        print(f"   ❌ Lỗi dự báo {province_name}: {e}")
        return None


def run_prediction_all():
    model_files = list(MODELS_DIR.glob("*_sarimax_full.pkl"))

    if not model_files:
        print("Chưa có model nào. Hãy chạy train trước!")
        return

    print(f"=== BẮT ĐẦU DỰ BÁO ({len(model_files)} TỈNH - 24H TỚI) ===")
    all_results = []

    for model_file in model_files:
        province_name = model_file.name.replace("_sarimax_full.pkl", "")

        # === ĐÃ SỬA THÀNH 24 GIỜ ===
        df_res = predict_province(province_name, hours_to_predict=24)

        if df_res is not None:
            all_results.append(df_res)
            df_res.to_csv(OUTPUT_DIR / f"{province_name}_pred.csv", index=False)

    if all_results:
        final_df = pd.concat(all_results)
        master_path = OUTPUT_DIR / "ALL_PROVINCES_FORECAST_24H.csv"
        final_df.to_csv(master_path, index=False)
        print(f"\n✅ Đã hoàn tất! File tổng hợp 24h: {master_path}")
        print(final_df.head())


if __name__ == "__main__":
    run_prediction_all()