"""
Hệ thống cảnh báo thời tiết cực đoan và gợi ý phòng tránh
"""
import requests
from typing import Dict, List
from datetime import timedelta
from django.utils import timezone

OPENWEATHER_API_KEY = "9d9dfae9131f26975dfab658ed2b4d36"


def save_alerts_to_db(location_obj, alerts_data):
    """
    Lưu cảnh báo vào database WeatherAlert model
    Luôn lưu kể cả khi không có alerts (lưu marker để biết đã check)
    """
    from Weather_App.models import WeatherAlert
    
    saved_alerts = []
    now = timezone.now()
    
    # Xóa tất cả alerts cũ của location này trước
    WeatherAlert.objects.filter(location=location_obj).delete()
    
    if alerts_data:
        # Có alerts → lưu từng alert
        for alert in alerts_data:
            try:
                # Tạo unique ID từ location + alert type + ngày
                alert_id = f"{location_obj.id}_{alert['type']}_{now.strftime('%Y%m%d%H')}"
                
                # Tạo hoặc cập nhật alert
                alert_obj, created = WeatherAlert.objects.update_or_create(
                    api_alert_id=alert_id,
                    defaults={
                        'location': location_obj,
                        'event_name': alert['title'],
                        'description': ' | '.join(alert['advice']),
                        'start_time': now,
                        'end_time': now + timedelta(hours=1),  # Alert có hiệu lực 1 giờ
                    }
                )
                saved_alerts.append(alert_obj)
                print(f"[WeatherAlert] {'Tạo mới' if created else 'Cập nhật'} alert: {alert['title']}")
            except Exception as e:
                print(f"[WeatherAlert] Lỗi lưu alert: {e}")
                continue
    else:
        # Không có alerts → lưu marker "no_alerts" để biết đã check
        try:
            alert_id = f"{location_obj.id}_no_alerts_{now.strftime('%Y%m%d%H')}"
            alert_obj, created = WeatherAlert.objects.update_or_create(
                api_alert_id=alert_id,
                defaults={
                    'location': location_obj,
                    'event_name': 'Không có cảnh báo',
                    'description': 'Thời tiết bình thường, không có cảnh báo đặc biệt',
                    'start_time': now,
                    'end_time': now + timedelta(hours=1),  # Check lại sau 1 giờ
                }
            )
            print(f"[WeatherAlert] Lưu marker: Không có cảnh báo")
        except Exception as e:
            print(f"[WeatherAlert] Lỗi lưu no_alerts marker: {e}")
    
    return saved_alerts


def get_alerts_from_db(location_obj):
    """
    Lấy cảnh báo từ database WeatherAlert
    Trả về list rỗng nếu có marker "Không có cảnh báo"
    """
    from Weather_App.models import WeatherAlert
    
    now = timezone.now()
    alerts = []
    
    try:
        db_alerts = WeatherAlert.objects.filter(
            location=location_obj,
            start_time__lte=now,
            end_time__gte=now
        ).order_by('-start_time')
        
        # Kiểm tra xem có marker "Không có cảnh báo" không
        has_no_alert_marker = db_alerts.filter(event_name='Không có cảnh báo').exists()
        if has_no_alert_marker:
            print(f"[WeatherAlert] Tìm thấy marker: Không có cảnh báo")
            return []  # Trả về rỗng nhưng đã có trong DB
        
        # Chuyển đổi từ DB sang format frontend
        for alert in db_alerts:
            # Tìm type từ event_name
            alert_type = alert.event_name.lower().replace(' ', '_').replace('cảnh_báo_', '')
            
            # Lấy config từ SAFETY_ADVICE nếu có
            advice_config = SAFETY_ADVICE.get(alert_type, {})
            
            alerts.append({
                'type': alert_type,
                'title': alert.event_name,
                'level': advice_config.get('level', 'Cảnh báo'),
                'icon': advice_config.get('icon', 'fa-exclamation-triangle'),
                'color': advice_config.get('color', '#FF6B6B'),
                'advice': alert.description.split(' | '),
                'start_time': alert.start_time.strftime('%H:%M %d/%m'),
                'end_time': alert.end_time.strftime('%H:%M %d/%m')
            })
        
        return alerts
    except Exception as e:
        print(f"[WeatherAlert] Lỗi đọc DB: {e}")
        return None  # None = chưa có trong DB, [] = có trong DB nhưng rỗng


