import requests
from django.conf import settings
from django.utils import timezone
from django.db.models import Max
from django.db import transaction
from datetime import datetime, time, timedelta, timezone as dt_timezone
import subprocess
import sys
from pathlib import Path


PROVINCE_NAME_MAPPING = {
    'Ho Chi Minh City': 'TP_Ho_Chi_Minh',
    'Hanoi': 'Ha_Noi',
    'Da Nang': 'Da_Nang',
    'Can Tho': 'Can_Tho',
    'Hai Phong': 'Hai_Phong',
    'Hue': 'Hue',
}


def solar_model_path(province_name: str) -> Path:
    base_dir = Path(__file__).resolve().parent.parent
    return base_dir / 'Weather_AI' / 'models_solar_multi_provinces' / f'{province_name}.keras'


def is_solar_supported(province_name: str) -> bool:
    return solar_model_path(province_name).exists()


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
        from .models import HourlyForecast

        now = timezone.now()
        next_hour = now.replace(minute=0, second=0, microsecond=0) + timezone.timedelta(hours=1)
        
        #kiểm tra forecast đầu tiên
        first_forecast = HourlyForecast.objects.filter(location=location).order_by('forecast_time').first()
        
        should_predict = False
        
        if first_forecast is None: #chưa có forecast
            should_predict = True
        else:
            if first_forecast.forecast_time != next_hour:
                should_predict = True
                print(f"[DEBUG] First forecast time {first_forecast.forecast_time} != next hour {next_hour}")
            else:
                #kiểm tra update_at cũ hơn 1h
                hours_since_update = (now - first_forecast.updated_at).total_seconds() / 3600
                if hours_since_update > 1:
                    should_predict = True
                    print(f"{hours_since_update:.1f}h ago, repredict")

        if should_predict:
            ai_dir = Path(__file__).resolve().parent.parent / 'Weather_AI'
            sys.path.insert(0, str(ai_dir))
            from Weather_AI.predict_lstm_hourly_24h import predict_hourly_temperature
            from Weather_AI.predict_humidity_lstm import predict_hourly_humidity
            from django.db import transaction
            import time
            
            province_name = get_province_name(location)
            
            #retry khi db bị lock
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    with transaction.atomic():
                        #predict temp
                        HourlyForecast.objects.filter(location=location).delete()
                        predict_hourly_temperature(province_name, steps=24, force=True)
                    
                    try:
                        with transaction.atomic():
                            #predict humidity
                            predict_hourly_humidity(province_name, steps=24, force=True)
                    except Exception as e:
                        print(f"Humidity prediction failed (temp saved): {e}")
                    
                    break  # Thành công, thoát loop
                    
                except Exception as e:
                    if 'database is locked' in str(e) and attempt < max_retries - 1:
                        wait_time = (attempt + 1)  # Đợi 1s, 2s, 3s, 4s, 5s
                        print(f"Database locked, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                    else:
                        print(f"Error predict hourly: {e}")
                        return []
        
        #trả về forecasts
        return HourlyForecast.objects.filter(location=location).order_by('forecast_time')
    
    @staticmethod
    def get_or_predict_daily(location):
        from .models import DailyForecast
        from datetime import timedelta
        
        forecasts = DailyForecast.objects.filter(location=location).order_by('forecast_date')
        should_predict = False
        
        if not forecasts.exists(): #check chưa tồn tại
            should_predict = True
        else:
            latest = forecasts.aggregate(Max('updated_at'))['updated_at__max']
            if (timezone.now() - latest).total_seconds() > 86400:
                #quá 24h → re predicting
                should_predict = True
            else:
                #bắt đầu từ ngày mai
                base_date = timezone.localdate() if getattr(settings, 'USE_TZ', False) else timezone.now().date()
                tomorrow = base_date + timedelta(days=1)
                first_forecast = forecasts.first()
                if first_forecast.forecast_date != tomorrow:
                    #ngày dự báo sai → predict lại
                    should_predict = True
                    print(f"[INFO] Forecast dates incorrect. Expected {tomorrow}, got {first_forecast.forecast_date}")
        
        if should_predict:
            DailyForecast.objects.filter(location=location).delete()
            province_name = get_province_name(location)
            try:
                ai_dir = Path(__file__).resolve().parent.parent / 'Weather_AI'
                sys.path.insert(0, str(ai_dir))
                from Weather_AI.predict_daily_5days_sarima import predict_daily_temperature

                predict_daily_temperature(province_name, steps=5, force=True)
            except Exception as e:
                print(f"Error predict daily: {e}")
                return []
        
        #trả về forecasts
        return DailyForecast.objects.filter(location=location).order_by('forecast_date')

    @staticmethod
    def get_or_refresh_solar_daily(location, target_date=None, max_age_hours=1):
        from .models import SolarForecast, HourlyForecast
        import pandas as pd

        if target_date is None:
            target_date = timezone.localdate() if getattr(settings, 'USE_TZ', False) else timezone.now().date()

        day_start = datetime.combine(target_date, time.min)
        day_end = day_start + timedelta(days=1)

        def _hour_key(dt):
            if timezone.is_aware(dt):
                dt = timezone.localtime(dt).replace(tzinfo=None)
            return dt.replace(minute=0, second=0, microsecond=0)

        existing = SolarForecast.objects.filter(
            location=location,
            forecast_time__gte=day_start,
            forecast_time__lt=day_end,
        ).order_by('forecast_time')

        should_refresh = False
        if existing.count() != 24:
            should_refresh = True
        else:
            latest_created = existing.order_by('-created_at').first().created_at
            age_hours = (timezone.now() - latest_created).total_seconds() / 3600
            if age_hours > max_age_hours:
                should_refresh = True

        if should_refresh:
            province_name = get_province_name(location)
            if not is_solar_supported(province_name):
                raise ValueError(f"Chưa hỗ trợ dự báo bức xạ cho tỉnh này: {province_name}")

            base_dir = Path(__file__).resolve().parent.parent
            script_path = base_dir / "Weather_AI" / "predict_solar_lstm_34.py"
            result_dir = base_dir / "Weather_AI" / "results_train_shortwave_radiation_lstm"
            forecast_file = result_dir / f"forecast_{province_name}.csv"

            result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    province_name,
                    '--date',
                    target_date.strftime('%Y-%m-%d'),
                ],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(base_dir / "Weather_AI"),
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr or result.stdout or 'Solar predict failed')

            if not forecast_file.exists():
                raise FileNotFoundError(f"Không tìm thấy file dự báo: {forecast_file}")

            df = pd.read_csv(forecast_file)
            if 'Time' not in df.columns or 'Radiation_Forecast' not in df.columns:
                raise ValueError('File dự báo solar thiếu cột Time hoặc Radiation_Forecast')

            df['Time'] = pd.to_datetime(df['Time'])
            df = df[df['Time'].dt.date == target_date].copy()
            df = df.sort_values('Time')

            if len(df) != 24:
                raise ValueError(f"Dự báo solar không đủ 24 giờ cho {target_date} (got={len(df)})")

            solar_rows = []
            time_to_value = {}
            for _, row in df.iterrows():
                dt = row['Time'].to_pydatetime() if hasattr(row['Time'], 'to_pydatetime') else row['Time']
                if timezone.is_aware(dt):
                    dt = timezone.localtime(dt).replace(tzinfo=None)

                radiation_value = float(row['Radiation_Forecast'])
                solar_rows.append(
                    SolarForecast(
                        location=location,
                        forecast_time=dt,
                        shortwave_radiation=radiation_value,
                    )
                )
                time_to_value[_hour_key(dt)] = radiation_value

            with transaction.atomic():
                SolarForecast.objects.filter(
                    location=location,
                    forecast_time__gte=day_start,
                    forecast_time__lt=day_end,
                ).delete()
                SolarForecast.objects.bulk_create(solar_rows, ignore_conflicts=False)

            # Sync radiation into existing HourlyForecast rows (update-only)
            hourly_qs = HourlyForecast.objects.filter(
                location=location,
                forecast_time__gte=day_start,
                forecast_time__lt=day_end,
            )
            hourly = list(hourly_qs)
            now_ts = timezone.now()
            for hf in hourly:
                key = _hour_key(hf.forecast_time)
                if key in time_to_value:
                    hf.shortwave_radiation = time_to_value[key]
                    hf.updated_at = now_ts
            if hourly:
                HourlyForecast.objects.bulk_update(hourly, ['shortwave_radiation', 'updated_at'])

        return SolarForecast.objects.filter(
            location=location,
            forecast_time__gte=day_start,
            forecast_time__lt=day_end,
        ).order_by('forecast_time')
