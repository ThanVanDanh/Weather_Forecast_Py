# weather/management/commands/warm_cache.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from Weather_App.models import Location, CurrentWeatherCache
from Weather_App.services import MeteoAPIService  # Import service của bạn

# LẤY 9 ID TỪ FILE VIEWS.PY CỦA BẠN
FEATURED_IDS = [
    11,  # Ha Noi
    30,  # Ho Chi Minh City
    6,  # Da Nang
    13,  # Hai Phong
    4,  # Can Tho
    15,  # Khanh Hoa
    29,  # Hue
    1,  # An Giang
    3  # Ca Mau
]


class Command(BaseCommand):
    help = 'Nạp (warm up) cache cho 9 thành phố nổi bật'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Bắt đầu "Warm Up" Bảng 2 (Cache)...'))

        locations = Location.objects.filter(id__in=FEATURED_IDS)
        count = 0

        for location in locations:
            self.stdout.write(f'Đang lấy dữ liệu cho: {location.city_name}...')
            try:
                # 1. Gọi API Meteo (giống hệt views.py)
                service = MeteoAPIService(lat=location.latitude, lon=location.longitude)
                new_data = service.fetch_current_weather()

                if new_data:
                    # 2. Lưu vào Bảng 2 (CurrentWeatherCache)
                    cache, _ = CurrentWeatherCache.objects.update_or_create(
                        location=location,
                        defaults={'data': new_data, 'last_updated': timezone.now()}
                    )
                    count += 1
                    self.stdout.write(self.style.SUCCESS(f'Đã cache {location.city_name}'))
                else:
                    self.stdout.write(self.style.WARNING(f'Lỗi API, bỏ qua {location.city_name}'))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Lỗi nghiêm trọng: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Hoàn tất! Đã cache {count}/9 thành phố.'))