# weather/views.py
from django.shortcuts import render, get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db.models import Q

from .models import Location, CurrentWeatherCache, AIForecast, WeatherAlert
from .serializers import (
    AIForecastSerializer, WeatherAlertSerializer,
    LocationSerializer, FeaturedCitySerializer
)
from .services import MeteoAPIService


# ========================================================
# VIEW RENDER TRANG WEB CHÍNH
# ========================================================
def weather_dashboard(request):
    """
    Render trang HTML chính (dashboard) cho người dùng.
    """
    # Django sẽ tìm 'weather/dashboard.html' bên trong thư mục 'templates'
    return render(request, 'index.html')


# ========================================================
# API 1: TÌM KIẾM LOCATION
# ========================================================
@api_view(['GET'])
def get_location_search(request):
    """
    API để tìm kiếm Location (chỉ ở VN) dựa trên tên thành phố.
    Frontend gọi: /api/weather/search/?city=Hanoi
    """
    city_query = request.query_params.get('city')
    if not city_query:
        return Response(
            {"error": "Thiếu tham số 'city'"},
            status=status.HTTP_400_BAD_REQUEST
        )

    locations = Location.objects.filter(
        Q(country_code='VN') &
        Q(city_name__icontains=city_query)
    )

    if not locations.exists():
        return Response({"error": "Không tìm thấy tỉnh/thành phố"},
                        status=status.HTTP_404_NOT_FOUND)

    serializer = LocationSerializer(locations, many=True)
    return Response(serializer.data)


# ========================================================
# API 2: LẤY THỜI TIẾT HIỆN TẠI (DÙNG CACHE)
# ========================================================
@api_view(['GET'])
def get_current_weather(request):
    """
    API lấy thời tiết hiện tại (chi tiết), có cache 15 phút.
    Frontend gọi: /api/weather/current/?location_id=1
    """
    location_id = request.query_params.get('location_id')
    location = get_object_or_404(Location, id=location_id)

    try:
        cache = CurrentWeatherCache.objects.get(location=location)
        if not cache.is_stale(minutes=15):
            return Response(cache.data)  # 1. Dùng cache
    except CurrentWeatherCache.DoesNotExist:
        pass  # 2. Cache không có, đi tiếp

    # 3. Cache CŨ hoặc KHÔNG TỒN TẠI: Gọi API Meteo
    service = MeteoAPIService(lat=location.latitude, lon=location.longitude)
    new_data = service.fetch_current_weather()

    if new_data:
        cache, _ = CurrentWeatherCache.objects.update_or_create(
            location=location,
            defaults={'data': new_data, 'last_updated': timezone.now()}
        )
        return Response(cache.data)
    else:
        return Response({"error": "Không thể lấy dữ liệu từ API"},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)


# ========================================================
# API 3: LẤY DỰ BÁO AI (TỪ BẢNG 4)
# ========================================================
@api_view(['GET'])
def get_ai_forecast(request):
    """
    API lấy 15 ngày dự báo của AI (đã train).
    Frontend gọi: /api/weather/forecast/ai/?location_id=1
    """
    location_id = request.query_params.get('location_id')
    location = get_object_or_404(Location, id=location_id)

    today = timezone.localdate()
    forecasts = AIForecast.objects.filter(
        location=location,
        forecast_date__gte=today
    ).order_by('forecast_date')[:15]

    serializer = AIForecastSerializer(forecasts, many=True)
    return Response(serializer.data)


# ========================================================
# API 4: LẤY CẢNH BÁO (TỪ BẢNG 5)
# ========================================================
@api_view(['GET'])
def get_weather_alerts(request):
    """
    API lấy cảnh báo thời tiết.
    Frontend gọi: /api/weather/alerts/?location_id=1
    """
    location_id = request.query_params.get('location_id')
    location = get_object_or_404(Location, id=location_id)

    # (Service đã được cập nhật để trả về rỗng,
    # nhưng logic CSDL vẫn giữ lại)

    now = timezone.now()
    active_alerts = WeatherAlert.objects.filter(
        location=location, end_time__gte=now
    )

    serializer = WeatherAlertSerializer(active_alerts, many=True)
    return Response(serializer.data)


# ========================================================
# API 5: LẤY THÀNH PHỐ NỔI BẬT (BẢNG 1 + BẢNG 2)
# ========================================================
@api_view(['GET'])
def get_featured_weather(request):
    """
    API lấy dữ liệu thời tiết cho các thành phố nổi bật.
    Frontend gọi: /api/weather/featured/
    """
    # Lấy 9 tỉnh/TP hàng đầu (bạn có thể đổi ID)
    featured_ids = [
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

    locations = Location.objects.filter(
        id__in=featured_ids
    ).prefetch_related('current_weather_cache')

    # LƯU Ý: Bạn cần chạy API `get_current_weather` cho 9 TP này
    # ít nhất 1 lần để Bảng 2 (Cache) có dữ liệu cho họ.
    # JS sẽ kiểm tra 'current_weather' có null không.

    serializer = FeaturedCitySerializer(locations, many=True)
    return Response(serializer.data)

def province_view(request, slug):
    city_name_from_slug = slug.replace('-', ' ')
    try:
        location = get_object_or_404(Location, city_name__iexact=city_name_from_slug)

    except Location.DoesNotExist:
        return render(request, 'index.html', {'error': 'Không tìm thấy địa điểm'})
    context = {
        'location_id': location.id,
        'city_name': location.city_name,
        'latitude': location.latitude,
        'longitude': location.longitude,
    }
    return render(request, 'province-template.html', context)
def warning_view(request):

    return render(request, 'warningweather.html')