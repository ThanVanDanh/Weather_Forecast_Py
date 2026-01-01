import os
import glob
import time
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Input, Bidirectional
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
from concurrent.futures import ProcessPoolExecutor

# ============================
# CẤU HÌNH "HEAVY" - CHÍNH XÁC CAO
# ============================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models_solar_heavy"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

TARGET_COLUMN = 'shortwave_radiation'
SEQ_LENGTH = 168  # Nhìn lại 1 tuần (7 ngày)
PREDICT_HORIZON = 24
BATCH_SIZE = 512  # Batch vừa phải để hội tụ tốt hơn
EPOCHS = 70  # Train sâu
MAX_WORKERS =  6  # Tự động lấy số nhân CPU


def create_advanced_features(df):
    """Tạo features chuyên sâu cho Time Series"""
    df = df.copy()
    time_col = df.columns[0]
    df[time_col] = pd.to_datetime(df[time_col])
    # Sắp xếp theo thời gian để đảm bảo tính toán Lag/Rolling đúng
    df = df.sort_values(by=time_col).reset_index(drop=True)

    # 1. Cyclical Time Features
    df['hour_sin'] = np.sin(2 * np.pi * df[time_col].dt.hour / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df[time_col].dt.hour / 24)
    df['month_sin'] = np.sin(2 * np.pi * df[time_col].dt.month / 12)
    df['month_cos'] = np.cos(2 * np.pi * df[time_col].dt.month / 12)

    # 2. Lag Features (Quá khứ)
    # 24h trước, 48h trước, và 1 tuần trước (quan trọng)
    df['lag_24'] = df[TARGET_COLUMN].shift(24)
    df['lag_48'] = df[TARGET_COLUMN].shift(48)
    df['lag_168'] = df[TARGET_COLUMN].shift(168)

    # 3. Rolling Statistics (Xu hướng gần)
    # Trung bình và độ lệch chuẩn của 24h gần nhất
    df['rolling_mean_24'] = df[TARGET_COLUMN].shift(1).rolling(window=24).mean()
    df['rolling_std_24'] = df[TARGET_COLUMN].shift(1).rolling(window=24).std()


    feature_cols = [
        TARGET_COLUMN,
        'hour_sin', 'hour_cos', 'month_sin', 'month_cos',
        'lag_24', 'lag_48', 'lag_168',
        'rolling_mean_24', 'rolling_std_24'
    ]
    df = df[[time_col] + feature_cols]
    # Xóa NaN do shift và rolling tạo ra
    df = df.dropna().reset_index(drop=True)
    return df, feature_cols


def create_dataset(data, seq_len, horizon, target_idx):
    X, y = [], []
    for i in range(len(data) - seq_len - horizon + 1):
        X.append(data[i: i + seq_len])
        y.append(data[i + seq_len: i + seq_len + horizon, target_idx])
    return np.array(X), np.array(y)


def build_heavy_model(input_shape, output_shape):
    """
    Kiến trúc 2-Layer Bidirectional LSTM (ĐIỂM VÀNG CHO TIME SERIES)
    """
    model = Sequential([
        Input(shape=input_shape),

        # Layer 1: Giữ nguyên 128 units để "hứng" hết các đặc trưng (lag, rolling...)
        Bidirectional(LSTM(128, return_sequences=True)),
        Dropout(0.3),

        # Layer 2: Giữ lại lớp này để tổng hợp thông tin
        # Chú ý: return_sequences=False vì đây là lớp cuối cùng trước khi ra kết quả
        Bidirectional(LSTM(64, return_sequences=False)),
        Dropout(0.2),


        Dense(32, activation='relu'),
        Dense(output_shape)
    ])
    model.compile(optimizer='adam', loss='mse', metrics=['mae'])
    return model


def train_process(file_path):
    province_name = os.path.splitext(os.path.basename(file_path))[0]
    model_file = MODEL_DIR / f"{province_name}.keras"
    scaler_file = MODEL_DIR / f"{province_name}_scaler.pkl"

    if model_file.exists():
        return f"⏩ {province_name}: Đã có model."

    try:
        # Load & Feature Engineering
        raw_df = pd.read_csv(file_path)
        df, feature_cols = create_advanced_features(raw_df)

        # Scaling
        scaler = MinMaxScaler(feature_range=(0, 1))
        data_values = scaler.fit_transform(df[feature_cols].values)
        joblib.dump(scaler, scaler_file)

        # Split Data (Train 90% - Validation 10%)
        # Với dữ liệu 3 năm, 10% test là khoảng 3-4 tháng
        train_size = int(len(data_values) * 0.9)
        train_data = data_values[:train_size]
        val_data = data_values[train_size:]

        target_idx = feature_cols.index(TARGET_COLUMN)

        X_train, y_train = create_dataset(train_data, SEQ_LENGTH, PREDICT_HORIZON, target_idx)
        X_val, y_val = create_dataset(val_data, SEQ_LENGTH, PREDICT_HORIZON, target_idx)

        if len(X_train) == 0: return f"⚠️ {province_name}: Data quá ít."

        # Build & Train
        model = build_heavy_model((X_train.shape[1], X_train.shape[2]), PREDICT_HORIZON)

        # Callbacks thông minh
        early_stop = EarlyStopping(monitor='val_loss', patience=15, restore_best_weights=True)
        checkpoint = ModelCheckpoint(model_file, monitor='val_loss', save_best_only=True, verbose=0)
        # Giảm learning rate nếu loss không giảm sau 5 epoch
        reduce_lr = ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=5, min_lr=1e-6, verbose=0)

        model.fit(
            X_train, y_train,
            epochs=EPOCHS,
            batch_size=BATCH_SIZE,
            validation_data=(X_val, y_val),
            callbacks=[early_stop, checkpoint, reduce_lr],
            verbose=1
        )
        return f"✅ {province_name}: Train xong (Deep Model)."

    except Exception as e:
        return f"❌ {province_name}: Lỗi {str(e)}"


def main():
    # Tắt GPU ảo để ép chạy CPU đa nhân (multiprocessing) hiệu quả hơn
    import tensorflow as tf
    tf.config.set_visible_devices([], 'GPU')

    all_files = glob.glob(str(DATA_DIR / "*.csv"))
    print(f"🚀 Bắt đầu Train 'Heavy' Model cho {len(all_files)} tỉnh...")
    print(f"⚙️ Sử dụng {MAX_WORKERS} nhân CPU song song.")

    start = time.time()
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(train_process, all_files)
        for res in results:
            print(res)

    print(f"\n🏁 Hoàn tất huấn luyện sâu. Thời gian: {(time.time() - start) / 60:.1f} phút.")


if __name__ == "__main__":
    main()