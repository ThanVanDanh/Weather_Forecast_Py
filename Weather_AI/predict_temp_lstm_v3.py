"""
Dự báo nhiệt độ 120 giờ tiếp theo bằng LSTM v3 (univariate, multi-step).

- Input: 168 giờ nhiệt độ gần nhất từ data/{province}.csv
- Output: 120 giờ tương lai
- Model: models_lstm_v3/{province}_lstm_v3.keras
- Scaler: models_lstm_v3/{province}_scaler_v3.pkl
"""

from pathlib import Path
import numpy as np
import pandas as pd
import joblib

from tensorflow.keras.models import load_model


# =====================
# CONFIG
# =====================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models_lstm_v3"
OUT_DIR = BASE_DIR / "result_demo"
OUT_DIR.mkdir(exist_ok=True)

TARGET = "temperature_2m"

LOOKBACK = 168   # phải khớp lúc train
HORIZON = 120


# =====================
# LOAD SERIES
# =====================

def load_series(csv_path: Path) -> pd.Series:
    df = pd.read_csv(csv_path)

    if "time" not in df.columns or TARGET not in df.columns:
        raise ValueError("CSV thiếu cột 'time' hoặc target!")

    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").sort_index()
    df = df.asfreq("h").ffill().bfill()

    return df[TARGET]


# =====================
# FORECAST
# =====================

def forecast_lstm_v3_temperature(province: str, steps: int = HORIZON) -> pd.DataFrame:

    csv_path = DATA_DIR / f"{province}.csv"
    model_path = MODEL_DIR / f"{province}_lstm_v3.keras"
    scaler_path = MODEL_DIR / f"{province}_scaler_v3.pkl"

    if not csv_path.exists():
        raise FileNotFoundError(f"Không tìm thấy data: {csv_path}")
    if not model_path.exists():
        raise FileNotFoundError(f"Không tìm thấy model: {model_path}")
    if not scaler_path.exists():
        raise FileNotFoundError(f"Không tìm thấy scaler: {scaler_path}")

    # Load data
    series = load_series(csv_path)

    if len(series) < LOOKBACK:
        raise ValueError("Không đủ dữ liệu lịch sử cho LOOKBACK")

    history = series.iloc[-LOOKBACK:].values.reshape(-1, 1)

    # Load scaler + model
    scaler = joblib.load(scaler_path)
    model = load_model(model_path)

    # Scale input
    history_scaled = scaler.transform(history)

    X_input = history_scaled.reshape(1, LOOKBACK, 1)

    # Predict -> (1, 120)
    y_scaled = model.predict(X_input, verbose=0)[0]

    # Inverse scale
    y_scaled = y_scaled.reshape(-1, 1)
    y_pred = scaler.inverse_transform(y_scaled).ravel()

    # Build time index
    last_time = series.index[-1]
    future_times = pd.date_range(
        start=last_time + pd.Timedelta(hours=1),
        periods=steps,
        freq="h"
    )

    df_forecast = pd.DataFrame({
        "time": future_times,
        "temperature_lstm_v3": y_pred[:steps]
    })

    return df_forecast


# =====================
# MAIN
# =====================

if __name__ == "__main__":

    province = "An_Giang"   # đổi tỉnh ở đây
    steps = 120

    print(f"🔮 Forecast LSTM v3 for {province} – next {steps} hours")

    df = forecast_lstm_v3_temperature(province, steps=steps)

    out_path = OUT_DIR / f"{province}_LSTM_v3.csv"
    df.to_csv(out_path, index=False)

    print(df.head())
    print(f"\n✔ Saved to {out_path}")
