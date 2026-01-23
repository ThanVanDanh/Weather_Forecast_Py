from django.contrib.auth import logout

# View cho admin logout chuyển về /login/
def admin_logout_to_login(request):
    logout(request)
    return redirect('/login/')
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
# Custom LoginView: nếu user là admin thì chuyển hướng sang /admin/
class CustomLoginView(LoginView):
    def form_valid(self, form):
        user = form.get_user()
        if user.is_superuser or user.is_staff:
            return redirect('/admin/')
        return super().form_valid(form)
from django.shortcuts import render, get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db.models import Q
import requests
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic.edit import CreateView
from .forms import RegisterForm
from .models import UserProfile
from django.contrib.auth.decorators import login_required
from .forms import UserUpdateForm, ProfileUpdateForm
from django.shortcuts import redirect

from .models import Location, CurrentWeatherCache, HourlyForecast, DailyForecast, WeatherAlert, SolarForecast
from .outfit_advisor import DBOutfitAdvisor
from .serializers import (
    LocationSerializer, FeaturedCitySerializer, HourlyForecastSerializer, DailyForecastSerializer
)
from .services import MeteoAPIService, ForecastService, SOLAR_LOCATION_TO_PROVINCE
import subprocess
import pandas as pd
from pathlib import Path

from .services import MeteoAPIService
from django.contrib.auth.views import (
    PasswordChangeView,
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView
)
def weather_dashboard(request):
    # Django sẽ tìm 'weather/dashboard.html' bên trong thư mục 'templates'
    return render(request, 'index.html')

@login_required(login_url='Weather_App:login_page')
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


# API LẤY TẤT CẢ TỈNH/THÀNH PHỐ (34 tỉnh)
@api_view(['GET'])
def get_all_locations(request):
    """
    API lấy danh sách tất cả 34 tỉnh/thành phố
    GET /api/weather/locations/
    """
    locations = Location.objects.filter(country_code='VN').order_by('city_name')
    serializer = LocationSerializer(locations, many=True)
    return Response(serializer.data)


