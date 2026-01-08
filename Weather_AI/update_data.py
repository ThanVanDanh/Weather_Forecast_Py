import os
import time
import random
import requests
import pandas as pd
from tqdm import tqdm
from datetime import timedelta

DATA_DIR = "data"
API_ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
TIMEZONE = "Asia/Bangkok"

TARGET_END_DATE = "2026-01-01"

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

FIELDS = [
    "temperature_2m", "apparent_temperature", "relative_humidity_2m", "dewpoint_2m",
    "surface_pressure", "pressure_msl", "wind_speed_10m", "wind_direction_10m",
    "wind_gusts_10m", "cloudcover", "cloudcover_low", "cloudcover_mid", "cloudcover_high",
    "precipitation", "rain", "snowfall", "weathercode", "shortwave_radiation",
    "direct_radiation", "diffuse_radiation", "uv_index", "visibility",
]
HOURLY = ",".join(FIELDS)


def fetch_gap_data(lat, lon, start_date, end_date):
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": HOURLY,
        "timezone": TIMEZONE,
    }
    for attempt in range(5):
        try:
            r = requests.get(API_ARCHIVE, params=params, timeout=60)
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
            print(f"  Loi: {e}. Thu lai...")
            time.sleep(3)
    return None


if __name__ == "__main__":
    print(f"Bat dau va du lieu (Data Gap Filling) trong folder '{DATA_DIR}'...")

    files = [f for f in os.listdir(DATA_DIR) if f.endswith(".csv")]

    for filename in tqdm(files):
        province_name = filename.replace(".csv", "")
        file_path = os.path.join(DATA_DIR, filename)

        if province_name not in PROVINCE_COORDINATES:
            print(f"Bo qua {filename} (Khong co toa do)")
            continue

        lat, lon = PROVINCE_COORDINATES[province_name]

        try:
            df_old = pd.read_csv(file_path)
            time_col = df_old.columns[0]

            df_old[time_col] = pd.to_datetime(df_old[time_col])
            last_date_in_file = df_old[time_col].max()

            if last_date_in_file >= pd.to_datetime("2025-12-30"):
                continue

            print(f"\n{province_name}: Du lieu dung o {last_date_in_file}. Dang tai tiep...")

            start_date_fetch = (last_date_in_file + timedelta(days=1)).strftime("%Y-%m-%d")

            if pd.to_datetime(start_date_fetch) > pd.to_datetime(TARGET_END_DATE):
                continue

            df_new = fetch_gap_data(lat, lon, start_date_fetch, TARGET_END_DATE)

            if df_new is not None and not df_new.empty:
                df_new.rename(columns={"time": time_col}, inplace=True)

                df_combined = pd.concat([df_old, df_new], ignore_index=True)
                df_combined.drop_duplicates(subset=[time_col], keep='last', inplace=True)

                df_combined.to_csv(file_path, index=False)
                print(f"  Da noi them {len(df_new)} dong. Moi nhat: {df_combined[time_col].max()}")
            else:
                print("  Khong tai duoc du lieu moi.")

            time.sleep(random.uniform(1, 2))

        except Exception as e:
            print(f"Loi xu ly file {filename}: {e}")

    print("\nHOAN TAT CAP NHAT DU LIEU LICH SU!")