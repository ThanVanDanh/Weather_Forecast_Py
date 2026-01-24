from django.db import models
from django.utils import timezone

class Location(models.Model):
    city_name = models.CharField(max_length=100, verbose_name="Tỉnh thành")
    city_name_vn = models.CharField(max_length=100, verbose_name="Tỉnh thành có dấu", blank=True, null=True)
    country_code = models.CharField(max_length=5,verbose_name="Mã quốc gia" )
    latitude = models.FloatField(verbose_name="Vĩ độ")
    longitude = models.FloatField(verbose_name="Kinh độ")
    timezone = models.CharField(max_length=50,verbose_name="Múi giờ", null=True, blank=True)

    class Meta:
        unique_together = ('latitude', 'longitude')
        verbose_name = "vị trí"
        verbose_name_plural = "Vị trí"

    def __str__(self):
        return f"{self.city_name} ({self.country_code})" if f"{self.country_code}" else f"{self.city_name}"


class CurrentWeatherCache(models.Model):
    location = models.OneToOneField(Location,verbose_name="Tỉnh thành", on_delete=models.CASCADE, primary_key=True, related_name='current_weather_cache')
    data = models.JSONField(verbose_name="Dữ liệu JSON từ API")
    last_updated = models.DateTimeField(auto_now=True, verbose_name="Cập nhật lần cuối")

    class Meta:
        verbose_name = "bộ nhớ đệm thời tiết hiện tại"
        verbose_name_plural = "Bộ nhớ đệm thời tiết hiện tại"

    def is_stale(self, minutes=15):
        return (timezone.now() - self.last_updated).total_seconds() > (minutes * 60)


class RainForecastCache(models.Model):
    location = models.OneToOneField(Location, verbose_name="Tỉnh thành", on_delete=models.CASCADE, primary_key=True, related_name='rain_forecast_cache')
    data = models.JSONField(verbose_name="Dữ liệu dự báo mưa minutely")
    last_updated = models.DateTimeField(auto_now=True, verbose_name="Cập nhật lần cuối")

    class Meta:
        verbose_name = "bộ nhớ đệm dự báo mưa"
        verbose_name_plural = "Bộ nhớ đệm dự báo mưa"

    def is_stale(self, minutes=15):
        return (timezone.now() - self.last_updated).total_seconds() > (minutes * 60)

class HourlyForecast(models.Model):
    location = models.ForeignKey(Location,verbose_name="Tỉnh thành", on_delete=models.CASCADE, related_name='hourly_forecasts')
    forecast_time = models.DateTimeField(verbose_name="Giờ dự báo")
    
    temperature = models.FloatField(verbose_name="Nhiệt độ (°C)")
    humidity = models.FloatField(null=True, blank=True, verbose_name="Độ ẩm (%)")
    shortwave_radiation = models.FloatField(null=True, blank=True, verbose_name="Bức xạ (W/m²)")

    updated_at = models.DateTimeField(auto_now=True, verbose_name="Cập nhật lúc")

    class Meta:
        unique_together = ('location', 'forecast_time')
        ordering = ['forecast_time']
        verbose_name = "dự báo theo nhiệt độ theo giờ (24h)"
        verbose_name_plural = "Dự báo theo nhiệt độ theo giờ (24h)"

    def __str__(self):
        return f"{self.location.city_name} - {self.forecast_time.strftime('%H:%M')}"


class DailyForecast(models.Model):
    location = models.ForeignKey(Location,verbose_name="Tỉnh thành", on_delete=models.CASCADE, related_name='daily_forecasts')
    forecast_date = models.DateField(verbose_name="Ngày dự báo")
    
    temp_max = models.FloatField(verbose_name="Nhiệt độ cao nhất (°C)")
    temp_min = models.FloatField(verbose_name="Nhiệt độ thấp nhất (°C)")
    
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Cập nhật lúc")

    class Meta:
        unique_together = ('location', 'forecast_date')
        ordering = ['forecast_date']
        verbose_name = "dự báo nhiệt độ theo ngày"
        verbose_name_plural = "Dự báo nhiệt độ theo ngày (5 ngày)"

    def __str__(self):
        return f"{self.location.city_name} - {self.forecast_date.strftime('%d/%m/%Y')}"


class WeatherAlert(models.Model):
    location = models.ForeignKey(Location,verbose_name="Tỉnh thành",  on_delete=models.CASCADE, related_name='alerts')
    api_alert_id = models.CharField(max_length=100, unique=True)
    event_name = models.CharField(verbose_name="Tên sự kiện", max_length=200)
    description = models.TextField(verbose_name="Mô tả")
    start_time = models.DateTimeField(verbose_name="Bắt đầu")
    end_time = models.DateTimeField(verbose_name="Kết thúc")

    class Meta:
        verbose_name = "cảnh báo thời tiết"
        verbose_name_plural = "Cảnh báo thời tiết"

class SearchHistory(models.Model):
    from django.contrib.auth.models import User

    user = models.ForeignKey(User, verbose_name="Người dùng",on_delete=models.CASCADE, related_name='search_history')
    location = models.ForeignKey(Location,verbose_name="Tỉnh thành",  on_delete=models.CASCADE, related_name='search_history')

    temperature = models.FloatField(null=True, blank=True, verbose_name="Nhiệt độ lúc tìm kiếm")
    weather_code = models.IntegerField(null=True, blank=True, verbose_name="Mã thời tiết")
    is_day = models.BooleanField(default=True, verbose_name="Ban ngày")

    searched_at = models.DateTimeField(auto_now=True, verbose_name="Thời gian tìm kiếm")

    class Meta:
        ordering = ['-searched_at']
        verbose_name = "lịch sử tìm kiếm"
        verbose_name_plural = "Lịch sử tìm kiếm"

    def __str__(self):
        return f"{self.user.username} - {self.location.city_name_vn or self.location.city_name}"

class SolarForecast(models.Model):
    location = models.ForeignKey(Location,verbose_name="Tỉnh thành",  on_delete=models.CASCADE)
    forecast_time = models.DateTimeField(verbose_name="Giờ dự báo")
    shortwave_radiation = models.FloatField(null=True,verbose_name="Bức xạ")
    created_at = models.DateTimeField(auto_now_add=True,verbose_name="Tạo lúc")
    class Meta:
        unique_together = ['location', 'forecast_time']
        ordering = ['forecast_time']
        verbose_name = "dự báo bức xạ mặt trời"
        verbose_name_plural = "Dự báo bức xạ mặt trời"

    def __str__(self):
        return f"{self.location.city_name} - {self.forecast_time.strftime('%d/%m/%Y %H:%M')}"

from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User,verbose_name="Tỉnh thành",  on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, verbose_name='Số điện thoại', blank=True)
    address = models.CharField(max_length=255, verbose_name='Địa chỉ hiện tại', blank=True, null=True)
    latitude = models.FloatField(verbose_name='Vĩ độ', blank=True, null=True)
    longitude = models.FloatField(verbose_name='Kinh độ', blank=True, null=True)

    class Meta:
        verbose_name = "hồ sơ người dùng"
        verbose_name_plural = "Hồ sơ người dùng"

    def __str__(self):
        return f"{self.user.username} - {self.phone}"