# API 2: LẤY THỜI TIẾT HIỆN TẠI (DÙNG CACHE)
@api_view(['GET'])
def get_current_weather(request):
    import time
    from django.db import OperationalError

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
        # Retry logic để xử lý database locked
        max_retries = 5
        for attempt in range(max_retries):
            try:
                cache, _ = CurrentWeatherCache.objects.update_or_create(
                    location=location,
                    defaults={'data': new_data, 'last_updated': timezone.now()}
                )
                return Response(cache.data)
            except OperationalError as e:
                if 'database is locked' in str(e) and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 1.0  # Đợi 1s, 2s, 3s, 4s
                    print(f"[RETRY] Database locked, waiting {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    print(f"[ERROR] Database locked after {max_retries} retries")
                    raise  # Raise lại exception nếu hết retries hoặc lỗi khác
    else:
        return Response({"error": "Không thể lấy dữ liệu từ API"},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(['GET'])
def get_outfit_advice(request):
    """
    API trả về lời khuyên trang phục dựa trên dữ liệu DB (Daily/Hourly)
    URL: /api/weather/outfit/?location_id=1
    """
    location_id = request.query_params.get('location_id')

    if not location_id:
        return Response({'error': 'Thiếu location_id'}, status=status.HTTP_400_BAD_REQUEST)

    # Kiểm tra tồn tại + lấy location
    location = get_object_or_404(Location, id=location_id)

    try:
        # Đảm bảo có dữ liệu HourlyForecast để tư vấn theo độ ẩm & bức xạ
        # (Tránh race condition khi frontend gọi outfit song song với forecast)
        ForecastService.get_or_predict_hourly(location)

        # Gọi Class Advisor trong utils
        advisor = DBOutfitAdvisor(location_id=location_id)
        advice_text = advisor.get_advice()

        return Response({
            'status': 'success',
            'location_id': location_id,
            'advice': advice_text
        })
    except Exception as e:
        # Log lỗi ra console để debug nếu cần
        print(f"Lỗi gợi ý trang phục: {e}")
        return Response({'error': 'Lỗi xử lý gợi ý'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_solar_radiation(request):
    """
    API trả về dự báo bức xạ mặt trời cho tỉnh/thành
    URL: /api/weather/solar/?location_id=1

    Nếu chưa có dữ liệu, sẽ tự động chạy predict_solar_lstm_34.py
    """
    location_id = request.query_params.get('location_id')

    if not location_id:
        return Response({'error': 'Thiếu location_id'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        location_id = int(location_id)
        location = get_object_or_404(Location, id=location_id)

        # Lấy tên tỉnh từ mapping
        province_name = SOLAR_LOCATION_TO_PROVINCE.get(location_id)

        if not province_name:
            return Response({
                'status': 'error',
                'error': f'Chưa hỗ trợ dự báo bức xạ cho tỉnh này (ID: {location_id})'
            }, status=status.HTTP_404_NOT_FOUND)

        # Lấy / refresh dự báo từ DB (mỗi lần refresh sẽ xoá + tạo lại 0-23h của ngày hôm đó)
        target_date = timezone.localdate()
        forecasts = ForecastService.get_or_refresh_solar_daily(location, target_date=target_date, max_age_hours=1)

        values = [f.shortwave_radiation or 0 for f in forecasts]
        total_radiation = sum(values)
        avg_radiation = (total_radiation / len(values)) if values else 0
        max_radiation = max(values) if values else 0
        sunshine_hours = len([v for v in values if v > 100])

        # Ước tính sản lượng điện mặt trời (giả sử panel 5kW, hiệu suất 15%)
        # kWh = (W/m² * m² * hiệu suất * giờ) / 1000
        # Giả sử 20m² panel, hiệu suất 18%
        panel_area = 20  # m²
        efficiency = 0.18
        estimated_kwh = (total_radiation * panel_area * efficiency) / 1000

        # Đánh giá mức độ
        if avg_radiation > 400:
            rating = "Rất tốt"
            rating_color = "excellent"
        elif avg_radiation > 250:
            rating = "Tốt"
            rating_color = "good"
        elif avg_radiation > 100:
            rating = "Trung bình"
            rating_color = "average"
        else:
            rating = "Thấp"
            rating_color = "low"

        # Trả về dữ liệu (giữ format gần giống CSV: Time + Radiation_Forecast)
        hourly_data = []
        for f in forecasts:
            hourly_data.append({
                'Time': timezone.localtime(f.forecast_time).strftime('%Y-%m-%d %H:%M:%S'),
                'Radiation_Forecast': float(f.shortwave_radiation or 0),
            })

        return Response({
            'status': 'success',
            'location_id': location_id,
            'province': province_name,
            'city_name': location.city_name_vn or location.city_name,
            'summary': {
                'total_radiation_wh': round(total_radiation, 2),
                'avg_radiation_w': round(avg_radiation, 2),
                'max_radiation_w': round(max_radiation, 2),
                'sunshine_hours': sunshine_hours,
                'estimated_kwh': round(estimated_kwh, 2),
                'rating': rating,
                'rating_color': rating_color
            },
            'hourly_forecast': hourly_data
        })

    except Exception as e:
        print(f"[SOLAR] Lỗi: {e}")
        import traceback
        traceback.print_exc()
        return Response({
            'status': 'error',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_all_locations(request):
    """
    API trả về tất cả các tỉnh/thành phố (34 tỉnh)
    GET /api/weather/locations/
    """
    locations = Location.objects.filter(country_code='VN').order_by('city_name_vn')
    serializer = LocationSerializer(locations, many=True)
    return Response(serializer.data)


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
    city_name_vn = location.city_name_vn if location.city_name_vn else location.city_name
    context = {
        'location_id': location.id,
        'city_name': city_name_vn,
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

                if request.user.is_authenticated:
                    try:
                        # Lấy hoặc tạo profile nếu chưa có
                        profile, created = UserProfile.objects.get_or_create(user=request.user)

                        # Cập nhật thông tin
                        profile.latitude = lat
                        profile.longitude = lon
                        profile.address = display_name
                        profile.save()
                        print(f"DEBUG: Đã lưu vị trí cho user {request.user.username}")
                    except Exception as e:
                        print(f"ERROR: Không thể lưu vị trí vào profile: {e}")

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

# 1. VIEW ĐĂNG NHẬP
class CustomLoginView(LoginView):
    template_name = 'registration/login.html' # Trỏ vào file login riêng
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        messages.success(self.request, f"Chào mừng {user.username} quay trở lại!")
        if user.is_superuser or user.is_staff:
            return '/admin/'
        return reverse_lazy('Weather_App:dashboard')

    def form_invalid(self, form):
        messages.error(self.request, "Tên đăng nhập hoặc mật khẩu không đúng.")
        return super().form_invalid(form)

# 2. VIEW ĐĂNG KÝ
class CustomRegisterView(CreateView):
    form_class = RegisterForm
    template_name = 'registration/signup.html' # Trỏ vào file signup riêng
    success_url = reverse_lazy('Weather_App:login_page')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Đăng ký thành công! Vui lòng đăng nhập.")
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Đăng ký thất bại. Vui lòng kiểm tra lại thông tin.")
        return super().form_invalid(form)
# 3. VIEW ĐĂNG XUẤT (Có sẵn, chỉ cần gọi trong urls.py hoặc thừa kế nếu muốn custom)
class CustomLogoutView(LogoutView):
    next_page = 'Weather_App:login_page'

    def dispatch(self, request, *args, **kwargs):
        messages.info(request, "Bạn đã đăng xuất thành công.")
        return super().dispatch(request, *args, **kwargs)

# 1. VIEW ĐỔI MẬT KHẨU (User đang login muốn đổi pass)
class CustomPasswordChangeView(PasswordChangeView):
    template_name = 'registration/password_change.html'
    success_url = reverse_lazy('Weather_App:dashboard') # Đổi xong về trang chủ hoặc trang profile

    def form_valid(self, form):
        messages.success(self.request, "Mật khẩu đã được thay đổi thành công!")
        return super().form_valid(form)

# 2. CÁC VIEW QUÊN MẬT KHẨU (Quy trình 4 bước)

# Bước 1: Nhập Email
class CustomPasswordResetView(PasswordResetView):
    template_name = 'registration/password_reset_form.html'
    email_template_name = 'registration/password_reset_email.html'
    success_url = reverse_lazy('Weather_App:password_reset_done')

# Bước 2: Thông báo "Đã gửi email"
class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'registration/password_reset_done.html'

# Bước 3: Nhập mật khẩu mới (Sau khi bấm link trong mail)
class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'registration/password_reset_confirm.html'
    success_url = reverse_lazy('Weather_App:password_reset_complete')

# Bước 4: Thông báo hoàn tất
class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'registration/password_reset_complete.html'


@login_required
def profile_view(request):
    # Đảm bảo user luôn có profile (tránh lỗi nếu tạo user từ admin mà chưa có profile)
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, instance=profile)

        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Hồ sơ của bạn đã được cập nhật!')
            return redirect('Weather_App:profile')  # Load lại trang để thấy thay đổi
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=profile)

    context = {
        'u_form': u_form,
        'p_form': p_form,
        'profile': profile  # Truyền profile để hiển thị lat/lon dạng text (read-only)
    }
    return render(request, 'registration/profile.html', context)


# API CẢNH BÁO THỜI TIẾT CỰC ĐOAN
@api_view(['GET'])
def get_weather_alerts(request):
    """
    API lấy cảnh báo thời tiết cực đoan - Đọc từ database WeatherAlert
    GET /api/weather/alerts/?location_id=X
    """
    from .weather_alerts import get_weather_alerts as fetch_alerts

    location_id = request.GET.get('location_id')
    if not location_id:
        return Response({
            'status': 'error',
            'error': 'Thiếu location_id'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        location = Location.objects.get(id=location_id)
        # Truyền location object để có thể lưu/đọc từ database
        result = fetch_alerts(
            location.latitude,
            location.longitude,
            location_obj=location
        )
        return Response(result)
    except Location.DoesNotExist:
        return Response({
            'status': 'error',
            'error': 'Không tìm thấy địa điểm'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'status': 'error',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# API GỢI Ý TRANG PHỤC
@api_view(['GET'])
def get_outfit_advice(request):
    """
    API gợi ý trang phục theo thời tiết
    GET /api/weather/outfit/?location_id=X
    """
    location_id = request.GET.get('location_id')
    if not location_id:
        return Response({
            'status': 'error',
            'error': 'Thiếu location_id'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        location = Location.objects.get(id=location_id)

        # Sử dụng DBOutfitAdvisor để lấy gợi ý
        from .outfit_advisor import DBOutfitAdvisor
        advisor = DBOutfitAdvisor(location_id=location_id)
        advice = advisor.get_advice()

        return Response({
            'status': 'success',
            'advice': advice
        })

    except Location.DoesNotExist:
        return Response({
            'status': 'error',
            'error': 'Không tìm thấy địa điểm'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'status': 'error',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# API DỰ BÁO BỨC XẠ MẶT TRỜI
@api_view(['GET'])
def get_solar_radiation(request):
    """
    API dự báo bức xạ mặt trời và năng lượng điện mặt trời
    GET /api/weather/solar/?location_id=X
    """
    location_id = request.GET.get('location_id')
    if not location_id:
        return Response({
            'status': 'error',
            'error': 'Thiếu location_id'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        location = Location.objects.get(id=location_id)

        # Lấy dữ liệu hourly forecast có shortwave_radiation
        from .models import HourlyForecast
        from django.utils import timezone
        from datetime import timedelta

        now = timezone.localtime()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        forecasts = HourlyForecast.objects.filter(
            location=location,
            forecast_time__gte=today_start,
            forecast_time__lt=today_end,
            shortwave_radiation__isnull=False
        ).order_by('forecast_time')

        if not forecasts.exists():
            # Fallback: ước tính từ Open-Meteo
            import requests
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                'latitude': location.latitude,
                'longitude': location.longitude,
                'hourly': 'shortwave_radiation',
                'timezone': 'Asia/Ho_Chi_Minh',
                'forecast_days': 1
            }

            response = requests.get(url, params=params, timeout=10)
            if response.ok:
                data = response.json()
                hourly_radiation = data['hourly']['shortwave_radiation']

                # Tính toán
                avg_radiation = sum([r for r in hourly_radiation if r > 0]) / len([r for r in hourly_radiation if r > 0]) if any(r > 0 for r in hourly_radiation) else 0
                max_radiation = max(hourly_radiation)
                sunshine_hours = sum(1 for r in hourly_radiation if r > 100)

                # Ước tính kWh (giả sử hệ thống 1kW)
                # kWh = (tổng bức xạ W/m² * diện tích m² * hiệu suất) / 1000
                # Đơn giản: kWh ≈ (avg_radiation * sunshine_hours) / 1000
                estimated_kwh = (avg_radiation * sunshine_hours) / 1000

                # Đánh giá
                if avg_radiation >= 600:
                    rating = "Xuất sắc"
                    rating_color = "rating-excellent"
                elif avg_radiation >= 400:
                    rating = "Tốt"
                    rating_color = "rating-good"
                elif avg_radiation >= 200:
                    rating = "Trung bình"
                    rating_color = "rating-medium"
                else:
                    rating = "Thấp"
                    rating_color = "rating-low"

                return Response({
                    'status': 'success',
                    'summary': {
                        'avg_radiation_w': avg_radiation,
                        'max_radiation_w': max_radiation,
                        'sunshine_hours': sunshine_hours,
                        'estimated_kwh': estimated_kwh,
                        'rating': rating,
                        'rating_color': rating_color
                    },
                    'hourly': hourly_radiation
                })
            else:
                return Response({
                    'status': 'error',
                    'error': 'Không có dữ liệu bức xạ mặt trời'
                }, status=status.HTTP_404_NOT_FOUND)

        # Có dữ liệu từ database
        radiation_values = [f.shortwave_radiation for f in forecasts]
        avg_radiation = sum([r for r in radiation_values if r > 0]) / len([r for r in radiation_values if r > 0]) if any(r > 0 for r in radiation_values) else 0
        max_radiation = max(radiation_values)
        sunshine_hours = sum(1 for r in radiation_values if r > 100)
        estimated_kwh = (avg_radiation * sunshine_hours) / 1000

        if avg_radiation >= 600:
            rating = "Xuất sắc"
            rating_color = "rating-excellent"
        elif avg_radiation >= 400:
            rating = "Tốt"
            rating_color = "rating-good"
        elif avg_radiation >= 200:
            rating = "Trung bình"
            rating_color = "rating-medium"
        else:
            rating = "Thấp"
            rating_color = "rating-low"

        return Response({
            'status': 'success',
            'summary': {
                'avg_radiation_w': avg_radiation,
                'max_radiation_w': max_radiation,
                'sunshine_hours': sunshine_hours,
                'estimated_kwh': estimated_kwh,
                'rating': rating,
                'rating_color': rating_color
            },
            'hourly': radiation_values
        })

    except Location.DoesNotExist:
        return Response({
            'status': 'error',
            'error': 'Không tìm thấy địa điểm'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'status': 'error',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# API DỰ BÁO MƯA MINUTELY (60 PHÚT TỚI)
@api_view(['GET'])
def get_rain_forecast(request):
    """
    API dự báo mưa minutely cho 60 phút tới
    GET /api/weather/rain-forecast/?location_id=X
    Tự động refresh mỗi 15 phút
    """
    location_id = request.GET.get('location_id')
    if not location_id:
        return Response({
            'status': 'error',
            'error': 'Thiếu location_id'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        location = Location.objects.get(id=location_id)

        # Gọi rain forecast service (với cache 10 phút)
        from .rain_forecast import get_rain_forecast_minutely
        result = get_rain_forecast_minutely(
            location.latitude,
            location.longitude,
            location_obj=location  # Truyền location để sử dụng cache
        )

        return Response(result)

    except Location.DoesNotExist:
        return Response({
            'status': 'error',
            'error': 'Không tìm thấy địa điểm'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'status': 'error',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# API LỊCH SỬ TÌM KIẾM (THEO USER)
@api_view(['GET', 'POST', 'DELETE'])
def search_history_api(request):
    """
    API lịch sử tìm kiếm thời tiết (theo user đăng nhập)
    GET - Lấy danh sách lịch sử (10 mục gần nhất)
    POST - Lưu một lịch sử tìm kiếm mới
    DELETE - Xóa tất cả lịch sử của user
    """
    from .models import SearchHistory, Location
    from datetime import timedelta

    # Kiểm tra đăng nhập
    if not request.user.is_authenticated:
        return Response({
            'status': 'error',
            'error': 'Vui lòng đăng nhập để sử dụng tính năng này'
        }, status=status.HTTP_401_UNAUTHORIZED)

    user = request.user

    if request.method == 'GET':
        # Lấy lịch sử tìm kiếm của user (10 mục gần nhất, trong 30 ngày)
        thirty_days_ago = timezone.now() - timedelta(days=30)

        history = SearchHistory.objects.filter(
            user=user,
            searched_at__gte=thirty_days_ago
        ).select_related('location').order_by('-searched_at')[:10]

        history_data = []
        for item in history:
            history_data.append({
                'locationId': item.location.id,
                'cityName': item.location.city_name_vn or item.location.city_name,
                'temperature': item.temperature,
                'weatherCode': item.weather_code,
                'isDay': item.is_day,
                'timestamp': item.searched_at.isoformat()
            })

        return Response({
            'status': 'success',
            'history': history_data
        })

    elif request.method == 'POST':
        # Lưu lịch sử tìm kiếm mới
        location_id = request.data.get('location_id')
        temperature = request.data.get('temperature')
        weather_code = request.data.get('weather_code')
        is_day = request.data.get('is_day', True)

        if not location_id:
            return Response({
                'status': 'error',
                'error': 'Thiếu location_id'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            location = Location.objects.get(id=location_id)

            # Xóa lịch sử cũ của cùng location (tránh trùng lặp)
            SearchHistory.objects.filter(user=user, location=location).delete()

            # Tạo lịch sử mới
            history_item = SearchHistory.objects.create(
                user=user,
                location=location,
                temperature=temperature,
                weather_code=weather_code,
                is_day=is_day
            )

            # Giữ tối đa 10 mục - xóa các mục cũ nhất
            user_history = SearchHistory.objects.filter(user=user).order_by('-searched_at')
            if user_history.count() > 10:
                old_ids = list(user_history[10:].values_list('id', flat=True))
                SearchHistory.objects.filter(id__in=old_ids).delete()

            return Response({
                'status': 'success',
                'message': 'Đã lưu lịch sử tìm kiếm',
                'item': {
                    'locationId': location.id,
                    'cityName': location.city_name_vn or location.city_name,
                    'temperature': temperature,
                    'timestamp': history_item.searched_at.isoformat()
                }
            })

        except Location.DoesNotExist:
            return Response({
                'status': 'error',
                'error': 'Không tìm thấy địa điểm'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    elif request.method == 'DELETE':
        # Xóa tất cả lịch sử của user
        deleted_count, _ = SearchHistory.objects.filter(user=user).delete()
        return Response({
            'status': 'success',
            'message': f'Đã xóa {deleted_count} mục lịch sử'
        })