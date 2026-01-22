"""
Hệ thống dự báo mưa minutely (phút) - 60 phút tới
Sử dụng OpenWeatherMap One Call API 3.0
Với caching để tránh spam API khi F5 liên tục
"""
import requests
from typing import Dict, List, Optional
from django.utils import timezone

OPENWEATHER_API_KEY = "9d9dfae9131f26975dfab658ed2b4d36"


def get_rain_forecast_minutely(lat: float, lon: float, location_obj=None) -> Dict:
    """
    Lấy dự báo mưa cho 60 phút tới (với cache 10 phút)
    Trả về thông tin: khi nào mưa bắt đầu, khi nào kết thúc, cường độ
    """
    # Kiểm tra cache nếu có location_obj
    if location_obj:
        from .models import RainForecastCache
        try:
            cache = RainForecastCache.objects.get(location=location_obj)
            if not cache.is_stale(minutes=10):
                # Cache còn mới (< 10 phút)
                cached_age = (timezone.now() - cache.last_updated).total_seconds()
                print(f"[RainForecast] Sử dụng cache ({cached_age:.0f}s tuổi)")
                result = cache.data
                result['source'] = 'cache'
                result['cache_age_seconds'] = int(cached_age)
                return result
            else:
                print(f"[RainForecast] Cache đã cũ, fetch mới từ API")
        except RainForecastCache.DoesNotExist:
            print(f"[RainForecast] Chưa có cache, fetch từ API")
    
    # Fetch từ API
    try:
        # Gọi One Call API 3.0 - Minutely precipitation
        url = "https://api.openweathermap.org/data/3.0/onecall"
        params = {
            'lat': lat,
            'lon': lon,
            'appid': OPENWEATHER_API_KEY,
            'exclude': 'current,hourly,daily,alerts',  # Chỉ lấy minutely
            'units': 'metric'
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        # Nếu API 3.0 không khả dụng, thử API 2.5
        if response.status_code == 401 or response.status_code == 403:
            # Fallback sang API 2.5 (miễn phí)
            url = "https://api.openweathermap.org/data/2.5/onecall"
            response = requests.get(url, params=params, timeout=10)
        
        response.raise_for_status()
        data = response.json()
        
        # Phân tích dữ liệu minutely
        minutely = data.get('minutely', [])
        
        if not minutely:
            # Không có dữ liệu minutely - ước tính từ hourly
            return estimate_from_hourly(lat, lon)
        
        # Phân tích khi nào mưa bắt đầu
        rain_start = None
        rain_end = None
        max_precipitation = 0
        total_precipitation = 0
        
        for i, minute_data in enumerate(minutely):
            precipitation = minute_data.get('precipitation', 0)
            total_precipitation += precipitation
            max_precipitation = max(max_precipitation, precipitation)
            
            # Ngưỡng mưa: > 0.1 mm
            if precipitation > 0.1:
                if rain_start is None:
                    rain_start = i  # Phút thứ i
                rain_end = i
        
        # Tạo thông báo
        message = create_rain_message(rain_start, rain_end, max_precipitation, total_precipitation)
        
        # Tạo timeline cho visualization
        timeline = []
        for i, minute_data in enumerate(minutely):
            precipitation = minute_data.get('precipitation', 0)
            timeline.append({
                'minute': i,
                'precipitation': precipitation,
                'intensity': get_rain_intensity(precipitation)
            })
        
        result = {
            'status': 'success',
            'rain_start_minute': rain_start,
            'rain_end_minute': rain_end,
            'max_precipitation': max_precipitation,
            'total_precipitation': total_precipitation,
            'message': message,
            'timeline': timeline[:60],  # 60 phút
            'updated_at': data.get('current', {}).get('dt'),
            'icon': get_rain_icon(rain_start, max_precipitation),
            'color': get_rain_color(max_precipitation),
            'source': 'api'
        }
        
        # Lưu vào cache nếu có location_obj
        if location_obj:
            from .models import RainForecastCache
            try:
                cache, created = RainForecastCache.objects.update_or_create(
                    location=location_obj,
                    defaults={'data': result}
                )
                print(f"[RainForecast] {'Tạo mới' if created else 'Cập nhật'} cache")
            except Exception as e:
                print(f"[RainForecast] Lỗi lưu cache: {e}")
        
        return result
        
    except requests.exceptions.RequestException as e:
        # Fallback: ước tính từ hourly data
        print(f"[RainForecast] API minutely lỗi, fallback sang hourly: {e}")
        result = estimate_from_hourly(lat, lon)
        
        # Vẫn lưu cache kể cả khi dùng hourly estimate
        if location_obj and result.get('status') == 'success':
            from .models import RainForecastCache
            try:
                cache, created = RainForecastCache.objects.update_or_create(
                    location=location_obj,
                    defaults={'data': result}
                )
                print(f"[RainForecast] Lưu cache từ hourly estimate")
            except Exception as cache_error:
                print(f"[RainForecast] Lỗi lưu cache: {cache_error}")
        
        return result
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'message': 'Không thể lấy dự báo mưa'
        }


