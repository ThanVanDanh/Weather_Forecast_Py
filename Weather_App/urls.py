from django.urls import path
from . import views
from .views import locate_user

app_name = 'Weather_App'

urlpatterns = [
    # 1. API tìm kiếm Location (trả về ID, lat, lon...)
    # GET /api/weather/search/?city=Hanoi
    path('search/', views.get_location_search, name='api_search_location'),

    # 2. API lấy thời tiết hiện tại (theo ID)
    # GET /api/weather/current/?location_id=1
    path('current/', views.get_current_weather, name='api_current_weather'),

    # 3. API lấy các TP nổi bật
    # GET /api/weather/featured/
    path('featured/', views.get_featured_weather, name='api_featured_weather'),
    
    # 3.5. API lấy dự báo AI (24h + 5 ngày) - ON-DEMAND
    # GET /api/weather/forecast/?location_id=X
    path('forecast/', views.get_ai_forecast, name='api_ai_forecast'),
    
    # 4. URL cho trang chi tiết tỉnh
    # Sẽ khớp với các URL như /tinh/ha-noi/, /tinh/tuyen-quang/
    path('tinh/<slug:slug>/', views.province_view, name='province_detail'),

    #5. URL cho trang cảnh báo thời tiết
    # path('warning/', views.warning_view, name='api_weather_warning'),

    # 6. URL cho trang năng lượng mặt trời
    path('solar/', views.solar_energy_view, name='solar_energy'),

    # 7. URL cho trang chủ (dashboard)
    # (View này đã có trong views.py nhưng chưa được gán URL)
    path('', views.weather_dashboard, name='dashboard'),
    path("locate/", locate_user, name="locate_user"),
    
    # 7. URL cho trang chăm sóc khách hàng
    path('customer-care/', views.customer_care, name='customer_care'),

]
