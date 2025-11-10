# weather/serializers.py
from rest_framework import serializers
from .models import AIForecast, WeatherAlert, Location, CurrentWeatherCache

class LocationSerializer(serializers.ModelSerializer):
    """Serializer cho thông tin cơ bản của Location (khi tìm kiếm)"""
    class Meta:
        model = Location
        fields = ('id', 'city_name', 'country_code', 'latitude', 'longitude')

class AIForecastSerializer(serializers.ModelSerializer):
    """
    Serializer cho Bảng 4: Kết quả dự báo của AI (CẬP NHẬT)
    """
    class Meta:
        model = AIForecast
        fields = (
            'forecast_date',
            'predicted_temp_max',
            'predicted_temp_min',
            'predicted_precipitation_probability',
            'predicted_weather_code'
        )

class WeatherAlertSerializer(serializers.ModelSerializer):
    """Serializer cho Bảng 5: Cảnh báo thời tiết"""
    class Meta:
        model = WeatherAlert
        fields = ('event_name', 'description', 'start_time', 'end_time')

# --- THÊM SERIALIZER MỚI CHO "THÀNH PHỐ NỔI BẬT" ---
class FeaturedCitySerializer(serializers.ModelSerializer):
    """
    Serializer cho các thành phố nổi bật (Bảng 1 + Bảng 2)
    """
    current_weather = serializers.JSONField(
        source='current_weather_cache.data',
        read_only=True
    )

    class Meta:
        model = Location
        fields = ('id', 'city_name', 'current_weather')