import os
import sys
import django
from pathlib import Path
from datetime import datetime
from django.utils import timezone as tz
from django.conf import settings
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
from check_and_update_data import check_and_update_province

TARGET = "temperature_2m"

# Mapping tên file/province → tên Location trong DB
PROVINCE_TO_LOCATION = {
    'TP_Ho_Chi_Minh': 'Ho Chi Minh City',
    'Ha_Noi': 'Hanoi',
    'Da_Nang': 'Da Nang',
    'Can_Tho': 'Can Tho',
    'Hai_Phong': 'Hai Phong',
}


def get_location_name(province_name):
    """Convert tên province sang tên location trong DB"""
    if province_name in PROVINCE_TO_LOCATION:
        return PROVINCE_TO_LOCATION[province_name]
    return province_name.replace('_', ' ')


def load_recent_daily(province: str, days: int = 30) -> pd.DataFrame:
    csv_path = DATA_DIR / f"{province}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"No data for {province}")

    df = pd.read_csv(csv_path)
    df["time"] = pd.to_datetime(df["time"])
    # Convert UTC to Asia/Ho_Chi_Minh
    import pytz
    vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    df["time"] = df["time"].dt.tz_localize('UTC').dt.tz_convert(vn_tz)
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


def predict_daily_temperature(province_name: str, steps: int = 5, force: bool = False):
    """Dự báo nhiệt độ min/max theo ngày và lưu vào DB"""
    location_name = get_location_name(province_name)
    location = Location.objects.filter(city_name__icontains=location_name).first()
    if not location:
        raise ValueError(f"Location not found: {province_name} (searched: {location_name})")
    
    if not force:
        latest = DailyForecast.objects.filter(location=location).order_by('-updated_at').first()
        if latest:
            hours_since_update = (tz.now() - latest.updated_at).total_seconds() / 3600
            if hours_since_update < 24:
                return f"⏭️ {province_name}: Dự báo mới (<24h), bỏ qua"
    
    check_and_update_province(province_name)
    
    daily = load_recent_daily(province_name)

    min_pred = forecast_one_target(province_name, "min", daily["temp_min"], steps)
    max_pred = forecast_one_target(province_name, "max", daily["temp_max"], steps)

    # Dự báo từ NGÀY MAI (không phụ thuộc vào ngày cuối trong CSV)
    today = (tz.localtime(tz.now()) if getattr(settings, 'USE_TZ', False) else tz.now()).date()
    tomorrow = today + pd.Timedelta(days=1)
    idx = pd.date_range(start=tomorrow, periods=steps, freq="D")

    # Dùng bulk_create thay vì update_or_create để nhanh hơn
    forecasts = [
        DailyForecast(
            location=location,
            forecast_date=date.date(),
            temp_min=float(temp_min),
            temp_max=float(temp_max)
        )
        for date, temp_min, temp_max in zip(idx, min_pred.values, max_pred.values)
    ]
    DailyForecast.objects.bulk_create(forecasts)
    
    # Hiển thị thời gian VN (không phải UTC)
    vn_time = (tz.localtime(tz.now()) if getattr(settings, 'USE_TZ', False) else tz.now()).strftime('%Y-%m-%d %H:%M:%S')
    return f" {province_name}: Saved {steps} daily forecasts (VN time: {vn_time})"


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        province = sys.argv[1]
        print(predict_daily_temperature(province))
    else:
        print("Usage: python predict_daily_5days_sarima.py <province_name>")
        print("Example: python predict_daily_5days_sarima.py Ha_Noi")

