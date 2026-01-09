"""
URL configuration for Weather_Project_Python project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from Weather_App import views as weather_views  # Import view render trang
urlpatterns = [
    path('admin/', admin.site.urls),

    # 1. Đường dẫn trang chủ (trang dashboard)
    path('', weather_views.weather_dashboard, name='home'),

    # 2. Đường dẫn cho tất cả API
    path('api/weather/', include('Weather_App.urls', namespace='weather_api')),
]
