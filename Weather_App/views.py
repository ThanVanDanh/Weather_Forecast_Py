from django.shortcuts import render, get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db.models import Q

from .models import Location, CurrentWeatherCache, AIForecast, WeatherAlert
from .serializers import (
    LocationSerializer, FeaturedCitySerializer
)
from .services import MeteoAPIService

def weather_dashboard(request):
    # Django sẽ tìm 'weather/dashboard.html' bên trong thư mục 'templates'
    return render(request, 'index.html')

@api_view(['GET'])
def get_location_search(request):
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


# API 2: LẤY THỜI TIẾT HIỆN TẠI (DÙNG CACHE)
@api_view(['GET'])
def get_current_weather(request):
    location_id = request.query_params.get('location_id')
    location = get_object_or_404(Location, id=location_id)

    try:
        cache = CurrentWeatherCache.objects.get(location=location)
        if not cache.is_stale(minutes=30): # Kiểm tra dữ liệu đã được lấy hơn 30p chưa
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


@api_view(['GET'])
def get_featured_weather(request):
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

    serializer = FeaturedCitySerializer(locations, many=True)
    return Response(serializer.data)

def province_view(request, slug):
    city_name_from_slug = slug.replace('-', ' ')
    try:
        location = Location.objects.filter(city_name__icontains=city_name_from_slug).first()

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

def solar_energy_view(request):
    """Trang năng lượng mặt trời"""
    return render(request, 'solar-energy.html')