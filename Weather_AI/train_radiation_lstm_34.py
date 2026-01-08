import os
import glob
import time
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from sklearn.preprocessing import MinMaxScaler
import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, LSTM, Dense, Dropout, Flatten, Concatenate
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models_solar_multi_provinces"
MODEL_DIR.mkdir(parents=True, exist_ok=True)


TARGET_COLUMN = 'shortwave_radiation'
SEQ_LENGTH = 72  # Lấy dữ liệu 3 ngày trong quá khứ
PREDICT_HORIZON = 24  # Dự đoán 1 ngày trong tương lai

EXOG_COLUMNS = [
    'temperature_2m',
    'relative_humidity_2m',
    'cloud_cover', 'cloudcover',
    'precipitation', 'rain',
    'wind_speed_10m'
]

# Tháng mưa
WET_MONTHS = {5, 6, 7, 8, 9, 10}

BATCH_SIZE = 32
EPOCHS = 100

# Tọa độ tính góc mặt trời
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


def calculate_solar_elevation(times, lat, lon):
    # tính góc chiếu
    lat_rad = np.radians(lat)
    doy = times.dt.dayofyear
    declination = np.radians(23.45 * np.sin(np.radians(360 / 365 * (doy - 81))))
    time_correction = 4 * (lon - 105)
    solar_time = times.dt.hour + times.dt.minute / 60 + time_correction / 60
    hour_angle = np.radians(15 * (solar_time - 12))

    sin_elevation = np.sin(lat_rad) * np.sin(declination) + \
                    np.cos(lat_rad) * np.cos(declination) * np.cos(hour_angle)
    elevation = np.degrees(np.arcsin(np.clip(sin_elevation, -1, 1)))
    return elevation


def process_datetime_features(df, province_name):
    df = df.copy()
    time_col = df.columns[0]
    df[time_col] = pd.to_datetime(df[time_col])
    df = df.sort_values(by=time_col).reset_index(drop=True)

    df['hour'] = df[time_col].dt.hour
    df['month'] = df[time_col].dt.month
    df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
    df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
    df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
    df['wet_season'] = df['month'].isin(WET_MONTHS).astype(np.float32)

    if province_name in PROVINCE_COORDINATES:
        lat, lon = PROVINCE_COORDINATES[province_name]
        df['solar_elevation'] = calculate_solar_elevation(df[time_col], lat, lon)
    else:
        df['solar_elevation'] = 0.0

    available_exog = [col for col in EXOG_COLUMNS if col in df.columns]
    feature_cols = [TARGET_COLUMN] + available_exog + [
        'hour_sin', 'hour_cos', 'month_sin', 'month_cos', 'wet_season',
        'solar_elevation'
    ]
    return df[feature_cols]

def create_dual_dataset(X_scaled, y_scaled, seq_len, horizon):
    X_past, X_future, ys = [], [], []
    total_len = len(X_scaled)

    for i in range(total_len - seq_len - horizon + 1):
        # Input 1: Quá khứ (Target + Exog)
        X_past.append(X_scaled[i: i + seq_len])
        # Input 2: Tương lai (Chỉ Exog, bỏ cột Target đầu tiên)
        future_window = X_scaled[i + seq_len: i + seq_len + horizon, 1:]
        X_future.append(future_window)
        # Output: Target thực tế
        ys.append(y_scaled[i + seq_len: i + seq_len + horizon, 0])

    return [np.array(X_past), np.array(X_future)], np.array(ys)

