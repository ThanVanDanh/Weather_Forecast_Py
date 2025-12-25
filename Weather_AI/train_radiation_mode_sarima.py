import os
from pathlib import Path
from typing import Optional
import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

# ================== CẤU HÌNH CHUẨN ==================
# Lấy đường dẫn thư mục chứa file code hiện tại (Weather_AI)
BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "model_solar_sarima"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Tên tỉnh mục tiêu
TARGET_PROVINCE = "An_Giang"
TARGET_COL = "shortwave_radiation"

# Cấu hình SARIMA có MÙA VỤ (Seasonal)
VALIDATION_DAYS = 30

# Order (p,d,q) cho phần phi mùa vụ (Trend)
ORDER = (1, 1, 1)

# Seasonal Order (P,D,Q,s) cho phần mùa vụ
# s: Chu kỳ lặp lại.
# - Nếu dữ liệu ngày (D): s=7 (Tuần), s=30 (Tháng), s=365 (Năm - Rất nặng!)
# - Nếu bạn thấy chạy quá lâu, hãy giảm s xuống hoặc về (0,0,0,0)
SEASONAL_ORDER = (1, 1, 1, 7)


# ================== HÀM XỬ LÝ ==================
def load_and_aggregate_daily(csv_path: Path) -> Optional[pd.DataFrame]:
    try:
        df = pd.read_csv(csv_path)
        if "time" not in df.columns: return None
        df["time"] = pd.to_datetime(df["time"])
        df = df.set_index("time").sort_index()

        if TARGET_COL not in df.columns: return None

        # Resample Daily (Tính tổng bức xạ trong ngày)
        df_daily = df[[TARGET_COL]].resample('D').sum().ffill().bfill()
        return df_daily
    except Exception as e:
        print(f"Lỗi file {csv_path.name}: {e}")
        return None


def train_sarima_angiang():
    print(f"=== TRAINING SARIMA MÙA VỤ (TỈNH: {TARGET_PROVINCE}) ===")
    print(f"Cấu hình: Order={ORDER}, Seasonal={SEASONAL_ORDER}")

    # Tìm file csv của An Giang
    csv_path = DATA_DIR / f"{TARGET_PROVINCE}.csv"

    if not csv_path.exists():
        print(f"❌ Không tìm thấy file dữ liệu: {csv_path}")
        return

    # 1. Load Data
    df = load_and_aggregate_daily(csv_path)
    if df is None or len(df) < 100:
        print("Dữ liệu lỗi hoặc quá ít.")
        return

    # 2. Chia Train/Val
    endog = df[TARGET_COL].astype(float)
    train_endog = endog.iloc[:-VALIDATION_DAYS]
    val_endog = endog.iloc[-VALIDATION_DAYS:]

    # 3. Train
    print(f"Đang train model (có thể lâu hơn bình thường)...")
    try:
        # Thêm enforce_stationarity=False để giảm lỗi hội tụ khi dùng Seasonal
        model = SARIMAX(
            endog=train_endog,
            order=ORDER,
            seasonal_order=SEASONAL_ORDER,
            enforce_stationarity=False,
            enforce_invertibility=False
        )
        results = model.fit(disp=False)

        # 4. Đánh giá sơ bộ
        forecast = results.get_forecast(steps=VALIDATION_DAYS)
        pred = forecast.predicted_mean

        # Xử lý số âm nếu có
        pred[pred < 0] = 0

        mae = np.mean(np.abs(val_endog - pred))
        print(f"✅ Train xong. AIC: {results.aic:.1f} | MAE Val: {mae:.2f}")

        # 5. Lưu Model
        save_name = f"{TARGET_PROVINCE}_radiation_sarimax.pkl"
        results.save(MODELS_DIR / save_name)
        print(f"💾 Đã lưu model tại: {MODELS_DIR / save_name}")

    except Exception as e:
        print(f"Lỗi Training: {e}")


if __name__ == "__main__":
    train_sarima_angiang()