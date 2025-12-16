"""
Train mô hình SARIMA dự báo BỨC XẠ MẶT TRỜI (Solar Radiation) theo NGÀY.
(KHÔNG DÙNG BIẾN NGOẠI SINH - UNIVARIATE)
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
MODELS_DIR = BASE_DIR / "model_solar"
MODELS_DIR.mkdir(exist_ok=True)

# Số ngày validation
VALIDATION_DAYS = 30
# Cấu hình SARIMA (Không có X)
ORDER = (1, 1, 1)
SEASONAL_ORDER = (0, 0, 0, 0)

# Tên cột Target
TARGET_COL = "shortwave_radiation"

# ================== HÀM XỬ LÝ DỮ LIỆU ==================
def load_and_aggregate_daily(csv_path: Path) -> Optional[pd.DataFrame]:
    """
    Đọc CSV hourly -> Gộp thành Daily. Chỉ lấy cột Target.
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

        # 1. Chỉ lấy cột Target và resample theo ngày (Sum)
        df_daily = df[[TARGET_COL]].resample('D').sum()

        # 2. Xử lý missing data sinh ra do resample
        df_daily = df_daily.ffill().bfill()

        return df_daily

    except Exception as e:
        print(f"  [Error] Lỗi xử lý file {csv_path.name}: {e}")
        return None

# ================== HÀM TRAIN ==================
def train_radiation_model_no_exog(province_name: str, csv_path: Path):
    print(f"\nTraining (No Exog): {province_name}...")

    # 1. Load dữ liệu
    df = load_and_aggregate_daily(csv_path)
    if df is None:
        return

    if len(df) < 100:
        print("Dữ liệu quá ít, bỏ qua.")
        return

    # 2. Chia tập Train / Validation (Chỉ có Endog, không có Exog)
    endog = df[TARGET_COL].astype(float)

    if len(df) <= VALIDATION_DAYS * 2:
        train_endog = endog
        val_endog = None
    else:
        train_endog = endog.iloc[:-VALIDATION_DAYS]
        val_endog = endog.iloc[-VALIDATION_DAYS:]

    # 3. Cấu hình và Huấn luyện Fit SARIMAX (exog=None)
    try:
        model = SARIMAX(
            endog=train_endog,
            exog=None,  # <--- QUAN TRỌNG: Không dùng biến ngoại sinh
            order=ORDER,
            seasonal_order=SEASONAL_ORDER,
            enforce_stationarity=False,
            enforce_invertibility=False
        )
        results = model.fit(disp=False)

        # 4. Đánh giá Validation
        msg = ""
        if val_endog is not None:
            # Forecast không cần truyền exog
            forecast = results.get_forecast(steps=VALIDATION_DAYS, exog=None)
            pred = forecast.predicted_mean
            pred = pred.reindex(val_endog.index).fillna(0)
            pred[pred < 0] = 0

            mae = np.mean(np.abs(val_endog - pred))
            rmse = np.sqrt(np.mean((val_endog - pred) ** 2))

            msg = f" | Val MAE: {mae:.2f} Wh/m², RMSE: {rmse:.2f}"

        print(f"  -> OK. AIC: {results.aic:.1f}{msg}")

        # 5. Lưu model
        save_name = f"{province_name}_radiation_sarimax.pkl"
        results.save(MODELS_DIR / save_name)
        print(f"Đã lưu model: {save_name}")

    except Exception as e:
        print(f"Lỗi Training: {e}")

# ================== MAIN ==================

if __name__ == "__main__":
    print("=== TRAIN RADIATION MODEL (NO EXOG)===")

    csv_files = sorted(DATA_DIR.glob("*.csv"))
    if not csv_files:
        print("Không tìm thấy file CSV nào trong thư mục data/")
    else:
        for csv_path in csv_files:
            train_radiation_model_no_exog(csv_path.stem, csv_path)

    print("\nHoàn tất toàn bộ!")