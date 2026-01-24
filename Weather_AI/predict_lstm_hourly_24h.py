import os
import sys
import django
from pathlib import Path
from datetime import datetime
from django.utils import timezone as tz
from django.conf import settings
import pytz
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
from check_and_update_data import check_and_update_province

TARGET = "temperature_2m"
LOOKBACK = 48

# Mapping tên file/province → tên Location trong DB
PROVINCE_TO_LOCATION = {
    'TP_Ho_Chi_Minh': 'Ho Chi Minh City',
    'Ha_Noi': 'Ha Noi',
    'Da_Nang': 'Da Nang',
    'Can_Tho': 'Can Tho',
    'Hai_Phong': 'Hai Phong',
}


def get_location_name(province_name):
    """Convert tên province sang tên location trong DB"""
    if province_name in PROVINCE_TO_LOCATION:
        return PROVINCE_TO_LOCATION[province_name]
    return province_name.replace('_', ' ')


def load_recent_series(province: str) -> pd.Series:
    csv = DATA_DIR / f"{province}.csv"
    if not csv.exists():
        raise FileNotFoundError(f"No data for {province}")

    df = pd.read_csv(csv)
    df["time"] = pd.to_datetime(df["time"])
    # Convert UTC to Asia/Ho_Chi_Minh
    vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    df["time"] = df["time"].dt.tz_localize('UTC').dt.tz_convert(vn_tz)
    df = df.set_index("time").sort_index()
    df = df.asfreq("h").ffill().bfill()

    return df[TARGET].astype(float)


def predict_hourly_temperature(province_name: str, steps: int = 24, force: bool = False):
    location_name = get_location_name(province_name)
    location = Location.objects.filter(city_name__icontains=location_name).first()
    if not location:
        raise ValueError(f"Location not found: {province_name} (searched: {location_name})")
    
    if not force:
        latest = HourlyForecast.objects.filter(location=location).order_by('-updated_at').first()
        if latest:
            hours_since_update = (tz.now() - latest.updated_at).total_seconds() / 3600
            if hours_since_update < 1:
                return f"{province_name}: Dự báo mới (<1h), bỏ qua"
    
    check_and_update_province(province_name)
    
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
    
    #dự báo từ giờ tiếp theo
    now = tz.localtime(tz.now()) if getattr(settings, 'USE_TZ', False) else tz.now()
    next_hour = now.replace(minute=0, second=0, microsecond=0) + pd.Timedelta(hours=1)
    times = pd.date_range(start=next_hour, periods=steps, freq="h")

    #bulk_create
    forecasts = [
        HourlyForecast(
            location=location,
            forecast_time=time,
            temperature=float(temp)
        )
        for time, temp in zip(times, preds)
    ]
    HourlyForecast.objects.bulk_create(forecasts)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        province = sys.argv[1]
        print(predict_hourly_temperature(province))
    else:
        print("Usage: python predict_lstm_hourly_24h.py <province_name>")
        print("Example: python predict_lstm_hourly_24h.py Ca_Mau")

