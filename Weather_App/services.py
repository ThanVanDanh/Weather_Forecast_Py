import requests
from django.conf import settings
from django.utils import timezone
from django.db.models import Max
import sys
from pathlib import Path


# Mapping tên Location trong DB → tên file CSV/model
PROVINCE_NAME_MAPPING = {
    'Ho Chi Minh City': 'TP_Ho_Chi_Minh',
    'Hanoi': 'Ha_Noi',
    'Da Nang': 'Da_Nang',
    'Can Tho': 'Can_Tho',
    'Hai Phong': 'Hai_Phong',
    'Hue': 'Hue',
    # Thêm các mapping khác nếu cần
}


def get_province_name(location):
    """Convert location city_name sang tên province dùng trong AI scripts"""
    city_name = location.city_name
    
    # Kiểm tra mapping trước
    if city_name in PROVINCE_NAME_MAPPING:
        return PROVINCE_NAME_MAPPING[city_name]
    
    # Mặc định: replace space với underscore
    return city_name.replace(' ', '_')


class MeteoAPIService:

    def __init__(self, lat, lon):
        self.lat = lat
        self.lon = lon
        self.base_url = "https://api.open-meteo.com/v1/forecast"

    def fetch_current_weather(self):
    #get data hien tai
        params = {
            'latitude': self.lat,
            'longitude': self.lon,
            'timezone': 'Asia/Ho_Chi_Minh',

            'current_weather': 'true',

            'daily': 'weathercode,temperature_2m_max,temperature_2m_min,uv_index_max,sunrise,sunset',

            'hourly': 'temperature_2m,apparent_temperature,relativehumidity_2m,pressure_msl,visibility',

            'forecast_days': 1
        }

        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            print(f"Lỗi gọi API Meteo: {e}")
            return None


class ForecastService:
    """Service để quản lý dự báo AI on-demand"""
    
    @staticmethod
    def get_or_predict_hourly(location):
        """Lấy hoặc tạo dự báo 24h cho location"""
        from .models import HourlyForecast
        
        # Tính giờ tiếp theo (bắt đầu dự báo)
        now = timezone.now()
        next_hour = now.replace(minute=0, second=0, microsecond=0) + timezone.timedelta(hours=1)
        
        # Kiểm tra forecast đầu tiên
        first_forecast = HourlyForecast.objects.filter(location=location).order_by('forecast_time').first()
        
        should_predict = False
        
        if first_forecast is None:
            # Chưa có forecast
            should_predict = True
        else:
            # Kiểm tra xem forecast_time đầu tiên có phải là giờ tiếp theo không
            if first_forecast.forecast_time != next_hour:
                should_predict = True
                print(f"[DEBUG] First forecast time {first_forecast.forecast_time} != next hour {next_hour}")
            else:
                # Kiểm tra updated_at có quá cũ không (>1h)
                hours_since_update = (now - first_forecast.updated_at).total_seconds() / 3600
                if hours_since_update > 1:
                    should_predict = True
                    print(f"[DEBUG] Updated {hours_since_update:.1f}h ago, re-predicting")
        
        if should_predict:
            # Import predict functions
            ai_dir = Path(__file__).resolve().parent.parent / 'Weather_AI'
            sys.path.insert(0, str(ai_dir))
            from Weather_AI.predict_lstm_hourly_24h import predict_hourly_temperature
            from Weather_AI.predict_humidity_lstm import predict_hourly_humidity
            from django.db import transaction
            import time
            
            province_name = get_province_name(location)
            
            # Retry logic để xử lý database locked
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    # BƯỚC 1: Predict temperature (transaction riêng)
                    with transaction.atomic():
                        # Xóa dữ liệu cũ
                        HourlyForecast.objects.filter(location=location).delete()
                        
                        # Predict temperature
                        result_temp = predict_hourly_temperature(province_name, steps=24, force=True)
                        print(f"✅ Temperature: {result_temp}")
                    
                    # BƯỚC 2: Predict humidity (transaction riêng, không làm mất temperature nếu fail)
                    try:
                        with transaction.atomic():
                            result_hum = predict_hourly_humidity(province_name, steps=24, force=True)
                            print(f"✅ Humidity: {result_hum}")
                    except Exception as e:
                        print(f"⚠️ Warning: Humidity prediction failed (temperature saved): {e}")
                    
                    break  # Thành công, thoát loop
                    
                except Exception as e:
                    if 'database is locked' in str(e) and attempt < max_retries - 1:
                        wait_time = (attempt + 1)  # Đợi 1s, 2s, 3s, 4s, 5s
                        print(f"Database locked, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                    else:
                        print(f"❌ Error predicting hourly: {e}")
                        return []
        
        # Trả về forecasts
        return HourlyForecast.objects.filter(location=location).order_by('forecast_time')
    
    @staticmethod
    def get_or_predict_daily(location):
        """Lấy hoặc tạo dự báo 5 ngày cho location"""
        from .models import DailyForecast
        from datetime import timedelta
        
        # Lấy forecast hiện có
        forecasts = DailyForecast.objects.filter(location=location).order_by('forecast_date')
        
        # Kiểm tra xem có cần predict lại không
        should_predict = False
        
        if not forecasts.exists():
            # Chưa có dữ liệu → predict
            should_predict = True
        else:
            # Kiểm tra updated_at
            latest = forecasts.aggregate(Max('updated_at'))['updated_at__max']
            if (timezone.now() - latest).total_seconds() > 86400:
                # Quá 24h → predict lại
                should_predict = True
            else:
                # Kiểm tra xem ngày dự báo có đúng không (phải bắt đầu từ ngày mai)
                tomorrow = timezone.localtime().date() + timedelta(days=1)
                first_forecast = forecasts.first()
                if first_forecast.forecast_date != tomorrow:
                    # Ngày dự báo sai → predict lại
                    should_predict = True
                    print(f"[INFO] Forecast dates incorrect. Expected {tomorrow}, got {first_forecast.forecast_date}")
        
        if should_predict:
            # Xóa dữ liệu cũ
            DailyForecast.objects.filter(location=location).delete()
            
            # Gọi predict function
            province_name = get_province_name(location)
            try:
                # Import predict function
                ai_dir = Path(__file__).resolve().parent.parent / 'Weather_AI'
                sys.path.insert(0, str(ai_dir))
                from Weather_AI.predict_daily_5days_sarima import predict_daily_temperature
                
                result = predict_daily_temperature(province_name, steps=5, force=True)
                print(f"Daily prediction: {result}")
            except Exception as e:
                print(f"Error predicting daily: {e}")
                return []
        
        # Trả về forecasts
        return DailyForecast.objects.filter(location=location).order_by('forecast_date')
