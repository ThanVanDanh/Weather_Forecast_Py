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


def load_recent_daily(province: str, days: int = 120) -> pd.DataFrame:
    csv_path = DATA_DIR / f"{province}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"No data for {province}")

    df = pd.read_csv(csv_path)
    df["time"] = pd.to_datetime(df["time"])
    #convert UTC to Asia/Ho_Chi_Minh
    import pytz
    vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    df["time"] = df["time"].dt.tz_localize('UTC').dt.tz_convert(vn_tz)
    df = df.set_index("time").sort_index()
    
    df = df[(df[TARGET] >= -10) & (df[TARGET] <= 50)]
    df = df.asfreq("h").interpolate(method='time', limit=3).bfill().ffill()

    daily = df.resample("D")[TARGET].agg(
        temp_min="min",
        temp_max="max",
        temp_mean="mean",
        temp_std="std"
    )
    
    #temp_std >= 8 -> loai
    daily = daily[daily["temp_std"] < 8]
    
    # Đảm bảo min < max
    daily = daily[daily["temp_min"] < daily["temp_max"]]

    return daily.iloc[-days:]


def forecast_one_target(province: str, target: str, history: pd.Series, steps: int = 5):
    model_path = MODEL_DIR / f"{province}_{target}_daily.pkl"
    if not model_path.exists():
        raise FileNotFoundError(f"No daily model {target} for {province}")

    payload = joblib.load(model_path)
    history = history.dropna()
    
    if len(history) < 30:
        raise ValueError(f"Không đủ dữ liệu lịch sử: chỉ có {len(history)} ngày")

    model = SARIMAX(
        history,
        order=payload["order"],
        seasonal_order=payload["seasonal_order"],
        enforce_stationarity=False,
        enforce_invertibility=False
    )

    results = model.filter(payload["params"])
    fc = results.get_forecast(steps=steps)
    predictions = fc.predicted_mean
    
    #post-processing: Smooth predictions với moving average
    #tránh các bước nhảy đột ngột
    if steps >= 3:
        smoothed = predictions.rolling(window=2, min_periods=1).mean()
    else:
        smoothed = predictions
    
    #giới hạn biến động tối đa 5°C mỗi ngày
    for i in range(1, len(smoothed)):
        diff = smoothed.iloc[i] - smoothed.iloc[i-1]
        if abs(diff) > 5:
            smoothed.iloc[i] = smoothed.iloc[i-1] + (5 if diff > 0 else -5)
    
    #nhiệt độ VN 0-45°C
    smoothed = smoothed.clip(lower=0, upper=45)
    
    return smoothed


def predict_daily_temperature(province_name: str, steps: int = 5, force: bool = False):
    location_name = get_location_name(province_name)
    location = Location.objects.filter(city_name__icontains=location_name).first()
    if not location:
        raise ValueError(f"Location not found: {province_name} (searched: {location_name})")
    
    if not force:
        latest = DailyForecast.objects.filter(location=location).order_by('-updated_at').first()
        if latest:
            hours_since_update = (tz.now() - latest.updated_at).total_seconds() / 3600
            if hours_since_update < 24:
                return f"{province_name}: Dự báo mới (<24h), bỏ qua"
    
    check_and_update_province(province_name)
    
    daily = load_recent_daily(province_name)
    
    if len(daily) < 30:
        raise ValueError(f"{province_name}: Không đủ dữ liệu (chỉ có {len(daily)} ngày)")

    min_pred = forecast_one_target(province_name, "min", daily["temp_min"], steps)
    max_pred = forecast_one_target(province_name, "max", daily["temp_max"], steps)
    
    #min < max cho mỗi ngày
    for i in range(len(min_pred)):
        if min_pred.iloc[i] >= max_pred.iloc[i]:
            avg = (min_pred.iloc[i] + max_pred.iloc[i]) / 2
            min_pred.iloc[i] = avg - 2
            max_pred.iloc[i] = avg + 2

    #dự báo ngày mai
    today = (tz.localtime(tz.now()) if getattr(settings, 'USE_TZ', False) else tz.now()).date()
    tomorrow = today + pd.Timedelta(days=1)
    idx = pd.date_range(start=tomorrow, periods=steps, freq="D")

    #xóa dự báo cũ
    DailyForecast.objects.filter(
        location=location,
        forecast_date__gte=tomorrow
    ).delete()
    
    #bulk create
    forecasts = [
        DailyForecast(
            location=location,
            forecast_date=date.date(),
            temp_min=round(float(temp_min), 1),  # Làm tròn 1 chữ số
            temp_max=round(float(temp_max), 1)
        )
        for date, temp_min, temp_max in zip(idx, min_pred.values, max_pred.values)
    ]
    DailyForecast.objects.bulk_create(forecasts)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        province = sys.argv[1]
        print(predict_daily_temperature(province))
    else:
        print("Usage: python predict_daily_5days_sarima.py <province_name>")
        print("Example: python predict_daily_5days_sarima.py Ha_Noi")

