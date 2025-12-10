"""
Train mô hình SARIMAX dự báo NHIỆT ĐỘ (temperature) theo giờ
cho từng tỉnh, sử dụng dữ liệu 3 năm lưu trong thư mục ./data.

- Dữ liệu đầu vào: mỗi tỉnh 1 file CSV: data/{province}.csv
- Mỗi file có dạng time series theo giờ, cột "time" + các field thời tiết
  (ví dụ: temperature_2m, relative_humidity_2m, wind_speed_10m, ...)

- Mô hình: SARIMAX
    - endog: nhiệt độ (temperature_2m hoặc temperature)
    - exog: một số biến ngoại sinh (humidity, cloud, rain, ...)
    - order = (1, 1, 1)
    - seasonal_order = (1, 1, 1, 24)  # chu kỳ 24h (1 ngày)

- Kết quả:
    - models/{province}_temp_sarimax.pkl : model đã train
    - In ra MAE, RMSE trên 7 ngày cuối (validation) cho từng tỉnh
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX, SARIMAXResults


# ================== CẤU HÌNH THƯ MỤC ==================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(exist_ok=True)


# ================== CẤU HÌNH MÔ HÌNH SARIMAX ==================

# Cấu hình (p, d, q)
NON_SEASONAL_ORDER = (1, 1, 1)

# Cấu hình (P, D, Q, s) với s = 24 (chu kỳ 24 giờ ~ 1 ngày)
SEASONAL_ORDER = (1, 1, 1, 24)

# Số giờ dùng để validation (ví dụ: 7 ngày cuối)
VALIDATION_HOURS = 24 * 7  # 168 giờ


# Các cột exogenous ưu tiên (nếu có trong CSV)
PREFERRED_EXOG_COLS = [
    "relative_humidity_2m",
    "dewpoint_2m",
    "wind_speed_10m",
    "surface_pressure",
    "precipitation",
    "cloudcover",
]


# ================== HÀM TIỆN ÍCH ==================

def find_temperature_column(columns: List[str]) -> Optional[str]:
    """
    Tìm tên cột nhiệt độ trong DataFrame.
    Ưu tiên "temperature_2m", nếu không có thì thử "temperature".
    """
    if "temperature_2m" in columns:
        return "temperature_2m"
    if "temperature" in columns:
        return "temperature"
    # Thử tìm cột có chữ "temp"
    for col in columns:
        if "temp" in col.lower():
            return col
    return None


def select_exog_columns(df: pd.DataFrame) -> List[str]:
    """
    Chọn danh sách cột exogenous từ PREFERRED_EXOG_COLS có mặt trong df.
    """
    return [col for col in PREFERRED_EXOG_COLS if col in df.columns]


def load_province_dataset(csv_path: Path) -> pd.DataFrame:
    """
    Đọc file CSV và chuẩn hóa thành time series theo giờ:
    - Parse cột "time" thành DatetimeIndex
    - Sort theo thời gian
    - Xử lý missing đơn giản (ffill/bfill)
    """
    df = pd.read_csv(csv_path)

    # Đảm bảo có cột 'time'
    if "time" not in df.columns:
        raise ValueError(f"File {csv_path.name} không có cột 'time'.")

    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").sort_index()

    # Nếu dataset không đều theo giờ, có thể asfreq('H') rồi fill
    # Tuy nhiên nếu dữ liệu từ Open-Meteo chuẩn rồi thì có thể bỏ qua.
    # df = df.asfreq("H")

    # Xử lý missing: forward fill rồi backward fill cho an toàn
    df = df.ffill().bfill()

    return df


def train_sarimax_for_province(province_name: str, csv_path: Path) -> Optional[Tuple[float, float]]:
    """
    Train SARIMAX dự báo nhiệt độ cho 1 tỉnh.
    - province_name: tên tỉnh (dùng để log và lưu model)
    - csv_path: đường dẫn tới file CSV của tỉnh đó

    Trả về (mae, rmse) trên tập validation,
    hoặc None nếu không train được.
    """
    print(f"\n=== Training SARIMAX TEMP cho tỉnh: {province_name} ===")

    # 1. Load dữ liệu
    df = load_province_dataset(csv_path)

    # 2. Tìm cột nhiệt độ
    temp_col = find_temperature_column(df.columns.tolist())
    if temp_col is None:
        print(f"[{province_name}] Không tìm thấy cột nhiệt độ trong file {csv_path.name}, bỏ qua.")
        return None

    endog = df[temp_col].astype(float)

    # 3. Chọn exogenous
    exog_cols = select_exog_columns(df)
    if not exog_cols:
        print(f"[{province_name}] Không có cột exogenous phù hợp, train SARIMA (không exog).")
        exog = None
    else:
        exog = df[exog_cols].astype(float)

    # 4. Tách train / validation
    if len(df) <= VALIDATION_HOURS * 2:
        print(f"[{province_name}] Dữ liệu quá ít ({len(df)} dòng), vẫn train full nhưng không đánh giá validation.")
        train_endog = endog
        train_exog = exog
        val_endog = None
        val_exog = None
    else:
        train_endog = endog.iloc[:-VALIDATION_HOURS]
        val_endog = endog.iloc[-VALIDATION_HOURS:]

        if exog is not None:
            train_exog = exog.iloc[:-VALIDATION_HOURS]
            val_exog = exog.iloc[-VALIDATION_HOURS:]
        else:
            train_exog = None
            val_exog = None

    # 5. Khởi tạo & fit SARIMAX
    print(f"[{province_name}] Fitting model với order={NON_SEASONAL_ORDER}, seasonal_order={SEASONAL_ORDER} ...")

    model = SARIMAX(
        endog=train_endog,
        exog=train_exog,
        order=NON_SEASONAL_ORDER,
        seasonal_order=SEASONAL_ORDER,
        enforce_stationarity=False,
        enforce_invertibility=False,
    )

    results = model.fit(disp=False)
    print(f"[{province_name}] Fit xong. AIC = {results.aic:.2f}, BIC = {results.bic:.2f}")

    # 6. Đánh giá trên validation (nếu có)
    mae = rmse = np.nan
    if val_endog is not None:
        print(f"[{province_name}] Đang đánh giá trên {VALIDATION_HOURS} giờ validation cuối...")

        if val_exog is not None:
            forecast_res = results.get_forecast(steps=VALIDATION_HOURS, exog=val_exog)
        else:
            forecast_res = results.get_forecast(steps=VALIDATION_HOURS)

        y_pred = forecast_res.predicted_mean
        y_true = val_endog

        # Căn chỉnh index (phòng trường hợp lệch)
        y_pred = y_pred.reindex(y_true.index)

        mae = float(np.mean(np.abs(y_true - y_pred)))
        rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))

        print(f"[{province_name}] Validation MAE  = {mae:.4f}")
        print(f"[{province_name}] Validation RMSE = {rmse:.4f}")
    else:
        print(f"[{province_name}] Không đủ dữ liệu để tạo validation set.")

    # 7. Lưu model
    model_filename = MODELS_DIR / f"{province_name}_temp_sarimax.pkl"
    results.save(model_filename)
    print(f"[{province_name}] Đã lưu model tại: {model_filename}")

    return mae, rmse


def train_all_provinces():
    """
    Train SARIMAX nhiệt độ cho TẤT CẢ các file CSV trong thư mục ./data.
    File CSV nào không có cột nhiệt độ sẽ bị bỏ qua.
    """
    if not DATA_DIR.exists():
        print(f"Thư mục data không tồn tại: {DATA_DIR}")
        return

    csv_files = sorted(DATA_DIR.glob("*.csv"))
    if not csv_files:
        print(f"Không tìm thấy file CSV nào trong {DATA_DIR}")
        return

    summary = []

    for csv_path in csv_files:
        province_name = csv_path.stem  # ví dụ: "An_Giang" từ "An_Giang.csv"
        try:
            metrics = train_sarimax_for_province(province_name, csv_path)
            if metrics is not None:
                mae, rmse = metrics
                summary.append((province_name, mae, rmse))
        except Exception as e:
            print(f"[{province_name}] LỖI khi train: {e}")

    # In summary
    if summary:
        print("\n=== TỔNG KẾT KẾT QUẢ TRAIN NHIỆT ĐỘ (TEMP SARIMAX) ===")
        for province_name, mae, rmse in summary:
            print(f"- {province_name}: MAE={mae:.4f}, RMSE={rmse:.4f}")
    else:
        print("Không có model nào được train thành công.")


# ================== MAIN ==================

if __name__ == "__main__":
    print("Bắt đầu train mô hình SARIMAX dự báo NHIỆT ĐỘ cho tất cả tỉnh...")
    print(f"Thư mục dữ liệu:  {DATA_DIR}")
    print(f"Thư mục lưu model: {MODELS_DIR}")

    train_all_provinces()

    print("\nHoàn tất train tất cả mô hình nhiệt độ.")
