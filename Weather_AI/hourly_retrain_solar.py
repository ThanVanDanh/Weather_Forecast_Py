import os
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from tensorflow.keras.models import load_model
import tensorflow as tf

# ============================
# CẤU HÌNH RETRAIN & PREDICT
# ============================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models_heavy"
RESULT_DIR = BASE_DIR / "results_forecast"
RESULT_DIR.mkdir(exist_ok=True)

TARGET_COLUMN = 'shortwave_radiation'
SEQ_LENGTH = 168
PREDICT_HORIZON = 24


def create_advanced_features(df):
    """Phải giống hệt logic bên file Train"""
    df = df.copy()
    time_col = df.columns[0]
    df[time_col] = pd.to_datetime(df[time_col])
    df = df.sort_values(by=time_col).reset_index(drop=True)

    df['hour_sin'] = np.sin(2 * np.pi * df[time_col].dt.hour / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df[time_col].dt.hour / 24)
    df['month_sin'] = np.sin(2 * np.pi * df[time_col].dt.month / 12)
    df['month_cos'] = np.cos(2 * np.pi * df[time_col].dt.month / 12)

    df['lag_24'] = df[TARGET_COLUMN].shift(24)
    df['lag_48'] = df[TARGET_COLUMN].shift(48)
    df['lag_168'] = df[TARGET_COLUMN].shift(168)

    df['rolling_mean_24'] = df[TARGET_COLUMN].shift(1).rolling(window=24).mean()
    df['rolling_std_24'] = df[TARGET_COLUMN].shift(1).rolling(window=24).std()

    # Feature list
    feature_cols = [
        TARGET_COLUMN,
        'hour_sin', 'hour_cos', 'month_sin', 'month_cos',
        'lag_24', 'lag_48', 'lag_168',
        'rolling_mean_24', 'rolling_std_24'
    ]
    return df, feature_cols


def run_hourly_job(province_name):
    csv_path = DATA_DIR / f"{province_name}.csv"
    model_path = MODEL_DIR / f"{province_name}.keras"
    scaler_path = MODEL_DIR / f"{province_name}_scaler.pkl"

    if not model_path.exists():
        print(f"⚠️ {province_name}: Chưa có model.")
        return

    # 1. Load Resources
    try:
        model = load_model(model_path)
        scaler = joblib.load(scaler_path)
    except Exception as e:
        print(f"❌ {province_name}: Lỗi load file - {e}")
        return

    # 2. Load & Process Data Mới Nhất
    raw_df = pd.read_csv(csv_path)
    df, feature_cols = create_advanced_features(raw_df)

    # Cần đủ dữ liệu để tính lag 168 (1 tuần) + seq_len (1 tuần)
    min_req = SEQ_LENGTH + 168 + 24
    if len(df) < min_req:
        print(f"⚠️ {province_name}: Data chưa đủ dài.")
        return

    # Drop NaN để có data sạch cho việc train/predict
    clean_df = df.dropna().reset_index(drop=True)
    data_values = scaler.transform(clean_df[feature_cols].values)
    target_idx = feature_cols.index(TARGET_COLUMN)

    # ==========================================
    # PHẦN QUAN TRỌNG: RETRAIN (HỌC THÊM)
    # ==========================================
    # Lấy 14 ngày gần nhất để "ôn bài"
    tuning_window = 24 * 14
    tuning_data = data_values[-tuning_window:] if len(data_values) > tuning_window else data_values

    X_new, y_new = [], []
    for i in range(len(tuning_data) - SEQ_LENGTH - PREDICT_HORIZON + 1):
        X_new.append(tuning_data[i: i + SEQ_LENGTH])
        y_new.append(tuning_data[i + SEQ_LENGTH: i + SEQ_LENGTH + PREDICT_HORIZON, target_idx])

    if len(X_new) > 0:
        X_new = np.array(X_new)
        y_new = np.array(y_new)

        # Train nhẹ với Learning Rate rất nhỏ để tinh chỉnh, không làm hỏng kiến thức cũ
        optimizer = tf.keras.optimizers.Adam(learning_rate=1e-5)
        model.compile(optimizer=optimizer, loss='mse')

        # Train 5 epochs để cập nhật xu hướng mới nhất
        model.fit(X_new, y_new, epochs=5, batch_size=16, verbose=0)
        model.save(model_path)  # Lưu đè model đã khôn hơn

    # ==========================================
    # DỰ BÁO
    # ==========================================
    # Lấy chuỗi cuối cùng
    last_sequence = data_values[-SEQ_LENGTH:]
    input_seq = np.expand_dims(last_sequence, axis=0)

    pred_scaled = model.predict(input_seq, verbose=0)

    # Inverse Scale
    dummy = np.zeros((PREDICT_HORIZON, len(feature_cols)))
    dummy[:, target_idx] = pred_scaled.flatten()
    pred_values = scaler.inverse_transform(dummy)[:, target_idx]
    pred_values = np.maximum(pred_values, 0)  # Bức xạ không âm

    # Xuất file
    last_time = pd.to_datetime(raw_df.iloc[-1, 0])
    future_timeline = pd.date_range(start=last_time + pd.Timedelta(hours=1), periods=PREDICT_HORIZON, freq='h')

    result_df = pd.DataFrame({
        'Time': future_timeline,
        'Radiation_Forecast': pred_values,
        'Province': province_name
    })

    output_path = RESULT_DIR / f"forecast_{province_name}.csv"
    result_df.to_csv(output_path, index=False)
    print(f"--> ✅ {province_name}: Đã Retrain & Dự báo xong.")
#
#
# if __name__ == "__main__":
#     all_files = list(DATA_DIR.glob("*.csv"))
#     print(f"🚀 Bắt đầu cập nhật giờ & dự báo cho {len(all_files)} tỉnh...")
#     for f in all_files:
#         run_hourly_job(f.stem)