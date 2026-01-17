import os
import sys
import django
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Weather_Project_Python.settings')
django.setup()

from django.utils import timezone
from Weather_App.models import Location
from predict_lstm_hourly_24h import predict_hourly_temperature
from predict_daily_5days_sarima import predict_daily_temperature

PROVINCES = [
    "Tuyen_Quang", "Lao_Cai", "Thai_Nguyen", "Phu_Tho", "Bac_Ninh",
    "Hung_Yen", "Hai_Phong", "Ninh_Binh", "Quang_Tri", "Da_Nang",
    "Quang_Ngai", "Gia_Lai", "Khanh_Hoa", "Lam_Dong", "Dak_Lak",
    "TP_Ho_Chi_Minh", "Dong_Nai", "Tay_Ninh", "Can_Tho", "Vinh_Long",
    "Dong_Thap", "Ca_Mau", "An_Giang", "Ha_Noi", "Hue", "Lai_Chau",
    "Dien_Bien", "Son_La", "Lang_Son", "Quang_Ninh", "Thanh_Hoa",
    "Nghe_An", "Ha_Tinh", "Cao_Bang"
]


def predict_all_hourly():
    """Dự báo 24h cho tất cả 34 tỉnh"""
    print(f"\n{'='*60}")
    print(f"🕐 BẮT ĐẦU DỰ BÁO 24H CHO 34 TỈNH - {timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    success = 0
    failed = []
    
    for province in PROVINCES:
        try:
            result = predict_hourly_temperature(province, steps=24)
            print(result)
            success += 1
        except Exception as e:
            error_msg = f"❌ {province}: {str(e)}"
            print(error_msg)
            failed.append(province)
    
    print(f"\n{'='*60}")
    print(f"✅ Hoàn tất: {success}/{len(PROVINCES)} tỉnh")
    if failed:
        print(f"❌ Lỗi: {', '.join(failed)}")
    print(f"{'='*60}\n")
    
    return success, failed


def predict_all_daily():
    """Dự báo 5 ngày cho tất cả 34 tỉnh"""
    print(f"\n{'='*60}")
    print(f"📅 BẮT ĐẦU DỰ BÁO 5 NGÀY CHO 34 TỈNH - {timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    success = 0
    failed = []
    
    for province in PROVINCES:
        try:
            result = predict_daily_temperature(province, steps=5)
            print(result)
            success += 1
        except Exception as e:
            error_msg = f"❌ {province}: {str(e)}"
            print(error_msg)
            failed.append(province)
    
    print(f"\n{'='*60}")
    print(f"✅ Hoàn tất: {success}/{len(PROVINCES)} tỉnh")
    if failed:
        print(f"❌ Lỗi: {', '.join(failed)}")
    print(f"{'='*60}\n")
    
    return success, failed


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Dự báo cho tất cả tỉnh thành')
    parser.add_argument('--type', choices=['hourly', 'daily', 'both'], default='both',
                        help='Loại dự báo: hourly (24h), daily (5 ngày), hoặc both')
    
    args = parser.parse_args()
    
    if args.type in ['hourly', 'both']:
        predict_all_hourly()
    
    if args.type in ['daily', 'both']:
        predict_all_daily()
