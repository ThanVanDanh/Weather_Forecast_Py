"""
PREDICT TEMPERATURE USING LSTM v2 (HOURLY)
========================================

✔ Model: Bidirectional LSTM v2
✔ Window: 72 giờ
✔ Forecast: N giờ (vd: 120h)
✔ Input CSV: ./data/{province}.csv
✔ Output: DataFrame (time, temperature_forecast)
"""

from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from tensorflow.keras.models import load_model


# =========================
# PATH CONFIG
# =========================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models_lstm"

TARGET = "temperature_2m"
WINDOW_SIZE = 72


# =========================
# LOAD HISTORY
# =========================
def load_recent_history(province: str, hours: int) -> np.ndarray:
    csv_path = DATA_DIR / f"{province}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Không tìm thấy CSV cho {province}")

    df = pd.read_csv(csv_path)

    if TARGET not in df.columns:
        raise ValueError(f"{province} thiếu cột {TARGET}")

    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").sort_index()
    df = df.asfreq("h")
    df = df.ffill().bfill()

    series = df[TARGET].astype(float).values

    if len(series) < hours:
        raise ValueError("Không đủ dữ liệu lịch sử cho window")

    return series[-hours:], df.index.max()


# =========================
# FORECAST FUNCTION
# =========================
def forecast_lstm_v2_temperature(province: str, steps: int = 120) -> pd.DataFrame:
    model_path = MODEL_DIR / f"{province}_lstm_temp.h5"
    scaler_path = MODEL_DIR / f"{province}_scaler.pkl"

    if not model_path.exists():
        raise FileNotFoundError(f"Không có model LSTM cho {province}")
    if not scaler_path.exists():
        raise FileNotFoundError(f"Không có scaler cho {province}")

    # Load model & scaler
    model = load_model(model_path, compile=False)
    scaler = joblib.load(scaler_path)

    # Load last WINDOW_SIZE hours
    history, last_time = load_recent_history(province, WINDOW_SIZE)

    # Scale history
    history_scaled = scaler.transform(history.reshape(-1, 1))

    window = history_scaled.copy()
    preds_scaled = []

    # Rolling forecast
    for _ in range(steps):
        X = window.reshape(1, WINDOW_SIZE, 1)
        yhat = model.predict(X, verbose=0)[0, 0]

        preds_scaled.append(yhat)
        window = np.vstack([window[1:], [[yhat]]])

    # Inverse scale to real temperature
    preds = scaler.inverse_transform(
        np.array(preds_scaled).reshape(-1, 1)
    ).flatten()

    # Build future time index
    future_index = pd.date_range(
        start=last_time + pd.Timedelta(hours=1),
        periods=steps,
        freq="h"
    )

    df_forecast = pd.DataFrame({
        "time": future_index,
        "temperature_forecast": preds
    })

    return df_forecast


# =========================
# TEST
# =========================
if __name__ == "__main__":
    province = "An_Giang"
    steps = 120

    df = forecast_lstm_v2_temperature(province, steps)
    df.to_csv("result_demo/CaMau_LSTM.csv", index=False)
