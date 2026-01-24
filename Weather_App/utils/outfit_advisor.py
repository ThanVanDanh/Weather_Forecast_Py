# File: Weather_App/utils/outfit_advisor.py
from django.db.models import Max, Avg
from datetime import date
from Weather_App.models import HourlyForecast, DailyForecast, CurrentWeatherCache


class DBOutfitAdvisor:
    def __init__(self, location_id, target_date=None):
        self.location_id = location_id
        self.target_date = target_date or date.today()

    def get_advice(self):

        data = self._fetch_data()

        if data['temp_min'] is None or data['temp_max'] is None:
            return "Đang cập nhật dữ liệu thời tiết để đưa ra gợi ý trang phục..."

        base_advice = self._analyze_base_outfit(data['temp_min'], data['temp_max'])
        layering_advice = self._analyze_layering(data['temp_min'], data['temp_max'])
        sun_humid_advice = self._analyze_sun_and_heat(data['max_rad'], data['avg_hum'], data['temp_max'])

        full_advice = [
            base_advice,
            layering_advice,
            sun_humid_advice
        ]

        return " ".join([advice for advice in full_advice if advice])

    def _fetch_data(self):

        daily_record = DailyForecast.objects.filter(
            location_id=self.location_id,
            forecast_date=self.target_date
        ).first()

        hourly_stats = HourlyForecast.objects.filter(
            location_id=self.location_id,
            forecast_time__date=self.target_date
        ).aggregate(
            max_rad=Max('shortwave_radiation'),
            avg_hum=Avg('humidity')
        )

        temp_min = None
        temp_max = None

        if daily_record:
            temp_min = daily_record.temp_min
            temp_max = daily_record.temp_max
        else:
            cache = CurrentWeatherCache.objects.filter(location_id=self.location_id).first()
            if cache and isinstance(cache.data, dict):
                daily = cache.data.get('daily') or {}
                # Lấy phần tử đầu tiên
                mins = daily.get('temperature_2m_min')
                maxs = daily.get('temperature_2m_max')
                if mins and maxs:
                    temp_min = mins[0]
                    temp_max = maxs[0]

        return {
            'temp_min': temp_min,
            'temp_max': temp_max,
            'max_rad': hourly_stats.get('max_rad') or 0,
            'avg_hum': hourly_stats.get('avg_hum') or 0,
        }

    def _analyze_base_outfit(self, low, high):

        if high >= 35:
            return "Trời cực kỳ nóng bức. Hãy ưu tiên áo ba lỗ, áo phông cotton mỏng hoặc vải linen thoáng mát. Quần short là lựa chọn tốt nhất."
        elif high >= 30:
            return "Thời tiết nóng. Áo phông ngắn tay, sơ mi chất liệu mỏng nhẹ (voan, lụa) sẽ giúp bạn thoải mái."
        elif high >= 25:
            return "Nhiệt độ ấm áp. Bạn có thể mặc áo phông, áo polo kết hợp quần jeans hoặc váy."
        elif high >= 20:
            return "Trời mát mẻ. Một chiếc áo thun dài tay hoặc sơ mi dày dặn là vừa đủ."
        elif high >= 15:
            return "Trời se lạnh. Hãy mặc áo nỉ (sweatshirt), áo len mỏng hoặc khoác thêm áo cardigan."
        elif high >= 10:
            return "Trời lạnh. Cần mặc áo len dày, áo giữ nhiệt bên trong và quần dày."
        else:  # < 10 độ
            return "Trời rất rét. Hãy trang bị áo phao, áo đại hàn, khăn quàng cổ và găng tay để giữ ấm."

    def _analyze_layering(self, low, high):
        if low is None or high is None: return ""

        diff = high - low
        if diff >= 10:
            return f"Chênh lệch nhiệt độ lớn ({low:.0f}°C - {high:.0f}°C). Sáng sớm và đêm lạnh nhưng trưa nóng, hãy mặc nhiều lớp (áo thun trong, áo khoác ngoài) để dễ cởi bỏ."
        elif diff >= 8:
            return "Nhiệt độ thay đổi trong ngày, nên mang theo một chiếc áo khoác nhẹ đề phòng khi trời trở lạnh."
        return ""

    def _analyze_sun_and_heat(self, radiation, humidity, max_temp):
        parts = []
        if radiation > 800:
            parts.append("Nắng rất gắt, chỉ số UV cao. Đừng quên kính râm và bôi kem chống nắng kỹ càng.")
        elif radiation > 500:
            parts.append("Trời có nắng rõ, nên đội mũ nón khi ra ngoài trời lâu.")

        if max_temp > 28 and humidity > 80:
            parts.append("Độ ẩm cao gây cảm giác oi bức, nên chọn quần áo rộng rãi, thấm hút mồ hôi.")
        elif max_temp > 28 and humidity < 40:
            parts.append("Trời hanh khô, nhớ uống nhiều nước và dưỡng ẩm da.")

        elif max_temp < 20 and humidity < 50:
            parts.append("Trời lạnh và hanh khô, nên dùng kem dưỡng ẩm và son dưỡng.")

        return " ".join(parts)