import requests
from django.conf import settings


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