def estimate_from_hourly(lat: float, lon: float, location_obj=None) -> Dict:
    """
    Ước tính dự báo mưa từ hourly data (khi minutely không khả dụng)
    """
    try:
        url = "https://api.openweathermap.org/data/2.5/forecast"
        params = {
            'lat': lat,
            'lon': lon,
            'appid': OPENWEATHER_API_KEY,
            'units': 'metric',
            'cnt': 8  # 24h (mỗi 3h)
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Kiểm tra 24h tới có mưa không
        forecast_list = data.get('list', [])
        
        rain_found = False
        hours_until_rain = None
        max_rain = 0
        
        for i, forecast in enumerate(forecast_list):
            rain_3h = forecast.get('rain', {}).get('3h', 0)
            if rain_3h > 0.1:
                rain_found = True
                if hours_until_rain is None:
                    hours_until_rain = i * 3  # Mỗi forecast cách nhau 3h
                max_rain = max(max_rain, rain_3h)
        
        if not rain_found:
            message = "🌤️ Không có mưa trong 24 giờ tới. Trời quang đãng!"
            icon = "fa-sun"
            color = "#4CAF50"
        elif hours_until_rain == 0:
            message = f"🌧️ Đang có mưa hoặc sắp có mưa trong giờ tới. Cường độ: {get_rain_level(max_rain)}"
            icon = "fa-cloud-rain"
            color = "#2196F3"
        elif hours_until_rain <= 3:
            message = f"⛈️ Mưa sẽ bắt đầu trong khoảng {hours_until_rain} giờ tới. Hãy chuẩn bị ô/áo mưa!"
            icon = "fa-cloud-showers-heavy"
            color = "#FF9800"
        elif hours_until_rain <= 12:
            message = f"🌦️ Dự báo có mưa sau {hours_until_rain} giờ nữa"
            icon = "fa-cloud-sun-rain"
            color = "#9C27B0"
        else:
            message = f"☁️ Có thể có mưa trong 24h tới"
            icon = "fa-cloud"
            color = "#607D8B"
        
        return {
            'status': 'success',
            'method': 'hourly_estimate',
            'rain_start_minute': None,
            'message': message,
            'icon': icon,
            'color': color,
            'hours_until_rain': hours_until_rain,
            'max_rain_3h': max_rain,
            'timeline': [],  # Không có minutely data
            'source': 'hourly_api'
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'message': 'Không thể lấy dự báo mưa',
            'icon': 'fa-exclamation-triangle',
            'color': '#FF6B6B'
        }
        return {
            'status': 'error',
            'error': str(e),
            'message': '❌ Không thể lấy dự báo mưa. Vui lòng thử lại sau.'
        }


def create_rain_message(rain_start: Optional[int], rain_end: Optional[int], 
                        max_precip: float, total_precip: float) -> str:
    """
    Tạo thông báo dự báo mưa dễ hiểu cho người dùng
    """
    if rain_start is None:
        return "🌤️ Không có mưa trong 1 giờ tới. Trời quang đãng!"
    
    if rain_start == 0:
        # Đang mưa hoặc sắp mưa ngay
        duration = rain_end - rain_start if rain_end else 60
        intensity = get_rain_level(max_precip)
        return f"🌧️ Đang có mưa hoặc mưa sẽ bắt đầu ngay. Kéo dài khoảng {duration} phút. Cường độ: {intensity}"
    
    if rain_start <= 5:
        return f"⛈️ CẢNH BÁO: Mưa sẽ bắt đầu trong {rain_start} phút tới! Hãy tìm chỗ trú ẩn."
    
    if rain_start <= 15:
        duration = rain_end - rain_start if rain_end else 60 - rain_start
        return f"🌦️ Mưa sẽ bắt đầu sau {rain_start} phút nữa, kéo dài khoảng {duration} phút."
    
    if rain_start <= 30:
        return f"☔ Dự báo có mưa sau {rain_start} phút nữa. Hãy chuẩn bị ô hoặc áo mưa!"
    
    # Mưa sau > 30 phút
    return f"🌂 Có thể có mưa sau {rain_start} phút nữa (khoảng {rain_start // 60} giờ)"


def get_rain_intensity(precipitation: float) -> str:
    """
    Phân loại cường độ mưa
    precipitation: mm/h
    """
    if precipitation < 0.1:
        return "no_rain"
    elif precipitation < 2.5:
        return "light"
    elif precipitation < 7.6:
        return "moderate"
    elif precipitation < 50:
        return "heavy"
    else:
        return "violent"


def get_rain_icon(rain_start: Optional[int], max_precip: float) -> str:
    """
    Lấy icon phù hợp với tình trạng mưa
    """
    if rain_start is None:
        return "fa-sun"
    elif rain_start == 0 or rain_start <= 5:
        if max_precip >= 10:
            return "fa-cloud-showers-heavy"
        return "fa-cloud-rain"
    elif rain_start <= 15:
        return "fa-cloud-sun-rain"
    else:
        return "fa-umbrella"


def get_rain_color(max_precip: float) -> str:
    """
    Lấy màu cảnh báo theo cường độ mưa
    """
    if max_precip < 0.1:
        return "#4CAF50"  # Xanh lá - Không mưa
    elif max_precip < 2.5:
        return "#81C784"  # Xanh nhạt - Mưa nhẹ
    elif max_precip < 7.6:
        return "#FFB74D"  # Cam - Mưa vừa
    elif max_precip < 50:
        return "#FF7043"  # Đỏ cam - Mưa lớn
    else:
        return "#E53935"  # Đỏ đậm - Mưa rất lớn


def get_rain_level(precipitation: float) -> str:
    """
    Mô tả cường độ mưa bằng tiếng Việt
    """
    if precipitation < 0.1:
        return "Không mưa"
    elif precipitation < 2.5:
        return "Mưa nhỏ"
    elif precipitation < 7.6:
        return "Mưa vừa"
    elif precipitation < 50:
        return "Mưa to"
    else:
        return "Mưa rất to"