# Ngưỡng cảnh báo
THRESHOLDS = {
    'heat_wave': 35,      # Nhiệt độ >= 35°C
    'extreme_heat': 38,   # Nhiệt độ >= 38°C
    'cold_wave': 10,      # Nhiệt độ <= 10°C
    'extreme_cold': 5,    # Nhiệt độ <= 5°C
    'heavy_rain': 50,     # Mưa >= 50mm/h
    'extreme_rain': 100,  # Mưa >= 100mm/h
    'strong_wind': 40,    # Gió >= 40 km/h
    'storm_wind': 60,     # Gió >= 60 km/h
    'high_humidity': 85,  # Độ ẩm >= 85%
    'low_visibility': 1000, # Tầm nhìn <= 1km
}

# Gợi ý phòng tránh cho từng loại cảnh báo
SAFETY_ADVICE = {
    'heat_wave': {
        'icon': 'fa-temperature-arrow-up',
        'color': '#ff6b6b',
        'title': 'Cảnh báo nắng nóng',
        'level': 'Cao',
        'advice': [
            '☀️ Hạn chế ra ngoài từ 10h-16h',
            '💧 Uống nhiều nước, tránh đồ uống có cồn',
            '👕 Mặc quần áo mỏng, màu sáng',
            '🧴 Thường xuyên bôi kem chống nắng',
            '🏠 Sử dụng điều hòa hoặc quạt mát',
            '👶 Chú ý người già, trẻ em, phụ nữ mang thai'
        ]
    },
    'extreme_heat': {
        'icon': 'fa-fire',
        'color': '#d63031',
        'title': 'Cảnh báo nắng nóng cực đoan',
        'level': 'Rất cao',
        'advice': [
            '🚫 KHÔNG ra ngoài nếu không cần thiết',
            '💦 Uống nước mỗi 15-20 phút',
            '🏥 Gọi cấp cứu nếu có triệu chứng say nắng',
            '❄️ Tìm nơi có điều hòa để tránh nóng',
            '📱 Kiểm tra sức khỏe người thân',
            '🌡️ Theo dõi nhiệt độ cơ thể'
        ]
    },
    'cold_wave': {
        'icon': 'fa-temperature-arrow-down',
        'color': '#74b9ff',
        'title': 'Cảnh báo rét đậm',
        'level': 'Trung bình',
        'advice': [
            '🧥 Mặc nhiều lớp quần áo ấm',
            '🧣 Đội mũ, quấn khăn, đeo găng tay',
            '🔥 Sử dụng máy sưởi an toàn',
            '🏠 Giữ ấm trong nhà, tránh gió lùa',
            '🌾 Che chắn cây trồng, vật nuôi',
            '⚠️ Cẩn thận với sương muối, đường trơn'
        ]
    },
    'extreme_cold': {
        'icon': 'fa-snowflake',
        'color': '#0984e3',
        'title': 'Cảnh báo rét hại',
        'level': 'Cao',
        'advice': [
            '🏠 Ở trong nhà, hạn chế ra ngoài',
            '🔥 Đun sưởi liên tục, tránh CO',
            '💊 Chuẩn bị thuốc cảm, cúm',
            '📞 Liên hệ người thân thường xuyên',
            '🌾 Bảo vệ gia súc, cây trồng',
            '🏥 Tìm nơi trú ẩn nếu vô gia cư'
        ]
    },
    'heavy_rain': {
        'icon': 'fa-cloud-showers-heavy',
        'color': '#6c5ce7',
        'title': 'Cảnh báo mưa lớn',
        'level': 'Trung bình',
        'advice': [
            '🌂 Mang theo áo mưa, ô khi ra ngoài',
            '🚗 Lái xe chậm, cẩn thận đường ngập',
            '⚡ Tránh xa cột điện, dây điện',
            '🏠 Kiểm tra mái nhà, cống rãnh',
            '📱 Theo dõi tin tức về mưa lũ',
            '💼 Chuẩn bị đồ dùng khẩn cấp'
        ]
    },
    'extreme_rain': {
        'icon': 'fa-house-flood-water',
        'color': '#a29bfe',
        'title': 'Cảnh báo mưa lũ cực đoan',
        'level': 'Rất cao',
        'advice': [
            '🚫 KHÔNG đi qua vùng ngập sâu',
            '🏔️ Di chuyển lên nơi cao',
            '📦 Bảo vệ tài sản, giấy tờ quan trọng',
            '🔌 Ngắt điện, khóa gas',
            '📞 Gọi 113/114/115 khi cần hỗ trợ',
            '🚁 Sẵn sàng sơ tán nếu có lệnh'
        ]
    },
    'strong_wind': {
        'icon': 'fa-wind',
        'color': '#00b894',
        'title': 'Cảnh báo gió mạnh',
        'level': 'Trung bình',
        'advice': [
            '🏠 Chằng chống nhà cửa, mái tôn',
            '🌳 Tránh xa cây to, biển hiệu',
            '🚗 Cẩn thận khi lái xe, giữ vững tay lái',
            '⚓ Buộc chặt thuyền bè, neo đậu an toàn',
            '📱 Cập nhật tin bão liên tục',
            '🪟 Đóng cửa sổ, cửa ra vào'
        ]
    },
    'storm_wind': {
        'icon': 'fa-hurricane',
        'color': '#d63031',
        'title': 'Cảnh báo bão',
        'level': 'Rất cao',
        'advice': [
            '🏠 Ở trong nhà, tránh xa cửa sổ',
            '💪 Gia cố nhà cửa bằng ván gỗ',
            '💧 Dự trữ nước, thức ăn, thuốc men',
            '🔋 Sạc đầy điện thoại, pin dự phòng',
            '📻 Nghe đài để cập nhật tin bão',
            '🚁 Sơ tán theo hướng dẫn chính quyền'
        ]
    },
    'thunderstorm': {
        'icon': 'fa-bolt',
        'color': '#fdcb6e',
        'title': 'Cảnh báo giông sét',
        'level': 'Cao',
        'advice': [
            '🏠 Trú ẩn trong nhà hoặc xe hơi',
            '🌳 KHÔNG trú dưới gốc cây',
            '⚡ Tránh xa vật kim loại, nước',
            '📱 Tắt thiết bị điện, rút phích cắm',
            '🏊 KHÔNG bơi lội, đánh cá',
            '⛰️ Xuống nơi trũng nếu ở ngoài trời'
        ]
    },
    'fog': {
        'icon': 'fa-smog',
        'color': '#b2bec3',
        'title': 'Cảnh báo sương mù',
        'level': 'Thấp',
        'advice': [
            '🚗 Bật đèn chiếu gần, giảm tốc độ',
            '👀 Giữ khoảng cách an toàn với xe phía trước',
            '📡 Sử dụng còi để báo hiệu',
            '🚫 Không đậu xe trên đường',
            '✈️ Kiểm tra chuyến bay trước khi đi',
            '⏰ Xuất phát sớm hơn dự định'
        ]
    },
    'high_humidity': {
        'icon': 'fa-droplet',
        'color': '#74b9ff',
        'title': 'Độ ẩm cao',
        'level': 'Thấp',
        'advice': [
            '💨 Sử dụng máy hút ẩm trong nhà',
            '🪟 Mở cửa sổ để thông gió',
            '👕 Phơi quần áo ở nơi khô ráo',
            '🧴 Bảo quản thực phẩm cẩn thận',
            '💊 Chú ý người bệnh tim mạch',
            '🏃 Hạn chế vận động mạnh'
        ]
    }
}


