# weather/services.py
import requests
from django.conf import settings


class MeteoAPIService:

    def __init__(self, lat, lon):
        self.lat = lat
        self.lon = lon
        self.base_url = "https://api.open-meteo.com/v1/forecast"

    def fetch_current_weather(self):
        """
        Gọi API Meteo chi tiết hơn để lấy đủ dữ liệu cho HTML.
        """
        params = {
            'latitude': self.lat,
            'longitude': self.lon,
            'timezone': 'Asia/Ho_Chi_Minh',

            # 1. Dữ liệu hiện tại
            # (Thêm weathercode, wind_speed)
            'current_weather': 'true',

            # 2. Dữ liệu hôm nay (để lấy Thấp/Cao, UV)
            'daily': 'weathercode,temperature_2m_max,temperature_2m_min,uv_index_max',

            # 3. Dữ liệu giờ (để lấy Cảm giác như, Độ ẩm, Áp suất, Tầm nhìn)
            'hourly': 'apparent_temperature,relativehumidity_2m,pressure_msl,visibility',

            # Chỉ lấy 1 ngày (hôm nay)
            'forecast_days': 1
        }

        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            print(f"Lỗi gọi API Meteo: {e}")
            return None

    def fetch_weather_alerts(self):
        # (API Meteo không có cảnh báo cho VN, nên tạm thời trả về rỗng)
        return []