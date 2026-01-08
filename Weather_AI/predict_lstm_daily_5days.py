from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from tensorflow.keras.models import load_model

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models_lstm_daily"

TARGET = "temperature_2m"
LOOKBACK = 14
HORIZON = 5


def load_recent_daily(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").sort_index()
    df = df.asfreq("h").ffill().bfill()

    daily = df.resample("D")[TARGET].agg(["max", "min"])
    daily.columns = ["temp_max", "temp_min"]
    return daily.astype(float)


def forecast_daily_maxmin(province: str) -> pd.DataFrame:
    csv_path = DATA_DIR / f"{province}.csv"
    model_path = MODEL_DIR / f"{province}_lstm_daily_maxmin.keras"
    scaler_path = MODEL_DIR / f"{province}_daily_scaler.pkl"

    if not model_path.exists():
        raise FileNotFoundError(f"No model for {province}")

    model = load_model(model_path, compile=False)
    scaler = joblib.load(scaler_path)

    daily = load_recent_daily(csv_path)
    last_day = daily.index[-1]

    values = daily.values
    scaled = scaler.transform(values)

    window = scaled[-LOOKBACK:].reshape((1, LOOKBACK, 2))

    preds_scaled = model.predict(window, verbose=0)[0]
    preds_scaled = preds_scaled.reshape((HORIZON, 2))

    preds = scaler.inverse_transform(preds_scaled)

    days = pd.date_range(start=last_day + pd.Timedelta(days=1),
                         periods=HORIZON, freq="D")

    return pd.DataFrame({
        "date": days,
        "temp_max_forecast": preds[:, 0],
        "temp_min_forecast": preds[:, 1],
    })


if __name__ == "__main__":
    df = forecast_daily_maxmin("Ca_Mau")
    print(df)
    df.to_csv("result_demo/result_lstm_daily_maxmin_Ca_Mau.csv", index=False)
