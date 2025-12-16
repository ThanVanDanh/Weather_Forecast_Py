import pandas as pd
import statsmodels.api as sm
from pathlib import Path
from datetime import timedelta
import os

# ================== CẤU HÌNH ==================
BASE_DIR = Path("Weather_AI")
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"

# Thư mục chứa các file CSV kết quả
OUTPUT_DIR = BASE_DIR / "forecast_5_days"

# Cấu hình biến ngoại sinh
EXOG_CONFIG = {
    "cloudcover": "mean",
    "cloudcover_low": "mean",
    "cloudcover_mid": "mean",
    "cloudcover_high": "mean",
    "precipitation": "sum",
    "rain": "sum",
    "relative_humidity_2m": "mean",
    "dewpoint_2m": "mean",
    "temperature_2m": "mean",
    "direct_radiation": "sum",
    "diffuse_radiation": "sum",
    "weathercode": "max"
}


def predict_5_days_separate_files():
    print(f"=== BẮT ĐẦU DỰ BÁO 5 NGÀY VÀ XUẤT FILE RIÊNG LẺ ===")

    # Tạo thư mục output nếu chưa có
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Lấy danh sách model
    model_files = sorted(MODELS_DIR.glob("*_radiation_sarimax.pkl"))

    if not model_files:
        print("❌ Không tìm thấy model nào. Hãy train trước!")
        return

    count = 0
    for model_path in model_files:
        # Lấy tên tỉnh từ tên file model
        province = model_path.name.replace("_radiation_sarimax.pkl", "")
        csv_path = DATA_DIR / f"{province}.csv"

        if not csv_path.exists():
            print(f"⚠️ Thiếu data gốc cho {province}, bỏ qua.")
            continue

        try:
            # 2. Load Model & Data
            model = sm.load(str(model_path))

            df = pd.read_csv(csv_path)
            df["time"] = pd.to_datetime(df["time"])
            df = df.set_index("time").sort_index()

            # Resample sang Daily để khớp với model đã train
            agg_dict = {k: v for k, v in EXOG_CONFIG.items() if k in df.columns}
            df_daily = df.resample('D').agg(agg_dict).ffill().bfill()

            # 3. Lấy dữ liệu ngoại sinh giả lập cho 5 ngày tới
            # (Lấy 5 ngày cuối cùng của dữ liệu lịch sử để làm giả định cho tương lai)
            exog_future = df_daily[list(agg_dict.keys())].iloc[-5:]

            # 4. Thực hiện Dự báo 5 ngày (steps=5)
            forecast_result = model.get_forecast(steps=5, exog=exog_future)
            predicted_values = forecast_result.predicted_mean
            predicted_values[predicted_values < 0] = 0  # Bức xạ không thể âm

            # 5. Tạo DataFrame kết quả cho tỉnh này
            last_date = df_daily.index[-1]
            forecast_dates = [last_date + timedelta(days=i + 1) for i in range(5)]

            result_df = pd.DataFrame({
                "Date": forecast_dates,
                "Solar_Radiation_Wh_m2": predicted_values.values.round(2),
                "Province": province
            })

            # 6. Lưu ra file CSV riêng biệt trong thư mục forecast_5_days
            save_path = OUTPUT_DIR / f"{province}.csv"
            result_df.to_csv(save_path, index=False, encoding="utf-8-sig")

            print(f"✅ Đã lưu: {save_path}")
            count += 1

        except Exception as e:
            print(f"❌ Lỗi {province}: {e}")

    print(f"\n🎉 HOÀN TẤT! Đã tạo {count} file CSV trong thư mục '{OUTPUT_DIR}'")


if __name__ == "__main__":
    predict_5_days_separate_files()