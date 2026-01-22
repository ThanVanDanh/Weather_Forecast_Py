import os
import time
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
API_URL = "https://archive-api.open-meteo.com/v1/archive"
TIMEZONE = "Asia/Ho_Chi_Minh"

FIELDS = [
    "temperature_2m", "apparent_temperature", "relative_humidity_2m", "dewpoint_2m",
    "surface_pressure", "pressure_msl", "wind_speed_10m", "wind_direction_10m",
    "wind_gusts_10m", "cloudcover", "cloudcover_low", "cloudcover_mid", "cloudcover_high",
    "precipitation", "rain", "snowfall", "weathercode", "shortwave_radiation",
    "direct_radiation", "diffuse_radiation", "uv_index", "visibility",
]

PROVINCE_COORDINATES = {
    "Tuyen_Quang": (21.82356, 105.21424), "Lao_Cai": (21.72000, 104.91000),
    "Thai_Nguyen": (21.59000, 105.85000), "Phu_Tho": (21.32000, 105.40000),
    "Bac_Ninh": (21.27000, 106.20000), "Hung_Yen": (20.64637, 106.05112),
    "Hai_Phong": (20.86000, 106.68000), "Ninh_Binh": (20.25809, 105.97965),
    "Quang_Tri": (17.46594, 106.59840), "Da_Nang": (16.07000, 108.22000),
    "Quang_Ngai": (15.12047, 108.79232), "Gia_Lai": (13.78297, 109.21966),
    "Khanh_Hoa": (12.24510, 109.19400), "Lam_Dong": (11.95000, 108.44000),
    "Dak_Lak": (12.67000, 108.04000), "TP_Ho_Chi_Minh": (10.82000, 106.63000),
    "Dong_Nai": (10.94000, 106.82000), "Tay_Ninh": (10.54000, 106.41000),
    "Can_Tho": (10.04000, 105.79000), "Vinh_Long": (10.25000, 105.97000),
    "Dong_Thap": (10.36000, 106.36000), "Ca_Mau": (9.18000, 105.15000),
    "An_Giang": (10.01000, 105.08000), "Ha_Noi": (21.02000, 105.84000),
    "Hue": (16.46000, 107.60000), "Lai_Chau": (22.39922, 103.44532),
    "Dien_Bien": (21.38602, 103.02301), "Son_La": (21.32725, 103.90918),
    "Lang_Son": (21.85000, 106.76000), "Quang_Ninh": (20.95050, 107.07300),
    "Thanh_Hoa": (19.80669, 105.78518), "Nghe_An": (18.67958, 105.68133),
    "Ha_Tinh": (18.35595, 105.88775), "Cao_Bang": (22.66556, 106.26067),
}


def fetch_missing_data(lat, lon, start_date, end_date):
    """Gọi API lấy dữ liệu thiếu"""
    params = {
        "latitude": lat, "longitude": lon,
        "start_date": start_date, "end_date": end_date,
        "hourly": ",".join(FIELDS), "timezone": TIMEZONE,
    }
    
    for attempt in range(3):
        try:
            r = requests.get(API_URL, params=params, timeout=60)
            if r.status_code == 429:
                time.sleep(5 + attempt * 2)
                continue
            r.raise_for_status()
            
            data = r.json()
            hourly = data["hourly"]
            df = pd.DataFrame({"time": hourly["time"]})
            for field in FIELDS:
                df[field] = hourly.get(field)
            df["time"] = pd.to_datetime(df["time"])
            return df
            
        except Exception as e:
            print(f"  ⚠️ Lỗi API (attempt {attempt+1}): {e}")
            time.sleep(3)
    
    return None


def check_and_update_province(province_name):
    csv_path = DATA_DIR / f"{province_name}.csv"
    if province_name not in PROVINCE_COORDINATES:
        return False
    
    lat, lon = PROVINCE_COORDINATES[province_name]
    now = datetime.now()
    current_hour = now.replace(minute=0, second=0, microsecond=0)
    
    if not csv_path.exists():
        return False
    
    df = pd.read_csv(csv_path)
    time_col = df.columns[0]
    df[time_col] = pd.to_datetime(df[time_col])
    last_time = df[time_col].max()
    
    hours_behind = (current_hour - last_time).total_seconds() / 3600
    
    if hours_behind < 1:
        return True
    
    start_date = (last_time + timedelta(hours=1)).strftime("%Y-%m-%d")
    end_date = now.strftime("%Y-%m-%d")
    
    new_data = fetch_missing_data(lat, lon, start_date, end_date)
    
    if new_data is None or new_data.empty:
        return False
    
    new_data = new_data[new_data["time"] <= current_hour]
    
    if new_data.empty:
        return False
    
    new_data.rename(columns={"time": time_col}, inplace=True)
    df_combined = pd.concat([df, new_data], ignore_index=True)
    df_combined.drop_duplicates(subset=[time_col], keep='last', inplace=True)
    df_combined = df_combined.sort_values(time_col).reset_index(drop=True)
    
    df_combined.to_csv(csv_path, index=False)

    return True


def check_and_update_all():

    success_count = 0
    for province in PROVINCE_COORDINATES.keys():
        if check_and_update_province(province):
            success_count += 1
        time.sleep(0.5)
    
    return success_count == len(PROVINCE_COORDINATES)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        province = sys.argv[1]
        check_and_update_province(province)
    else:
        check_and_update_all()