def get_weather_alerts(lat: float, lon: float, location_obj=None) -> Dict:
    """
    Lấy cảnh báo thời tiết - Ưu tiên từ database, fallback sang API
    """
    # Nếu có location_obj, kiểm tra database trước
    if location_obj:
        db_alerts = get_alerts_from_db(location_obj)
        
        # db_alerts = None → chưa có trong DB
        # db_alerts = [] → có trong DB nhưng rỗng (đã check, không có alerts)
        # db_alerts = [...] → có alerts
        if db_alerts is not None:  # Có trong DB (dù rỗng hay không)
            from Weather_App.models import WeatherAlert
            latest_check = WeatherAlert.objects.filter(
                location=location_obj,
                end_time__gte=timezone.now()
            ).order_by('-start_time').first()
            
            if latest_check and (timezone.now() - latest_check.start_time).total_seconds() < 3600:
                print(f"[WeatherAlert] Sử dụng từ database ({len(db_alerts)} alerts, check {int((timezone.now() - latest_check.start_time).total_seconds())}s trước)")
                return {
                    'status': 'success',
                    'alert_count': len(db_alerts),
                    'alerts': db_alerts,
                    'source': 'database'
                }
    
    # Nếu không có trong DB hoặc đã cũ (>1h), fetch mới từ API
    print(f"[WeatherAlert] Fetch alerts từ OpenWeatherMap API")
    result = _fetch_weather_alerts_from_api(lat, lon)
    
    # LUÔN lưu vào database, kể cả khi không có alerts
    if location_obj and result['status'] == 'success':
        save_alerts_to_db(location_obj, result['alerts'])
        result['source'] = 'api_and_saved'
    else:
        result['source'] = 'api'
    
    return result


