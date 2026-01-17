import os
import sys
import django
from pathlib import Path
import pandas as pd
import joblib
from statsmodels.tsa.statespace.sarimax import SARIMAX

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models_daily_sarima"

DJANGO_PROJECT_DIR = BASE_DIR.parent
sys.path.insert(0, str(DJANGO_PROJECT_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Weather_Project_Python.settings')
django.setup()

from Weather_App.models import Location, DailyForecast

TARGET = "temperature_2m"


def load_recent_daily(province: str, days: int = 30) -> pd.DataFrame:
    csv_path = DATA_DIR / f"{province}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"No data for {province}")

    df = pd.read_csv(csv_path)
    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").sort_index()
    df = df.asfreq("h").ffill().bfill()

    daily = df.resample("D")[TARGET].agg(
        temp_min="min",
        temp_max="max",
        temp_mean="mean"
    )

    return daily.iloc[-days:]


def forecast_one_target(province: str, target: str, history: pd.Series, steps: int = 5):
    model_path = MODEL_DIR / f"{province}_{target}_daily.pkl"
    if not model_path.exists():
        raise FileNotFoundError(f"No daily model {target} for {province}")

    payload = joblib.load(model_path)

    model = SARIMAX(
        history,
        order=payload["order"],
        seasonal_order=payload["seasonal_order"],
        enforce_stationarity=False,
        enforce_invertibility=False
    )

    results = model.filter(payload["params"])
    fc = results.get_forecast(steps=steps)
    return fc.predicted_mean


def predict_daily_temperature(province_name: str, steps: int = 5):
    """Dự báo nhiệt độ min/max theo ngày và lưu vào DB"""
    daily = load_recent_daily(province_name)

    min_pred = forecast_one_target(province_name, "min", daily["temp_min"], steps)
    max_pred = forecast_one_target(province_name, "max", daily["temp_max"], steps)

    start = daily.index[-1] + pd.Timedelta(days=1)
    idx = pd.date_range(start=start, periods=steps, freq="D")

    location = Location.objects.filter(city_name__icontains=province_name.replace('_', ' ')).first()
    if not location:
        raise ValueError(f"Location not found: {province_name}")

    for date, temp_min, temp_max in zip(idx, min_pred.values, max_pred.values):
        DailyForecast.objects.update_or_create(
            location=location,
            forecast_date=date.date(),
            defaults={'temp_min': float(temp_min), 'temp_max': float(temp_max)}
        )
    
    return f"✅ {province_name}: Saved {steps} daily forecasts"


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        province = sys.argv[1]
        print(predict_daily_temperature(province))
    else:
        print("Usage: python predict_daily_5days_sarima.py <province_name>")
        print("Example: python predict_daily_5days_sarima.py Ha_Noi")

