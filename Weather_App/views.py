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
from .models_profile import UserProfile
from django.contrib.auth.decorators import login_required
from .forms import UserUpdateForm, ProfileUpdateForm
from django.shortcuts import redirect

from .models import Location, CurrentWeatherCache, HourlyForecast, DailyForecast, WeatherAlert
from .outfit_advisor import DBOutfitAdvisor
from .serializers import (
    LocationSerializer, FeaturedCitySerializer, HourlyForecastSerializer, DailyForecastSerializer
)
from .services import MeteoAPIService, ForecastService
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


# Mapping location ID sang tên tỉnh trong file predict_solar_lstm_34.py
LOCATION_TO_PROVINCE = {
    1: "An_Giang",
    2: "Bac_Ninh",
    3: "Ca_Mau",
    4: "Can_Tho",
    5: "Cao_Bang",
    6: "Da_Nang",
    7: "Dak_Lak",
    8: "Dien_Bien",
    9: "Dong_Nai",
    10: "Dong_Thap",
    11: "Ha_Noi",
    12: "Gia_Lai",
    13: "Hai_Phong",
    14: "Ha_Tinh",
    15: "Khanh_Hoa",
    16: "Lam_Dong",
    17: "Lang_Son",
    18: "Lao_Cai",
    19: "Lai_Chau",
    20: "Nghe_An",
    21: "Ninh_Binh",
    22: "Phu_Tho",
    23: "Quang_Ngai",
    24: "Quang_Ninh",
    25: "Quang_Tri",
    26: "Son_La",
    27: "Tay_Ninh",
    28: "Thai_Nguyen",
    29: "Hue",
    30: "TP_Ho_Chi_Minh",
    31: "Thanh_Hoa",
    32: "Tuyen_Quang",
    33: "Vinh_Long",
    34: "Hung_Yen",
}


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
        province_name = LOCATION_TO_PROVINCE.get(location_id)
        
        if not province_name:
            return Response({
                'status': 'error',
                'error': f'Chưa hỗ trợ dự báo bức xạ cho tỉnh này (ID: {location_id})'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Đường dẫn file kết quả
        BASE_DIR = Path(__file__).resolve().parent.parent
        RESULT_DIR = BASE_DIR / "Weather_AI" / "results_train_shortwave_radiation_lstm"
        forecast_file = RESULT_DIR / f"forecast_{province_name}.csv"
        
        # Kiểm tra file có tồn tại và còn mới không (< 1 giờ)
        need_predict = True
        if forecast_file.exists():
            import os
            file_mtime = os.path.getmtime(forecast_file)
            file_age_hours = (timezone.now().timestamp() - file_mtime) / 3600
            if file_age_hours < 1:  # File còn mới (< 1 giờ)
                need_predict = False
        
        # Nếu cần predict lại
        if need_predict:
            print(f"[SOLAR] Chạy predict cho {province_name}...")
            script_path = BASE_DIR / "Weather_AI" / "predict_solar_lstm_34.py"
            
            try:
                result = subprocess.run(
                    ['python', str(script_path), province_name],
                    capture_output=True,
                    text=True,
                    timeout=60,  # Timeout 60 giây
                    cwd=str(BASE_DIR / "Weather_AI")
                )
                
                if result.returncode != 0:
                    print(f"[SOLAR] Lỗi predict: {result.stderr}")
                    return Response({
                        'status': 'error',
                        'error': 'Không thể dự báo bức xạ',
                        'detail': result.stderr
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    
                print(f"[SOLAR] Predict thành công: {result.stdout}")
                
            except subprocess.TimeoutExpired:
                return Response({
                    'status': 'error',
                    'error': 'Timeout khi dự báo bức xạ'
                }, status=status.HTTP_504_GATEWAY_TIMEOUT)
            except Exception as e:
                print(f"[SOLAR] Lỗi subprocess: {e}")
                return Response({
                    'status': 'error', 
                    'error': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Đọc file kết quả
        if not forecast_file.exists():
            return Response({
                'status': 'error',
                'error': 'Không tìm thấy file dự báo'
            }, status=status.HTTP_404_NOT_FOUND)
        
        df = pd.read_csv(forecast_file)
        
        # ===== LƯU DỮ LIỆU BỨC XẠ VÀO DATABASE =====
        saved_count = 0
        for _, row in df.iterrows():
            try:
                forecast_time = pd.to_datetime(row['Time'])
                radiation_value = float(row['Radiation_Forecast'])
                
                # Kiểm tra xem bản ghi HourlyForecast đã tồn tại chưa
                existing_forecast = HourlyForecast.objects.filter(
                    location=location,
                    forecast_time=forecast_time
                ).first()
                
                if existing_forecast:
                    # Nếu đã tồn tại, chỉ cập nhật shortwave_radiation
                    existing_forecast.shortwave_radiation = radiation_value
                    existing_forecast.save(update_fields=['shortwave_radiation', 'updated_at'])
                    saved_count += 1
                else:
                    # Nếu chưa tồn tại, tạo mới với temperature mặc định = 0
                    # (Temperature sẽ được cập nhật sau khi gọi forecast API)
                    HourlyForecast.objects.create(
                        location=location,
                        forecast_time=forecast_time,
                        temperature=0,  # Giá trị tạm, sẽ được cập nhật sau
                        shortwave_radiation=radiation_value
                    )
                    saved_count += 1
                    
            except Exception as e:
                print(f"[SOLAR] Lỗi lưu bản ghi {row['Time']}: {e}")
                continue
        
        print(f"[SOLAR] Đã lưu {saved_count}/{len(df)} bản ghi bức xạ vào DB cho {province_name}")
        
        # Tính toán tổng kết
        total_radiation = df['Radiation_Forecast'].sum()
        avg_radiation = df['Radiation_Forecast'].mean()
        max_radiation = df['Radiation_Forecast'].max()
        
        # Tính số giờ nắng (bức xạ > 100 W/m²)
        sunshine_hours = len(df[df['Radiation_Forecast'] > 100])
        
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
        
        # Trả về dữ liệu
        hourly_data = df.to_dict('records')
        
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