def _fetch_weather_alerts_from_api(lat: float, lon: float) -> Dict:
    """
    Fetch cảnh báo từ OpenWeatherMap API (hàm nội bộ)
    """
    try:
        # Gọi One Call API 3.0
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            'lat': lat,
            'lon': lon,
            'appid': OPENWEATHER_API_KEY,
            'units': 'metric',
            'lang': 'vi'
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Phân tích dữ liệu và tạo cảnh báo
        alerts = []
        temp = data['main']['temp']
        humidity = data['main']['humidity']
        wind_speed = data['wind']['speed'] * 3.6  # m/s -> km/h
        visibility = data.get('visibility', 10000)  # meters
        weather_main = data['weather'][0]['main'].lower()
        
        # Kiểm tra nhiệt độ
        if temp >= THRESHOLDS['extreme_heat']:
            alerts.append({
                'type': 'extreme_heat',
                **SAFETY_ADVICE['extreme_heat'],
                'value': f"{temp:.1f}°C"
            })
        elif temp >= THRESHOLDS['heat_wave']:
            alerts.append({
                'type': 'heat_wave',
                **SAFETY_ADVICE['heat_wave'],
                'value': f"{temp:.1f}°C"
            })
        elif temp <= THRESHOLDS['extreme_cold']:
            alerts.append({
                'type': 'extreme_cold',
                **SAFETY_ADVICE['extreme_cold'],
                'value': f"{temp:.1f}°C"
            })
        elif temp <= THRESHOLDS['cold_wave']:
            alerts.append({
                'type': 'cold_wave',
                **SAFETY_ADVICE['cold_wave'],
                'value': f"{temp:.1f}°C"
            })
        
        # Kiểm tra gió
        if wind_speed >= THRESHOLDS['storm_wind']:
            alerts.append({
                'type': 'storm_wind',
                **SAFETY_ADVICE['storm_wind'],
                'value': f"{wind_speed:.0f} km/h"
            })
        elif wind_speed >= THRESHOLDS['strong_wind']:
            alerts.append({
                'type': 'strong_wind',
                **SAFETY_ADVICE['strong_wind'],
                'value': f"{wind_speed:.0f} km/h"
            })
        
        # Kiểm tra mưa
        if 'rain' in data and '1h' in data['rain']:
            rain_1h = data['rain']['1h']
            if rain_1h >= THRESHOLDS['extreme_rain']:
                alerts.append({
                    'type': 'extreme_rain',
                    **SAFETY_ADVICE['extreme_rain'],
                    'value': f"{rain_1h:.0f} mm/h"
                })
            elif rain_1h >= THRESHOLDS['heavy_rain']:
                alerts.append({
                    'type': 'heavy_rain',
                    **SAFETY_ADVICE['heavy_rain'],
                    'value': f"{rain_1h:.0f} mm/h"
                })
        
        # Kiểm tra giông
        if weather_main == 'thunderstorm':
            alerts.append({
                'type': 'thunderstorm',
                **SAFETY_ADVICE['thunderstorm'],
                'value': 'Đang có giông'
            })
        
        # Kiểm tra sương mù
        if visibility <= THRESHOLDS['low_visibility']:
            alerts.append({
                'type': 'fog',
                **SAFETY_ADVICE['fog'],
                'value': f"{visibility} m"
            })
        
        # Kiểm tra độ ẩm
        if humidity >= THRESHOLDS['high_humidity']:
            alerts.append({
                'type': 'high_humidity',
                **SAFETY_ADVICE['high_humidity'],
                'value': f"{humidity}%"
            })
        
        return {
            'status': 'success',
            'alert_count': len(alerts),
            'alerts': alerts,
            'current_conditions': {
                'temp': temp,
                'humidity': humidity,
                'wind_speed': wind_speed,
                'visibility': visibility,
                'weather': data['weather'][0]['description']
            }
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'alert_count': 0,
            'alerts': []
        }