def train_one_province(file_path):
    province_name = os.path.splitext(os.path.basename(file_path))[0]
    model_file = MODEL_DIR / f"{province_name}.keras"
    scaler_x_file = MODEL_DIR / f"scaler_X_{province_name}.pkl"
    scaler_y_file = MODEL_DIR / f"scaler_Y_{province_name}.pkl"

    try:
        raw_df = pd.read_csv(file_path)
        if TARGET_COLUMN not in raw_df.columns:
            return f"⚠️ {province_name}: Thiếu cột {TARGET_COLUMN}."

        df = process_datetime_features(raw_df, province_name).ffill().bfill()
        data_values = df.values.astype('float32')

        train_size = int(len(data_values) * 0.9)
        train_data = data_values[:train_size]
        test_data = data_values[train_size:]

        scaler_X = MinMaxScaler(feature_range=(0, 1))
        scaler_Y = MinMaxScaler(feature_range=(0, 1))

        # Fit trên train, transform trên cả train và test
        X_train_scaled = scaler_X.fit_transform(train_data)
        y_train_scaled = scaler_Y.fit_transform(train_data[:, 0].reshape(-1, 1))

        X_test_scaled = scaler_X.transform(test_data)
        y_test_scaled = scaler_Y.transform(test_data[:, 0].reshape(-1, 1))

        # Lưu Scaler để dùng lúc dự báo
        joblib.dump(scaler_X, scaler_x_file)
        joblib.dump(scaler_Y, scaler_y_file)

        # 3. Tạo Dataset 2 đầu vào
        X_train, y_train = create_dual_dataset(X_train_scaled, y_train_scaled, SEQ_LENGTH, PREDICT_HORIZON)
        X_test, y_test = create_dual_dataset(X_test_scaled, y_test_scaled, SEQ_LENGTH, PREDICT_HORIZON)

        if len(y_train) == 0: return f"{province_name}: Không đủ dữ liệu để train."

        n_features = X_train_scaled.shape[1]  # Tổng số đặc trưng
        n_future_features = n_features - 1  # Đặc trưng tương lai (trừ target)

        # 4. Xây dựng Model (Dual-Input LSTM Architecture)
        #

        # Nhánh 1: Xử lý chuỗi Quá khứ (Past)
        input_past = Input(shape=(SEQ_LENGTH, n_features), name='input_past')
        x1 = LSTM(128, return_sequences=False)(input_past)
        x1 = Dropout(0.2)(x1)

        # Nhánh 2: Xử lý chuỗi Tương lai (Future)
        input_future = Input(shape=(PREDICT_HORIZON, n_future_features), name='input_future')
        x2 = Flatten()(input_future)
        x2 = Dense(64, activation='relu')(x2)

        # Hợp nhất (Concatenate)
        merged = Concatenate()([x1, x2])
        merged = Dense(64, activation='relu')(merged)
        output = Dense(PREDICT_HORIZON, name='output')(merged)

        model = Model(inputs=[input_past, input_future], outputs=output)
        model.compile(optimizer='adam', loss='mse')

        # 5. Training
        early_stop = EarlyStopping(monitor='val_loss', patience=15, restore_best_weights=True)
        checkpoint = ModelCheckpoint(model_file, monitor='val_loss', save_best_only=True, verbose=0)

        model.fit(
            X_train, y_train,
            epochs=EPOCHS,
            batch_size=BATCH_SIZE,
            validation_data=(X_test, y_test),
            callbacks=[early_stop, checkpoint],
            verbose=1
        )

        return f" {province_name}: Hoàn tất! (Features: {n_features})"

    except Exception as e:
        return f" {province_name}: Lỗi {str(e)}"


def main():
    try:
        tf.config.set_visible_devices([], 'GPU')
    except:
        pass

    all_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
    if not all_files:
        print(" Không tìm thấy file CSV")
        return
    TARGET_FILE_NAME = "Ha_Noi.csv"
    target_path = None
    if TARGET_FILE_NAME:
        for f in all_files:
            if TARGET_FILE_NAME in f:
                target_path = f
                break

    if target_path is None:
        target_path = all_files[0]
        print(
            f"️ Không tìm thấy '{TARGET_FILE_NAME}', chuyển sang chạy file đầu tiên: {os.path.basename(target_path)}")

    print(f" Đang train file: {os.path.basename(target_path)}")
    print("-" * 50)

    start_time = time.time()
    result = train_one_province(target_path)
    print("-" * 50)
    print(result)
    print(f" Thời gian chạy: {(time.time() - start_time) / 60:.2f} phút.")


if __name__ == "__main__":
    main()