from django.shortcuts import render, get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db.models import Q
import requests

from .models import Location, CurrentWeatherCache, HourlyForecast, DailyForecast, WeatherAlert
from .serializers import (
    LocationSerializer, FeaturedCitySerializer, HourlyForecastSerializer, DailyForecastSerializer
)
from .services import MeteoAPIService, ForecastService

def weather_dashboard(request):
    # Django sẽ tìm 'weather/dashboard.html' bên trong thư mục 'templates'
    return render(request, 'index.html')

def customer_care(request):
    """Trang chăm sóc khách hàng"""
    return render(request, 'customer_care.html')

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




@api_view(['POST'])
def locate_user(request):
    print("DEBUG: Processing User Location Request...")

    # Lấy latitude/longitude từ JSON body (do location.js gửi lên)
    lat = request.data.get('latitude')
    lon = request.data.get('longitude')

    # Nếu client gửi tọa độ GPS hợp lệ
    if lat is not None and lon is not None:
        print(f"DEBUG: Received GPS Coordinates: {lat}, {lon}")
        try:
            lat = float(lat)
            lon = float(lon)

            # Gọi BigDataCloud Reverse Geocoding API (Free, chính xác hơn Nominatim)
            url = f"https://api.bigdatacloud.net/data/reverse-geocode-client?latitude={lat}&longitude={lon}&localityLanguage=vi"
            headers = {"User-Agent": "WeatherApp/1.0"}

            resp = requests.get(url, headers=headers, timeout=10)

            if resp.status_code == 200:
                data = resp.json()

                # BigDataCloud trả về: city, locality, principalSubdivision (tỉnh/TP)

                province = data.get("principalSubdivision") or ""
                city = data.get("city") or ""

                display_name = province or city or data.get("countryName", "Việt Nam")

                request.session["current_city"] = display_name
                request.session.modified = True

                return Response({
                    "ok": True,
                    "city": display_name,
                    "province": province,
                    "source": "GPS + BigDataCloud",
                    "coordinates": {"lat": lat, "lon": lon}
                })
            else:
                return Response({
                    "ok": False,
                    "error": "Không thể xác định địa điểm từ tọa độ"
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        except (ValueError, TypeError) as e:
            print(f"DEBUG: Invalid coordinates: {e}")
            return Response({
                "ok": False,
                "error": "Tọa độ không hợp lệ"
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"DEBUG: Reverse geocoding error: {e}")
            return Response({
                "ok": False,
                "error": "Lỗi khi xác định địa điểm"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Fallback: Nếu không có tọa độ GPS
    return Response({
        "ok": False,
        "error": "Vui lòng cho phép trình duyệt truy cập vị trí GPS của bạn"
    }, status=status.HTTP_400_BAD_REQUEST)
# API DỰ BÁO AI (24H + 5 NGÀY) - ON-DEMAND
@api_view(['GET'])
def get_ai_forecast(request):
    """
    API lấy dự báo AI cho tỉnh/thành
    GET /api/weather/forecast/?location_id=X

    Logic:
    - Kiểm tra updated_at của forecast cuối cùng
    - Nếu hourly > 1h hoặc daily > 24h → XÓA toàn bộ → predict lại
    - Trả về dữ liệu forecast
    """
    location_id = request.query_params.get('location_id')
    if not location_id:
        return Response(
            {"error": "Thiếu tham số 'location_id'"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        location = get_object_or_404(Location, id=location_id)

        print(f"[DEBUG] Location: {location.city_name} (ID: {location.id})")

        # Lấy hoặc predict hourly (24h)
        hourly_forecasts = ForecastService.get_or_predict_hourly(location)
        hourly_data = HourlyForecastSerializer(hourly_forecasts, many=True).data

        print(f"[DEBUG] Hourly forecasts: {len(hourly_data)} records")

        # Lấy hoặc predict daily (5 ngày)
        daily_forecasts = ForecastService.get_or_predict_daily(location)
        daily_data = DailyForecastSerializer(daily_forecasts, many=True).data

        print(f"[DEBUG] Daily forecasts: {len(daily_data)} records")

        return Response({
            'location': {
                'id': location.id,
                'city_name': location.city_name,
                'latitude': location.latitude,
                'longitude': location.longitude
            },
            'hourly_forecast': hourly_data,
            'daily_forecast': daily_data
        })
    except Exception as e:
        print(f"[ERROR] get_ai_forecast: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
from math import radians, sin, cos, asin, sqrt


