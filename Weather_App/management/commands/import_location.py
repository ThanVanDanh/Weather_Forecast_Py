# weather/management/commands/import_locations.py
from django.core.management.base import BaseCommand
from Weather_App.models import Location

VIETNAM_LOCATIONS = [
    {'city': 'An Giang', 'lat': 10.0124, 'lon': 105.0809, 'tz': 'Asia/Ho_Chi_Minh'},
    {'city': 'Bac Ninh', 'lat': 21.2731, 'lon': 106.1946, 'tz': 'Asia/Ho_Chi_Minh'},
    {'city': 'Ca Mau', 'lat': 9.1768, 'lon': 105.1524, 'tz': 'Asia/Ho_Chi_Minh'},
    {'city': 'Can Tho', 'lat': 10.0371, 'lon': 105.7883, 'tz': 'Asia/Ho_Chi_Minh'},
    {'city': 'Cao Bang', 'lat': 22.6657, 'lon': 106.2579, 'tz': 'Asia/Ho_Chi_Minh'},
    {'city': 'Da Nang', 'lat': 16.0678, 'lon': 108.2208, 'tz': 'Asia/Ho_Chi_Minh'},
    {'city': 'Dak Lak', 'lat': 12.6675, 'lon': 108.0378, 'tz': 'Asia/Ho_Chi_Minh'},
    {'city': 'Dien Bien', 'lat': 21.6268, 'lon': 103.1589, 'tz': 'Asia/Ho_Chi_Minh'},
    {'city': 'Dong Nai', 'lat': 10.9447, 'lon': 106.8243, 'tz': 'Asia/Ho_Chi_Minh'},
    {'city': 'Dong Thap', 'lat': 10.4554, 'lon': 105.6378, 'tz': 'Asia/Ho_Chi_Minh'},
    {'city': 'Gia Lai', 'lat': 13.7765, 'lon': 109.2237, 'tz': 'Asia/Ho_Chi_Minh'},
    {'city': 'Ha Noi', 'lat': 21.0245, 'lon': 105.8412, 'tz': 'Asia/Ho_Chi_Minh'},
    {'city': 'Ha Tinh', 'lat': 18.3428, 'lon': 105.9057, 'tz': 'Asia/Ho_Chi_Minh'},
    {'city': 'Hai Phong', 'lat': 20.8648, 'lon': 106.6834, 'tz': 'Asia/Ho_Chi_Minh'},
    {'city': 'Hung Yen', 'lat': 20.6464, 'lon': 106.0511, 'tz': 'Asia/Ho_Chi_Minh'},
    {'city': 'Khanh Hoa', 'lat': 12.2451, 'lon': 109.1943, 'tz': 'Asia/Ho_Chi_Minh'},
    {'city': 'Lai Chau', 'lat': 22.3964, 'lon': 103.4582, 'tz': 'Asia/Ho_Chi_Minh'},
    {'city': 'Lam Dong', 'lat': 11.53, 'lon': 108.05, 'tz': 'Asia/Ho_Chi_Minh'},
    {'city': 'Lang Son', 'lat': 21.8526, 'lon': 106.7610, 'tz': 'Asia/Ho_Chi_Minh'},
    {'city': 'Lao Cai', 'lat': 21.7229, 'lon': 104.9113, 'tz': 'Asia/Ho_Chi_Minh'},
    {'city': 'Nghe An', 'lat': 18.6734, 'lon': 105.6923, 'tz': 'Asia/Ho_Chi_Minh'},
    {'city': 'Ninh Binh', 'lat': 20.2581, 'lon': 105.9797, 'tz': 'Asia/Ho_Chi_Minh'},
    {'city': 'Phu Tho', 'lat': 21.3227, 'lon': 105.4020, 'tz': 'Asia/Ho_Chi_Minh'},
    {'city': 'Quang Ngai', 'lat': 15.1205, 'lon': 108.7923, 'tz': 'Asia/Ho_Chi_Minh'},
    {'city': 'Quang Ninh', 'lat': 20.9505, 'lon': 107.0734, 'tz': 'Asia/Ho_Chi_Minh'},
    {'city': 'Quang Tri', 'lat': 17.4688, 'lon': 106.6223, 'tz': 'Asia/Ho_Chi_Minh'},
    {'city': 'Son La', 'lat': 21.3256, 'lon': 103.9188, 'tz': 'Asia/Ho_Chi_Minh'},
    {'city': 'Tay Ninh', 'lat': 10.5359, 'lon': 106.4137, 'tz': 'Asia/Ho_Chi_Minh'},
    {'city': 'Thai Nguyen', 'lat': 21.5973, 'lon': 105.8438, 'tz': 'Asia/Ho_Chi_Minh'},
    {'city': 'Thanh Hoa', 'lat': 19.8000, 'lon': 105.7667, 'tz': 'Asia/Ho_Chi_Minh'},
    {'city': 'Hue', 'lat': 16.4619, 'lon': 107.5955, 'tz': 'Asia/Ho_Chi_Minh'},
    {'city': 'Ho Chi Minh City', 'lat': 10.8230, 'lon': 106.6296, 'tz': 'Asia/Ho_Chi_Minh'},
    {'city': 'Tuyen Quang', 'lat': 21.8236, 'lon': 105.2142, 'tz': 'Asia/Ho_Chi_Minh'},
    {'city': 'Vinh Long', 'lat': 10.2537, 'lon': 105.9722, 'tz': 'Asia/Ho_Chi_Minh'},
]

class Command(BaseCommand):
    help = 'Nạp (seed) các tỉnh/thành phố của Việt Nam vào CSDL'

    def handle(self, *args, **options):
        self.stdout.write('Bắt đầu nạp dữ liệu vị trí Việt Nam...')
        count_created = 0
        for loc in VIETNAM_LOCATIONS:
            obj, created = Location.objects.update_or_create(
                city_name=loc['city'],
                defaults={
                    'country_code': 'VN',
                    'latitude': loc['lat'],
                    'longitude': loc['lon'],
                    'timezone': loc['tz']
                }
            )
            if created:
                count_created += 1
        self.stdout.write(self.style.SUCCESS(f'Hoàn tất! Đã tạo mới {count_created} vị trí.'))