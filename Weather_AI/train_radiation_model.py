"""
Train mô hình SARIMAX dự báo BỨC XẠ MẶT TRỜI (Solar Radiation) theo NGÀY.
- Input: Dữ liệu Hourly từ data/
- Process: Resample sang Daily.
- Target: shortwave_radiation (Sum - Tổng năng lượng ngày)
- Exog (Biến ngoại sinh):
    1. cloudcover (Mean) - Mây
    2. precipitation/rain (Sum) - Mưa
    3. relative_humidity_2m (Mean) - Độ ẩm
    4. dewpoint_2m (Mean) - Điểm sương
    5. temperature_2m (Mean/Max) - Nhiệt độ
    6. direct/diffuse radiation (Sum) - Thành phần bức xạ (nếu có để train)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

# ================== CẤU HÌNH ==================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(exist_ok=True)

# Số ngày validation
VALIDATION_DAYS = 30
# Cấu hình SARIMAX
ORDER = (1, 1, 1)
SEASONAL_ORDER = (0, 0, 0, 0)
# Tên cột Target
TARGET_COL = "shortwave_radiation"
# Key: Tên cột trong CSV, Value:gộp theo ngày ('sum', 'mean', 'max')
EXOG_CONFIG = {
    "cloudcover": "mean",
    "cloudcover_low": "mean",
    "cloudcover_mid": "mean",
    "cloudcover_high": "mean",
    "precipitation": "sum",
    "rain": "sum",
    "relative_humidity_2m": "mean",  # Độ ẩm ảnh hưởng tán xạ
    "dewpoint_2m": "mean",  # Điểm sương
    "temperature_2m": "mean",  # Nhiệt độ (quan hệ với chu kỳ nắng)
    "direct_radiation": "sum",  # Bức xạ trực tiếp
    "diffuse_radiation": "sum",  # Bức xạ tán xạ
    "weathercode": "max"  # Mã thời tiết
}

# ================== HÀM XỬ LÝ DỮ LIỆU ==================
def load_and_aggregate_daily(csv_path: Path) -> Optional[Tuple[pd.DataFrame, List[str]]]:
    """
    Đọc CSV hourly -> Gộp thành Daily theo quy tắc trong EXOG_CONFIG.
    Trả về: (DataFrame Daily, Danh sách cột Exog tìm thấy)
    """
    try:
        df = pd.read_csv(csv_path)
        if "time" not in df.columns:
            return None

        df["time"] = pd.to_datetime(df["time"])
        df = df.set_index("time").sort_index()

        if TARGET_COL not in df.columns:
            print(f"  [Warn] File {csv_path.name} thiếu cột target {TARGET_COL}")
            return None

        # 1. Xây dựng dictionary cho hàm agg()
        # Target luôn là sum (tổng năng lượng)
        agg_dict = {TARGET_COL: 'sum'}

        found_exog = []

        # Quét xem file CSV có những cột nào trong cấu hình EXOG_CONFIG
        for col_name, agg_method in EXOG_CONFIG.items():
            if col_name in df.columns:
                agg_dict[col_name] = agg_method
                found_exog.append(col_name)

        # 2. Resample sang Daily
        df_daily = df.resample('D').agg(agg_dict)

        # 3. Xử lý missing data sinh ra do resample
        df_daily = df_daily.ffill().bfill()

        return df_daily, found_exog

    except Exception as e:
        print(f"  [Error] Lỗi xử lý file {csv_path.name}: {e}")
        return None, []

# ================== HÀM TRAIN ==================
def train_radiation_model_3(province_name: str, csv_path: Path):
    print(f"\n☀️  [Model 3] Training: {province_name}...")

    # 1. Load và Kiểm tra dữ liệu đầu vào
    result = load_and_aggregate_daily(csv_path)
    if result is None:
        return
    df, exog_cols = result

    if len(df) < 100:
        print("  -> Dữ liệu quá ít, bỏ qua.")
        return

    print(f"  -> Các biến ngoại sinh sử dụng: {', '.join(exog_cols)}")

    # 2. Chia tập Train / Validation
    endog = df[TARGET_COL].astype(float)
    exog = df[exog_cols].astype(float) if exog_cols else None

    if len(df) <= VALIDATION_DAYS * 2:
        train_endog = endog
        train_exog = exog
        val_endog = None
        val_exog = None
    else:
        train_endog = endog.iloc[:-VALIDATION_DAYS]
        train_exog = exog.iloc[:-VALIDATION_DAYS] if exog is not None else None

        val_endog = endog.iloc[-VALIDATION_DAYS:]
        val_exog = exog.iloc[-VALIDATION_DAYS:] if exog is not None else None

    # 3. Fit SARIMAX
    try:
        model = SARIMAX(
            endog=train_endog,
            exog=train_exog,
            order=ORDER,
            seasonal_order=SEASONAL_ORDER,
            enforce_stationarity=False,
            enforce_invertibility=False
        )
        results = model.fit(disp=False)

        # 4. Đánh giá Validation
        msg = ""
        if val_endog is not None:
            forecast = results.get_forecast(steps=VALIDATION_DAYS, exog=val_exog)
            pred = forecast.predicted_mean
            pred = pred.reindex(val_endog.index).fillna(0)
            pred[pred < 0] = 0  # Bức xạ không thể âm

            mae = np.mean(np.abs(val_endog - pred))
            # RMSE cho bức xạ thường khá lớn vì giá trị hàng nghìn Wh/m2
            rmse = np.sqrt(np.mean((val_endog - pred) ** 2))

            msg = f" | Val MAE: {mae:.2f} Wh/m², RMSE: {rmse:.2f}"

        print(f"  -> OK. AIC: {results.aic:.1f}{msg}")

        # 5. Lưu model
        save_name = f"{province_name}_radiation_sarimax.pkl"
        results.save(MODELS_DIR / save_name)
        print(f"  -> Đã lưu model: {save_name}")

    except Exception as e:
        print(f"  -> Lỗi Training: {e}")

# ================== MAIN ==================

if __name__ == "__main__":
    print("=== TRAIN RADIATION MODEL (DAILY SUM)===")

    csv_files = sorted(DATA_DIR.glob("*.csv"))
    if not csv_files:
        print("Không tìm thấy file CSV nào trong thư mục data/")
    else:
        for csv_path in csv_files:
            train_radiation_model_3(csv_path.stem, csv_path)

    print("\nHoàn tất toàn bộ!")