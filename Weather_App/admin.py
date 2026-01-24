from django.contrib import admin
from .models import UserProfile
from django.utils import timezone
from django.conf import settings

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'address', 'latitude', 'longitude')
    search_fields = ('user__username', 'phone', 'address')
from .models import Location, CurrentWeatherCache, HistoricalData, HourlyForecast, DailyForecast, WeatherAlert, SolarForecast

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('city_name', 'city_name_vn', 'country_code', 'latitude', 'longitude')
    search_fields = ('city_name', 'city_name_vn')

@admin.register(CurrentWeatherCache)
class CurrentWeatherCacheAdmin(admin.ModelAdmin):
    list_display = ('location', 'last_updated')

@admin.register(HistoricalData)
class HistoricalDataAdmin(admin.ModelAdmin):
    list_display = ('location', 'observation_date', 'temp_avg', 'humidity_avg')
    list_filter = ('location',)

@admin.register(HourlyForecast)
class HourlyForecastAdmin(admin.ModelAdmin):
    list_display = ('location', 'forecast_time', 'temperature', 'humidity', 'shortwave_radiation', 'updated_at')
    list_filter = ('location', 'forecast_time')
    ordering = ('-forecast_time',)

@admin.register(DailyForecast)
class DailyForecastAdmin(admin.ModelAdmin):
    list_display = ('location', 'forecast_date', 'temp_max', 'temp_min', 'updated_at')
    list_filter = ('location', 'forecast_date')
    ordering = ('-forecast_date',)

@admin.register(WeatherAlert)
class WeatherAlertAdmin(admin.ModelAdmin):
    list_display = ('location', 'event_name', 'start_time', 'end_time')


@admin.register(SolarForecast)
class SolarForecastAdmin(admin.ModelAdmin):
    list_display = ('location', 'forecast_time_local', 'forecast_time', 'shortwave_radiation', 'created_at')
    list_filter = ('location', 'forecast_time')
    ordering = ('-forecast_time',)

    @admin.display(description='forecast_time (local)')
    def forecast_time_local(self, obj):
        dt = obj.forecast_time
        if dt is None:
            return None
        if not getattr(settings, 'USE_TZ', False):
            return dt
        try:
            return timezone.localtime(dt)
        except Exception:
            return dt