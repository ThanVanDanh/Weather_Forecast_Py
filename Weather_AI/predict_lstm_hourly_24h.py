import os
import sys
import django
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from tensorflow.keras.models import load_model

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models_lstm_hourly"

DJANGO_PROJECT_DIR = BASE_DIR.parent
sys.path.insert(0, str(DJANGO_PROJECT_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Weather_Project_Python.settings')
django.setup()

from Weather_App.models import Location, HourlyForecast

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


def predict_hourly_temperature(province_name: str, steps: int = 24):
    """Dự báo nhiệt độ theo giờ và lưu vào DB"""
    model_path = MODEL_DIR / f"{province_name}_hourly.keras"
    scaler_path = MODEL_DIR / f"{province_name}_scaler.pkl"

    if not model_path.exists():
        raise FileNotFoundError(f"No model for {province_name}")

    model = load_model(model_path, compile=False)
    scaler = joblib.load(scaler_path)

    series = load_recent_series(province_name)
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
    times = pd.date_range(start=last_time + pd.Timedelta(hours=1), periods=steps, freq="h")

    location = Location.objects.filter(city_name__icontains=province_name.replace('_', ' ')).first()
    if not location:
        raise ValueError(f"Location not found: {province_name}")

    for time, temp in zip(times, preds):
        HourlyForecast.objects.update_or_create(
            location=location,
            forecast_time=time,
            defaults={'temperature': float(temp)}
        )
    
    return f"✅ {province_name}: Saved {steps} hourly forecasts"


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        province = sys.argv[1]
        print(predict_hourly_temperature(province))
    else:
        print("Usage: python predict_lstm_hourly_24h.py <province_name>")
        print("Example: python predict_lstm_hourly_24h.py Ca_Mau")

