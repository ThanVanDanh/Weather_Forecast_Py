import pandas as pd
import numpy as np
import statsmodels.api as sm
from pathlib import Path
from datetime import timedelta

# ================== CẤU HÌNH ==================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "model_solar_sarima"
OUTPUT_DIR = BASE_DIR / "model_solar_sarima"  # Thư mục lưu kết quả mới
TARGET_PROVINCE = "An_Giang"


def create_future_exog(start_date, periods=24):
    """
    Tạo biến Fourier cho tương lai (24 giờ tiếp theo)
    """
    # Tạo dải thời gian theo giờ
    future_dates = pd.date_range(start=start_date, periods=periods, freq='h')

    df_future = pd.DataFrame(index=future_dates)

    # Tính toán Fourier y hệt lúc train
    df_future['hour_sin'] = np.sin(2 * np.pi * df_future.index.hour / 24)
    df_future['hour_cos'] = np.cos(2 * np.pi * df_future.index.hour / 24)

    day_of_year = df_future.index.dayofyear
    df_future['year_sin'] = np.sin(2 * np.pi * day_of_year / 365.25)
    df_future['year_cos'] = np.cos(2 * np.pi * day_of_year / 365.25)

    return df_future


def predict_24h_next():
    print(f"=== DỰ BÁO 24 GIỜ TỚI (TỈNH: {TARGET_PROVINCE}) ===")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    model_name = f"{TARGET_PROVINCE}_radiation_hourly_sarimax.pkl"
    model_path = MODELS_DIR / model_name
    csv_path = DATA_DIR / f"{TARGET_PROVINCE}.csv"

    if not model_path.exists():
        print("Chưa có model hourly. Hãy chạy train_radiation_hourly.py trước!")
        return

    try:
        # 1. Load Data gốc để lấy mốc thời gian cuối cùng
        df = pd.read_csv(csv_path)
        df["time"] = pd.to_datetime(df["time"])
        last_time = df["time"].max()

        # Thời gian bắt đầu dự báo là giờ tiếp theo của dữ liệu cuối cùng
        start_forecast = last_time + timedelta(hours=1)
        print(f"Dữ liệu cuối: {last_time}. Dự báo từ: {start_forecast}")

        # 2. Load Model
        model_loaded = sm.load(str(model_path))

        # 3. Tạo biến ngoại sinh cho 24h tới
        # Model cần biết "giờ nào" để áp dụng công thức sin/cos
        exog_future = create_future_exog(start_forecast, periods=24)

        # 4. Dự báo
        # steps=24 (24 giờ), truyền exog mới vào
        forecast = model_loaded.get_forecast(steps=24, exog=exog_future)
        predicted_values = forecast.predicted_mean

        # Làm sạch: Bức xạ ban đêm (nếu model dự báo âm hoặc dương nhỏ) về 0
        # Mẹo: Ép các giờ từ 19h tối đến 5h sáng về 0 để loại bỏ nhiễu của model
        predicted_values[predicted_values < 0] = 0

        # Optional: Hard-code ban đêm về 0 (nếu muốn biểu đồ đẹp tuyệt đối)
        # for time_idx in predicted_values.index:
        #     if time_idx.hour > 18 or time_idx.hour < 6:
        #         predicted_values[time_idx] = 0

        # 5. Lưu kết quả
        result_df = pd.DataFrame({
            "Time": predicted_values.index,
            "Solar_Radiation_Wh_m2": predicted_values.values.round(2),
            "Province": TARGET_PROVINCE
        })

        save_path = OUTPUT_DIR / f"{TARGET_PROVINCE}_24h.csv"
        result_df.to_csv(save_path, index=False)
        print(f"-> Đã lưu dự báo tại: {save_path}")
        print(result_df.head(10))  # In thử vài dòng đầu

    except Exception as e:
        print(f"Lỗi: {e}")


if __name__ == "__main__":
    predict_24h_next()