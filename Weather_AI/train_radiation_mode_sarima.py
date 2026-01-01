import pandas as pd
import numpy as np
from pathlib import Path
from statsmodels.tsa.statespace.sarimax import SARIMAX
import warnings

warnings.filterwarnings("ignore")

# ================== CẤU HÌNH ==================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "model_solar_sarima"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

TARGET_PROVINCE = "An_Giang"
TARGET_COL = "shortwave_radiation"

# Cấu hình ARIMA (đã tinh chỉnh cho Hourly)
# p,d,q: Tự hồi quy, sai phân, trung bình trượt
ORDER = (2, 0, 2)
# P,D,Q,s: Mùa vụ. s=24 (chu kỳ 24h).
# Lưu ý: Vì đã dùng Fourier gánh bớt phần chu kỳ, ta để Seasonal nhẹ hoặc tắt (0,0,0,0) để train nhanh hơn.
# Ở đây mình để (1,0,1,24) để bắt các mẫu còn sót lại.
SEASONAL_ORDER = (1, 0, 1, 24)


def add_fourier_terms(df, time_col_name='time'):
    """
    Tạo biến ngoại sinh (Exogenous) dựa trên chu kỳ thời gian
    """
    df_exog = df.copy()
    if time_col_name in df_exog.columns:
        times = df_exog[time_col_name]
    else:
        times = df_exog.index

    # 1. Chu kỳ Ngày (24h) - Quan trọng nhất cho bức xạ
    # Giúp model hiểu: 12h trưa nắng to, 0h đêm không có nắng
    df_exog['hour_sin'] = np.sin(2 * np.pi * times.hour / 24)
    df_exog['hour_cos'] = np.cos(2 * np.pi * times.hour / 24)

    # 2. Chu kỳ Năm (365.25 ngày)
    # Giúp model hiểu: Mùa hè nắng nhiều hơn mùa đông
    day_of_year = times.dayofyear
    df_exog['year_sin'] = np.sin(2 * np.pi * day_of_year / 365.25)
    df_exog['year_cos'] = np.cos(2 * np.pi * day_of_year / 365.25)

    return df_exog[['hour_sin', 'hour_cos', 'year_sin', 'year_cos']]


def load_and_prep_hourly_data(csv_path: Path):
    df = pd.read_csv(csv_path)
    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").sort_index()

    # Resample về theo GIỜ (1h) thay vì theo ngày
    # ffill/bfill để lấp dữ liệu thiếu nhỏ, cẩn thận đừng lấp quá xa
    df_hourly = df[[TARGET_COL]].resample('h').mean().interpolate(method='linear')

    # Xử lý số âm (bức xạ không thể âm)
    df_hourly[df_hourly < 0] = 0

    # Tạo biến ngoại sinh
    exog = add_fourier_terms(df_hourly, time_col_name=None)  # Index là time

    return df_hourly, exog


def train_sarimax_hourly():
    print(f"=== TRAINING SARIMAX HOURLY (TỈNH: {TARGET_PROVINCE}) ===")
    csv_path = DATA_DIR / f"{TARGET_PROVINCE}.csv"

    if not csv_path.exists():
        print(f"❌ Thiếu file data: {csv_path}")
        return

    # 1. Load Data
    df, exog = load_and_prep_hourly_data(csv_path)

    # Lấy 1000 giờ cuối để train cho nhanh (hoặc lấy hết nếu máy mạnh)
    # Solar data theo giờ rất nặng (1 năm = 8760 dòng).
    # Demo lấy 3 tháng gần nhất (~2000 dòng).
    TRAIN_SIZE = 24 * 90

    y_train = df[TARGET_COL].iloc[-TRAIN_SIZE:]
    X_train = exog.iloc[-TRAIN_SIZE:]

    print(f"Dữ liệu train: {len(y_train)} dòng (đã resample 1h).")
    print("Đang train model (có thể mất vài phút vì s=24)...")

    try:
        # Sử dụng SARIMAX với biến ngoại sinh (exog)
        model = SARIMAX(
            endog=y_train,
            exog=X_train,
            order=ORDER,
            seasonal_order=SEASONAL_ORDER,
            enforce_stationarity=False,
            enforce_invertibility=False
        )
        results = model.fit(disp=False, method='powell')  # 'powell' thường bền hơn với dữ liệu phức tạp

        print(f"✅ Train xong. AIC: {results.aic:.1f}")

        # Lưu Model
        save_name = f"{TARGET_PROVINCE}_radiation_hourly_sarimax.pkl"
        results.save(MODELS_DIR / save_name)
        print(f"💾 Đã lưu model tại: {MODELS_DIR / save_name}")

    except Exception as e:
        print(f"Lỗi Training: {e}")


if __name__ == "__main__":
    train_sarimax_hourly()