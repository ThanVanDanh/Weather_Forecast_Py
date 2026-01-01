import os
import glob
import time
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Input
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from concurrent.futures import ProcessPoolExecutor  # <--- Thư viện đa luồng

# ============================
# CẤU HÌNH "SIÊU TỐC"
# ============================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models_solar_multi_provinces"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

TARGET_COLUMN = 'shortwave_radiation'
SEQ_LENGTH = 72
PREDICT_HORIZON = 24

# --- BUFF CHỈ SỐ Ở ĐÂY ---
BATCH_SIZE = 32
EPOCHS = 50
MAX_WORKERS = 4  # Train 4 tỉnh cùng lúc (Buff CPU từ 17% -> ~70%)


# -------------------------

def process_datetime_features(df):
    df = df.copy()
    time_col = df.columns[0]  # Giả định cột đầu là time để chạy nhanh
    df[time_col] = pd.to_datetime(df[time_col])
    df = df.sort_values(by=time_col).reset_index(drop=True)
    df['hour'] = df[time_col].dt.hour
    df['month'] = df[time_col].dt.month
    df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
    df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
    df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
    return df[[TARGET_COLUMN, 'hour_sin', 'hour_cos', 'month_sin', 'month_cos']]


def create_dataset(X_scaled, y_scaled, seq_len, horizon):
    Xs, ys = [], []
    for i in range(len(X_scaled) - seq_len - horizon + 1):
        Xs.append(X_scaled[i: i + seq_len])
        ys.append(y_scaled[i + seq_len: i + seq_len + horizon, 0])
    return np.array(Xs), np.array(ys)


def train_one_province(file_path):
    province_name = os.path.splitext(os.path.basename(file_path))[0]
    model_file = MODEL_DIR / f"{province_name}.keras"

    # Nếu đã có model thì bỏ qua
    if model_file.exists():
        return f"⏩ {province_name}: Đã xong từ trước."

    scaler_x_file = MODEL_DIR / f"scaler_X_{province_name}.pkl"
    scaler_y_file = MODEL_DIR / f"scaler_Y_{province_name}.pkl"

    try:
        raw_df = pd.read_csv(file_path)
        if TARGET_COLUMN not in raw_df.columns: return f"⚠️ {province_name}: Lỗi cột."

        df = process_datetime_features(raw_df).ffill().bfill()
        data_values = df.values.astype('float32')  # Chuyển sang float32 cho nhẹ RAM

        train_size = int(len(data_values) * 0.9)
        train_data = data_values[:train_size]
        test_data = data_values[train_size:]

        scaler_X = MinMaxScaler(feature_range=(0, 1))
        scaler_Y = MinMaxScaler(feature_range=(0, 1))

        X_train_scaled = scaler_X.fit_transform(train_data)
        y_train_scaled = scaler_Y.fit_transform(train_data[:, 0].reshape(-1, 1))
        X_test_scaled = scaler_X.transform(test_data)
        y_test_scaled = scaler_Y.transform(test_data[:, 0].reshape(-1, 1))

        joblib.dump(scaler_X, scaler_x_file)
        joblib.dump(scaler_Y, scaler_y_file)

        X_train, y_train = create_dataset(X_train_scaled, y_train_scaled, SEQ_LENGTH, PREDICT_HORIZON)
        X_test, y_test = create_dataset(X_test_scaled, y_test_scaled, SEQ_LENGTH, PREDICT_HORIZON)

        if len(X_train) == 0: return f"⚠️ {province_name}: Không đủ data."


        model = Sequential([
            Input(shape=(X_train.shape[1], X_train.shape[2])),
            LSTM(128, return_sequences=False),
            Dropout(0.2),
            Dense(PREDICT_HORIZON)
        ])
        model.compile(optimizer='adam', loss='mse')

        early_stop = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)
        checkpoint = ModelCheckpoint(model_file, monitor='val_loss', save_best_only=True, verbose=0)

        model.fit(
            X_train, y_train,
            epochs=EPOCHS,
            batch_size=BATCH_SIZE,
            validation_data=(X_test, y_test),
            callbacks=[early_stop, checkpoint],
            verbose=1
        )
        return f"✅ {province_name}: Hoàn tất!"

    except Exception as e:
        return f"❌ {province_name}: Lỗi {str(e)}"


def main():
    # Fix lỗi đa luồng trên Windows
    import tensorflow as tf
    tf.config.set_visible_devices([], 'GPU')  # Tắt GPU ảo để tránh xung đột luồng

    all_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
    print(f"🚀 Bắt đầu chế độ 'Siêu Tốc' với {MAX_WORKERS} luồng song song...")

    start = time.time()

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(train_one_province, all_files)

        for res in results:
            print(res)

    print(f"\n🏁 TỔNG THỜI GIAN: {(time.time() - start) / 60:.1f} phút.")


if __name__ == "__main__":
    main()