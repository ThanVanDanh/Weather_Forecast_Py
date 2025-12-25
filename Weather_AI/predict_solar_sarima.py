import pandas as pd
import statsmodels.api as sm
from pathlib import Path
from datetime import timedelta
import os

# ================== CẤU HÌNH ==================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "model_solar_sarima"
OUTPUT_DIR = BASE_DIR / "model_solar_sarima"

# Tên tỉnh bạn muốn dự báo (phải trùng với tên file CSV gốc, ví dụ: AnGiang.csv -> AnGiang)
TARGET_PROVINCE = "An_Giang"


def predict_5_days_no_exog():
    print(f"=== BẮT ĐẦU DỰ BÁO 5 NGÀY (CHỈ TỈNH: {TARGET_PROVINCE}) ===")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Tạo đường dẫn cụ thể đến model của An Giang
    # Lưu ý: Tên file model được tạo ra theo quy tắc trong file train: {Tên_Tỉnh}_radiation_sarimax.pkl
    model_name = f"{TARGET_PROVINCE}_radiation_sarimax.pkl"
    model_path = MODELS_DIR / model_name

    # Tạo danh sách chỉ chứa 1 file này để xử lý
    if not model_path.exists():
        print(f"Lỗi: Không tìm thấy model '{model_name}'. Hãy train model cho {TARGET_PROVINCE} trước!")
        return

    model_files = [model_path]

    count = 0
    for model_path in model_files:
        # Lấy tên tỉnh từ tên file model
        province = model_path.name.replace("_radiation_sarimax.pkl", "")
        csv_path = DATA_DIR / f"{province}.csv"

        if not csv_path.exists():
            print(f"Thiếu data gốc cho {province} (cần để xác định ngày), bỏ qua.")
            continue

        try:
            # 2. Load Model
            print(f"Đang xử lý: {province}...")
            model = sm.load(str(model_path))

            # 3. Load Data chỉ để lấy ngày cuối cùng (làm mốc thời gian)
            df = pd.read_csv(csv_path)
            df["time"] = pd.to_datetime(df["time"])
            df = df.set_index("time").sort_index()

            # Resample để biết chính xác ngày cuối cùng của dữ liệu daily
            df_daily_index = df.resample('D').asfreq().index
            last_date = df_daily_index[-1]

            # 4. Thực hiện Dự báo 5 ngày
            forecast_result = model.get_forecast(steps=5)
            predicted_values = forecast_result.predicted_mean
            predicted_values[predicted_values < 0] = 0

            # 5. Tạo DataFrame kết quả
            forecast_dates = [last_date + timedelta(days=i + 1) for i in range(5)]

            result_df = pd.DataFrame({
                "Date": forecast_dates,
                "Solar_Radiation_Wh_m2": predicted_values.values.round(2),
                "Province": province
            })

            # 6. Lưu ra file CSV
            save_path = OUTPUT_DIR / f"{province}.csv"
            result_df.to_csv(save_path, index=False, encoding="utf-8-sig")

            print(f"-> Đã lưu kết quả tại: {save_path}")
            count += 1

        except Exception as e:
            print(f"Lỗi khi xử lý {province}: {e}")

    print(f"\nHOÀN TẤT! Đã tạo file dự báo cho {count} tỉnh.")


if __name__ == "__main__":
    predict_5_days_no_exog()