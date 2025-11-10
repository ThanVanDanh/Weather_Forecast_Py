# weather/urls.py
from django.urls import path
from . import views


app_name = 'Weather_App'

urlpatterns = [
    # 1. API tìm kiếm Location (trả về ID, lat, lon...)
    # GET /api/weather/search/?city=Hanoi
    path('search/', views.get_location_search, name='api_search_location'),

    # 2. API lấy thời tiết hiện tại (theo ID)
    # GET /api/weather/current/?location_id=1
    path('current/', views.get_current_weather, name='api_current_weather'),

    # 3. API lấy dự báo AI (theo ID)
    # GET /api/weather/forecast/ai/?location_id=1
    path('forecast/ai/', views.get_ai_forecast, name='api_ai_forecast'),

    # 4. API lấy cảnh báo (theo ID)
    # GET /api/weather/alerts/?location_id=1
    path('alerts/', views.get_weather_alerts, name='api_weather_alerts'),

    # 5. API lấy các TP nổi bật
    # GET /api/weather/featured/
    path('featured/', views.get_featured_weather, name='api_featured_weather'),
]
