from rest_framework import serializers
from .models import HourlyForecast, DailyForecast, WeatherAlert, Location, CurrentWeatherCache

class LocationSerializer(serializers.ModelSerializer):
    slug = serializers.SerializerMethodField()
    
    class Meta:
        model = Location
        fields = ('id', 'city_name', 'city_name_vn', 'country_code', 'latitude', 'longitude', 'slug')

    def get_slug(self, obj):
        from django.utils.text import slugify
        return slugify(obj.city_name_vn or obj.city_name)

class FeaturedCitySerializer(serializers.ModelSerializer):
    current_weather = serializers.JSONField(
        source='current_weather_cache.data',
        read_only=True
    )

    class Meta:
        model = Location
        fields = ('id', 'city_name', 'city_name_vn', 'current_weather')


class HourlyForecastSerializer(serializers.ModelSerializer):
    class Meta:
        model = HourlyForecast
        fields = ('forecast_time', 'temperature', 'humidity', 'shortwave_radiation', 'updated_at')


class DailyForecastSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyForecast
        fields = ('forecast_date', 'temp_max', 'temp_min', 'updated_at')