from django.db import models
from django.utils import timezone
from .models_profile import UserProfile

class Location(models.Model):
    city_name = models.CharField(max_length=100)
    city_name_vn = models.CharField(max_length=100, verbose_name="Tên tiếng Việt có dấu", blank=True, null=True)
    country_code = models.CharField(max_length=5)
    latitude = models.FloatField(verbose_name="Vĩ độ")
    longitude = models.FloatField(verbose_name="Kinh độ")
    timezone = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        unique_together = ('latitude', 'longitude')
        verbose_name = "Vị trí"
        verbose_name_plural = "1. Vị trí"

    def __str__(self):
        return f"{self.city_name} ({self.country_code})" if f"{self.country_code}" else f"{self.city_name}"


class CurrentWeatherCache(models.Model):
    location = models.OneToOneField(Location, on_delete=models.CASCADE, primary_key=True, related_name='current_weather_cache')
    data = models.JSONField(verbose_name="Dữ liệu JSON từ API")
    last_updated = models.DateTimeField(auto_now=True, verbose_name="Cập nhật lần cuối")

    class Meta:
        verbose_name = "Cache thời tiết hiện tại"
        verbose_name_plural = "2. Cache thời tiết hiện tại"

    def is_stale(self, minutes=15):
        return (timezone.now() - self.last_updated).total_seconds() > (minutes * 60)


class RainForecastCache(models.Model):
    location = models.OneToOneField(Location, on_delete=models.CASCADE, primary_key=True, related_name='rain_forecast_cache')
    data = models.JSONField(verbose_name="Dữ liệu dự báo mưa minutely")
    last_updated = models.DateTimeField(auto_now=True, verbose_name="Cập nhật lần cuối")

    class Meta:
        verbose_name = "Cache dự báo mưa minutely"
        verbose_name_plural = "2b. Cache dự báo mưa"

    def is_stale(self, minutes=15):
        """Cache có cũ không? Mặc định 15 phút"""
        return (timezone.now() - self.last_updated).total_seconds() > (minutes * 60)


class HistoricalData(models.Model):
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name='historical_data'
    )
    observation_date = models.DateField(verbose_name="Ngày quan sát")
    temp_avg = models.FloatField(null=True, blank=True, verbose_name="Nhiệt độ TB")
    temp_max = models.FloatField(null=True, blank=True, verbose_name="Nhiệt độ max")
    temp_min = models.FloatField(null=True, blank=True, verbose_name="Nhiệt độ min")
    humidity_avg = models.FloatField(null=True, blank=True, verbose_name="Độ ẩm TB")
    precipitation_total = models.FloatField(null=True, blank=True, verbose_name="Tổng lượng mưa")

    class Meta:
        unique_together = ('location', 'observation_date')
        verbose_name = "Dữ liệu lịch sử (AI Train)"
        verbose_name_plural = "3. Dữ liệu lịch sử (AI Train)"


class HourlyForecast(models.Model):
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='hourly_forecasts')
    forecast_time = models.DateTimeField(verbose_name="Giờ dự báo")
    
    temperature = models.FloatField(verbose_name="Nhiệt độ (°C)")
    humidity = models.FloatField(null=True, blank=True, verbose_name="Độ ẩm (%)")
    shortwave_radiation = models.FloatField(null=True, blank=True, verbose_name="Bức xạ (W/m²)")

    updated_at = models.DateTimeField(auto_now=True, verbose_name="Cập nhật lúc")

    class Meta:
        unique_together = ('location', 'forecast_time')
        ordering = ['forecast_time']
        verbose_name = "Dự báo theo Giờ (24h)"
        verbose_name_plural = "4. Dự báo theo Giờ (24h)"

    def __str__(self):
        return f"{self.location.city_name} - {self.forecast_time.strftime('%H:%M')}"


class DailyForecast(models.Model):
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='daily_forecasts')
    forecast_date = models.DateField(verbose_name="Ngày dự báo")
    
    temp_max = models.FloatField(verbose_name="Nhiệt độ cao nhất (°C)")
    temp_min = models.FloatField(verbose_name="Nhiệt độ thấp nhất (°C)")
    
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Cập nhật lúc")

    class Meta:
        unique_together = ('location', 'forecast_date')
        ordering = ['forecast_date']
        verbose_name = "Dự báo theo Ngày (5 ngày)"
        verbose_name_plural = "5. Dự báo theo Ngày (5 ngày)"

    def __str__(self):
        return f"{self.location.city_name} - {self.forecast_date.strftime('%d/%m/%Y')}"


class WeatherAlert(models.Model):
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='alerts')
    api_alert_id = models.CharField(max_length=100, unique=True)
    event_name = models.CharField(max_length=200)
    description = models.TextField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    class Meta:
        verbose_name = "Cảnh báo thời tiết"
        verbose_name_plural = "6. Cảnh báo thời tiết"

class SolarForecast(models.Model):
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    forecast_time = models.DateTimeField()
    shortwave_radiation = models.FloatField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ['location', 'forecast_time']
        ordering = ['forecast_time']