# weather/services.py
import requests
from django.conf import settings


# Giả sử bạn dùng API "Meteo" (ví dụ: Open-Meteo)
# Bạn cần đặt API Key (nếu có) vào settings.py
# METEO_API_KEY = "your_key_here"

class MeteoAPIService:
    """
    Lớp dịch vụ để gọi API của Meteo.
    """

    def __init__(self, lat, lon):
        self.lat = lat
        self.lon = lon
        self.base_url = "https://api.open-meteo.com/v1/forecast"

    def fetch_current_weather(self):
        params = {
            'latitude': self.lat,
            'longitude': self.lon,
            'current_weather': 'true',
            'timezone': 'Asia/Ho_Chi_Minh'
        }

        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()

            # Meteo trả về JSON, ta chỉ lấy phần 'current_weather'
            return response.json().get('current_weather')

        except requests.RequestException as e:
            print(f"Lỗi gọi API Meteo: {e}")
            return None

    def fetch_weather_alerts(self):
        """
        Gọi API Meteo để lấy cảnh báo (nếu có).
        """
        params = {
            'latitude': self.lat,
            'longitude': self.lon,
            'timezone': 'Asia/Ho_Chi_Minh'
            # Thêm các trường 'alerts' nếu API Meteo của bạn hỗ trợ
        }
        try:
            # ... (Logic gọi API cảnh báo của Meteo) ...
            return []  # Trả về danh sách cảnh báo
        except requests.RequestException:
            return []