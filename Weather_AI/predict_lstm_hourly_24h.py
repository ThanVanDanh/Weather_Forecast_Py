# predict_lstm_hourly_24h.py
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from tensorflow.keras.models import load_model

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models_lstm_hourly"

TARGET = "temperature_2m"
LOOKBACK = 48


def load_recent_series(province: str) -> pd.Series:
    csv = DATA_DIR / f"{province}.csv"
    if not csv.exists():
        raise FileNotFoundError(f"No data for {province}")

    df = pd.read_csv(csv)
    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").sort_index()
    df = df.asfreq("h").ffill().bfill()

    return df[TARGET].astype(float)


def forecast_24h(province: str, steps: int = 24) -> pd.DataFrame:
    model_path = MODEL_DIR / f"{province}_hourly.keras"
    scaler_path = MODEL_DIR / f"{province}_scaler.pkl"

    if not model_path.exists():
        raise FileNotFoundError(f"No model for {province}")

    model = load_model(model_path, compile=False)
    scaler = joblib.load(scaler_path)

    series = load_recent_series(province)
    last_time = series.index[-1]

    values = series.values.reshape(-1, 1)
    scaled = scaler.transform(values)

    window = scaled[-LOOKBACK:].copy()

    preds = []
    for _ in range(steps):
        x = window.reshape((1, LOOKBACK, 1))
        yhat = model.predict(x, verbose=0)[0, 0]
        preds.append(yhat)

        window = np.vstack([window[1:], [[yhat]]])

    preds = scaler.inverse_transform(np.array(preds).reshape(-1, 1)).ravel()

    times = pd.date_range(start=last_time + pd.Timedelta(hours=1),
                          periods=steps, freq="h")

    return pd.DataFrame({
        "time": times,
        "temperature_forecast": preds
    })


if __name__ == "__main__":
    df = forecast_24h("An_Giang", steps=24)
    print(df)
    df.to_csv("result_demo/result_lstm_hourly_An_Giang.csv", index=False)
