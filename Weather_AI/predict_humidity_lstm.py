import os
import sys
import django
from pathlib import Path
from django.utils import timezone as tz
from django.conf import settings
import pytz
import numpy as np
import pandas as pd
import joblib
from tensorflow.keras.models import load_model

# ============================
# CẤU HÌNH CHO DỰ ĐOÁN ĐỘ ẨM
# ============================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models_humidity"

DJANGO_PROJECT_DIR = BASE_DIR.parent
sys.path.insert(0, str(DJANGO_PROJECT_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Weather_Project_Python.settings')
django.setup()

from Weather_App.models import Location, HourlyForecast
from check_and_update_data import check_and_update_province

TARGET_COLUMN = 'relative_humidity_2m'
SEQ_LENGTH = 72  # 3 ngày dữ liệu quá khứ
PREDICT_HORIZON = 24  # Dự đoán 24 giờ tiếp theo

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


def process_humidity_features(df):
    """Tạo features giống training"""
    df = df.copy()
    time_col = df.columns[0]
    df[time_col] = pd.to_datetime(df[time_col])
    df = df.sort_values(by=time_col).reset_index(drop=True)

    df['hour'] = df[time_col].dt.hour
    df['month'] = df[time_col].dt.month
    df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
    df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
    df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)

    return df[[TARGET_COLUMN, 'hour_sin', 'hour_cos', 'month_sin', 'month_cos']]


def predict_hourly_humidity(province_name: str, steps: int = 24, force: bool = False):
    """Dự báo độ ẩm theo giờ và lưu vào DB"""
    location_name = get_location_name(province_name)
    location = Location.objects.filter(city_name__icontains=location_name).first()
    if not location:
        raise ValueError(f"Location not found: {province_name} (searched: {location_name})")
    
    if not force:
        latest = HourlyForecast.objects.filter(location=location, humidity__isnull=False).order_by('-updated_at').first()
        if latest:
            hours_since_update = (tz.now() - latest.updated_at).total_seconds() / 3600
            if hours_since_update < 1:
                return f"⏭️ {province_name}: Dự báo humidity mới (<1h), bỏ qua"
    
    check_and_update_province(province_name)
    
    model_path = MODEL_DIR / f"{province_name}.keras"
    scaler_x_path = MODEL_DIR / f"scaler_X_{province_name}.pkl"
    scaler_y_path = MODEL_DIR / f"scaler_Y_{province_name}.pkl"

    if not model_path.exists():
        raise FileNotFoundError(f"No humidity model for {province_name}")

    model = load_model(model_path, compile=False)
    scaler_X = joblib.load(scaler_x_path)
    scaler_Y = joblib.load(scaler_y_path)

    # Load và process data
    csv = DATA_DIR / f"{province_name}.csv"
    if not csv.exists():
        raise FileNotFoundError(f"No data for {province_name}")
        
    df = pd.read_csv(csv)
    df["time"] = pd.to_datetime(df["time"])
    vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    df["time"] = df["time"].dt.tz_localize('UTC').dt.tz_convert(vn_tz)
    df = df.set_index("time").sort_index().asfreq("h").ffill().bfill()
    
    df_features = process_humidity_features(df.reset_index())
    
    # Lấy SEQ_LENGTH giờ gần nhất
    recent_data = df_features.tail(SEQ_LENGTH).values
    
    # Scale
    X_scaled = scaler_X.transform(recent_data)
    y_scaled = scaler_Y.transform(recent_data[:, [0]])
    
    # Reshape cho LSTM
    x_input = X_scaled.reshape((1, SEQ_LENGTH, X_scaled.shape[1]))
    
    # Predict
    yhat_scaled = model.predict(x_input, verbose=0)[0]
    preds = scaler_Y.inverse_transform(yhat_scaled.reshape(-1, 1)).ravel()
    
    # Bắt đầu dự báo từ giờ tiếp theo
    now = tz.localtime(tz.now()) if getattr(settings, 'USE_TZ', False) else tz.now()
    next_hour = now.replace(minute=0, second=0, microsecond=0) + pd.Timedelta(hours=1)
    times = pd.date_range(start=next_hour, periods=steps, freq="h")
    
    # Dùng bulk_update để update humidity vào records đã có từ temperature prediction
    humidity_values = [round(h / 10) * 10 for h in preds]  # Làm tròn hàng chục
    
    forecasts_to_update = []
    for time, humidity in zip(times, humidity_values):
        try:
            forecast = HourlyForecast.objects.get(location=location, forecast_time=time)
            forecast.humidity = float(humidity)
            forecasts_to_update.append(forecast)
        except HourlyForecast.DoesNotExist:
            pass  # Bỏ qua nếu chưa có record (không nên xảy ra)
    
    if forecasts_to_update:
        HourlyForecast.objects.bulk_update(forecasts_to_update, ['humidity'])
    
    vn_time = (tz.localtime(tz.now()) if getattr(settings, 'USE_TZ', False) else tz.now()).strftime('%Y-%m-%d %H:%M:%S')
    return f"✅ {province_name}: Saved {steps} humidity forecasts (VN time: {vn_time})"


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        province = sys.argv[1]
        print(predict_hourly_humidity(province))
    else:
        print("Usage: python predict_humidity_lstm.py <province_name>")
        print("Example: python predict_humidity_lstm.py Ha_Noi")
