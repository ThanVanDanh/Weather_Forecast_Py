import os
import time
import requests
import pandas as pd
from tqdm import tqdm
from datetime import datetime, timedelta

# --- CẤU HÌNH ---
# Thư mục lưu dữ liệu tương lai (để riêng biệt với dữ liệu huấn luyện)
OUTPUT_DIR = "data_future"
API_FORECAST = "https://api.open-meteo.com/v1/forecast"
TIMEZONE = "Asia/Bangkok"

# Cấu hình ngày: Bắt đầu từ ngày 23 (như trong ảnh của bạn)
# Bạn có thể sửa ngày này tùy ý
START_DATE_STR = "2026-01-23"
DAYS_TO_FETCH = 7  # Lấy dữ liệu cho 7 ngày tính từ ngày bắt đầu

# Danh sách tỉnh (Full)
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

# Các trường dữ liệu cần thiết cho mô hình
FIELDS = [
    "temperature_2m", "relative_humidity_2m",
    "cloudcover",  # API trả về cái này
    "precipitation", "rain", "wind_speed_10m"
]


def fetch_future_weather(lat, lon, start_date, end_date):
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(FIELDS),
        "timezone": TIMEZONE,
    }

    try:
        r = requests.get(API_FORECAST, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()

        hourly = data.get("hourly", {})
        if not hourly:
            return pd.DataFrame()

        df = pd.DataFrame(hourly)

        # Đổi tên cột time cho chuẩn
        if "time" in df.columns:
            df.rename(columns={"time": "Time"}, inplace=True)

        # Xử lý format thời gian
        df["Time"] = pd.to_datetime(df["Time"])

        # QUAN TRỌNG: Tạo cột cloud_cover (có underscore) từ cloudcover
        # Vì trong ảnh của bạn có cả cột cloud_cover
        if "cloudcover" in df.columns:
            df["cloud_cover"] = df["cloudcover"]

        return df

    except Exception as e:
        print(f"Lỗi API: {e}")
        return pd.DataFrame()


if __name__ == "__main__":
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # Tính toán ngày kết thúc
    start_dt = pd.to_datetime(START_DATE_STR)
    end_dt = start_dt + timedelta(days=DAYS_TO_FETCH)
    end_date_str = end_dt.strftime("%Y-%m-%d")

    print(f"--- BẮT ĐẦU TẢI DỮ LIỆU TƯƠNG LAI ---")
    print(f"Khoảng thời gian: {START_DATE_STR} đến {end_date_str}")
    print(f"Lưu tại thư mục: {OUTPUT_DIR}/")

    for province, (lat, lon) in tqdm(PROVINCE_COORDINATES.items()):

        df = fetch_future_weather(lat, lon, START_DATE_STR, end_date_str)

        if not df.empty:
            # Lưu file CSV
            file_path = os.path.join(OUTPUT_DIR, f"{province}.csv")
            df.to_csv(file_path, index=False)
            # print(f"Đã lưu: {province}") # Comment lại cho đỡ rối màn hình
        else:
            print(f"⚠️ {province}: Không lấy được dữ liệu.")

        # Nghỉ nhẹ để tránh spam API
        time.sleep(0.5)

    print(f"\n✅ HOÀN TẤT! Dữ liệu đã sẵn sàng trong thư mục '{OUTPUT_DIR}'.")
    print(f"Bạn có thể dùng các file này để chạy mô hình dự báo.")