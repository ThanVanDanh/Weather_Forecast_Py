# File: Weather_App/utils/outfit_advisor.py
from django.db.models import Max, Avg
from datetime import date
from Weather_App.models import HourlyForecast, DailyForecast, CurrentWeatherCache


class DBOutfitAdvisor:
    def __init__(self, location_id, target_date=None):
        self.location_id = location_id
        self.target_date = target_date or date.today()

    def get_advice(self):
        # 1. Lấy dữ liệu tổng quan nhiệt độ từ bảng Daily (Nhanh và chính xác biên độ)
        daily_record = DailyForecast.objects.filter(
            location_id=self.location_id,
            forecast_date=self.target_date
        ).first()

        # 2. Lấy dữ liệu chi tiết từ bảng Hourly (Bức xạ và Độ ẩm)
        # Lưu ý: Lấy bức xạ Max để cảnh báo nắng, Độ ẩm Avg để cảnh báo oi bức
        hourly_stats = HourlyForecast.objects.filter(
            location_id=self.location_id,
            forecast_time__date=self.target_date
        ).aggregate(
            max_rad=Max('shortwave_radiation'),
            avg_hum=Avg('humidity')
        )

        # Trích xuất dữ liệu nhiệt độ: ưu tiên DB, fallback sang cache Meteo (hôm nay)
        temp_min = None
        temp_max = None

        if daily_record:
            temp_min = daily_record.temp_min
            temp_max = daily_record.temp_max
        else:
            cache = CurrentWeatherCache.objects.filter(location_id=self.location_id).first()
            if cache and isinstance(cache.data, dict):
                daily = cache.data.get('daily') or {}
                mins = daily.get('temperature_2m_min') or []
                maxs = daily.get('temperature_2m_max') or []
                if len(mins) > 0 and len(maxs) > 0:
                    temp_min = mins[0]
                    temp_max = maxs[0]

        if temp_min is None or temp_max is None:
            return "Đang cập nhật dữ liệu để đưa ra gợi ý trang phục..."

        max_radiation = hourly_stats.get('max_rad') or 0
        avg_humidity = hourly_stats.get('avg_hum') or 0

        # 3. Chạy logic gợi ý
        advice_parts = []

        # --- Logic A: Nhiệt độ & Layering ---
        advice_parts.append(self._analyze_temp(temp_min, temp_max))

        # --- Logic B: Bức xạ (Thay thế UV) ---
        # Ngưỡng: > 800 W/m2 thường là nắng rất gắt
        if max_radiation > 800:
            advice_parts.append("Trời nắng gắt, bức xạ cao. Nhớ mang kính râm và thoa kem chống nắng.")
        elif max_radiation > 500:
            advice_parts.append("Trời có nắng, nên đội mũ khi ra ngoài.")

        # --- Logic C: Độ ẩm ---
        if avg_humidity > 85:
            advice_parts.append("Độ ẩm cao có thể gây oi bức, ưu tiên quần áo thoáng khí.")

        return " ".join(advice_parts)

    def _analyze_temp(self, low, high):
        """Phân tích biên độ nhiệt để gợi ý mặc nhiều lớp"""
        if low is None or high is None:
            return ""

        diff = high - low

        # Logic Layering (Quan trọng nhất để "Chăm sóc" người dùng)
        if diff >= 8:
            return (f"Chênh lệch nhiệt độ lớn ({low:.0f}°C - {high:.0f}°C). "
                    "Sáng se lạnh cần áo khoác, nhưng trưa nóng nên mặc áo phông bên trong để dễ cởi bỏ.")

        if high < 18:
            return "Trời rét cả ngày. Hãy mặc ấm (áo len, áo phao) và giữ ấm cổ."

        if high < 25:
            return "Thời tiết mát mẻ. Một chiếc áo khoác mỏng hoặc hoodie là lựa chọn tuyệt vời."

        if low > 27:
            return "Trời nóng cả ngày. Hãy chọn trang phục mỏng nhẹ, thấm hút mồ hôi."

        return "Nhiệt độ dễ chịu. Mặc trang phục thường ngày thoải mái."