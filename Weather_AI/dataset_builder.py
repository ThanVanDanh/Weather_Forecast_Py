import os
import time
import random
import requests
import pandas as pd
from tqdm import tqdm


PROVINCE_COORDINATES = {
    "Tuyen_Quang": (21.82356, 105.21424),
    "Lao_Cai": (21.72000, 104.91000),
    "Thai_Nguyen": (21.59000, 105.85000),
    "Phu_Tho": (21.32000, 105.40000),
    "Bac_Ninh": (21.27000, 106.20000),
    "Hung_Yen": (20.64637, 106.05112),
    "Hai_Phong": (20.86000, 106.68000),
    "Ninh_Binh": (20.25809, 105.97965),
    "Quang_Tri": (17.46594, 106.59840),
    "Da_Nang": (16.07000, 108.22000),
    "Quang_Ngai": (15.12047, 108.79232),
    "Gia_Lai": (13.78297, 109.21966),
    "Khanh_Hoa": (12.24510, 109.19400),
    "Lam_Dong": (11.95000, 108.44000),
    "Dak_Lak": (12.67000, 108.04000),
    "TP_Ho_Chi_Minh": (10.82000, 106.63000),
    "Dong_Nai": (10.94000, 106.82000),
    "Tay_Ninh": (10.54000, 106.41000),
    "Can_Tho": (10.04000, 105.79000),
    "Vinh_Long": (10.25000, 105.97000),
    "Dong_Thap": (10.36000, 106.36000),
    "Ca_Mau": (9.18000, 105.15000),
    "An_Giang": (10.01000, 105.08000),
    "Ha_Noi": (21.02000, 105.84000),
    "Hue": (16.46000, 107.60000),
    "Lai_Chau": (22.39922, 103.44532),
    "Dien_Bien": (21.38602, 103.02301),
    "Son_La": (21.32725, 103.90918),
    "Lang_Son": (21.85000, 106.76000),
    "Quang_Ninh": (20.95050, 107.07300),
    "Thanh_Hoa": (19.80669, 105.78518),
    "Nghe_An": (18.67958, 105.68133),
    "Ha_Tinh": (18.35595, 105.88775),
    "Cao_Bang": (22.66556, 106.26067),
}

# ==========================
# API & FIELDS
# ==========================

API = "https://archive-api.open-meteo.com/v1/archive"
TIMEZONE = "Asia/Bangkok"

FIELDS = [
    "temperature_2m",
    "apparent_temperature",
    "relative_humidity_2m",
    "dewpoint_2m",
    "surface_pressure",
    "pressure_msl",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    "cloudcover",
    "cloudcover_low",
    "cloudcover_mid",
    "cloudcover_high",
    "precipitation",
    "rain",
    "snowfall",
    "weathercode",
    "shortwave_radiation",
    "direct_radiation",
    "diffuse_radiation",
    "uv_index",
    "visibility",
]
HOURLY = ",".join(FIELDS)

os.makedirs("data", exist_ok=True)


# ==========================
# Hàm xử lý retry 429
# ==========================

def fetch_with_retry(params, max_retry=5):
    for attempt in range(max_retry):
        try:
            r = requests.get(API, params=params, timeout=120)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.HTTPError as e:
            if "429" in str(e):
                wait = 5 + attempt * 3
                print(f" → 429 Too Many Requests — chờ {wait}s rồi thử lại...")
                time.sleep(wait)
            else:
                raise
        except Exception as e:
            wait = 5 + attempt * 3
            print(f" → Lỗi khác ({e}) — chờ {wait}s rồi thử lại...")
            time.sleep(wait)
    raise Exception("Không thể lấy dữ liệu sau nhiều lần retry")


# ==========================
# Hàm lấy 1 phát 3 năm
# ==========================

def fetch_full_dataset(lat, lon):
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": "2022-01-01",
        "end_date": "2026-01-01",
        "hourly": HOURLY,
        "timezone": TIMEZONE,
    }

    data = fetch_with_retry(params)

    hourly = data["hourly"]
    # Khởi tạo DataFrame với cột time
    df = pd.DataFrame({"time": hourly["time"]})

    # Thêm đầy đủ tất cả field đúng tên trong FIELDS
    for field in FIELDS:
        df[field] = hourly.get(field)

    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").asfreq("H")
    df = df.ffill().bfill()
    return df


# ==========================
# Main
# ==========================

if __name__ == "__main__":
    print("=== Dataset AI (full exogenous, tránh 429) ===")

    for province, (lat, lon) in tqdm(PROVINCE_COORDINATES.items()):
        try:
            df = fetch_full_dataset(lat, lon)
            # #Cộng tổng bức xạ các giờ lại thành 1 ngày
            # df_daily = df.resample('D').sum()
            # Đổi tên file cho gọn, không có dấu cách
            filename = f"{province}.csv"
            df.to_csv(os.path.join("data_test", filename), index_label="time")
            # df_daily.to_csv(os.path.join("data_test", filename), index_label="time")
            print(f"✔ {province}: {len(df)} dòng")
        except Exception as e:
            print(f"❌ Lỗi {province}: {e}")

        # Nghỉ RANDOM nhẹ để tránh bị đánh dấu spam
        time.sleep(random.uniform(1.5, 3.0))

    print("\n🎉 DONE!")
