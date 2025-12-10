from rest_framework import serializers
from .models import AIForecast, WeatherAlert, Location, CurrentWeatherCache

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ('id', 'city_name', 'country_code', 'latitude', 'longitude')

class FeaturedCitySerializer(serializers.ModelSerializer):
    current_weather = serializers.JSONField(
        source='current_weather_cache.data',
        read_only=True
    )

    class Meta:
        model = Location
        fields = ('id', 'city_name', 'current_weather')