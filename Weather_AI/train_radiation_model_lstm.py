import os
import glob
import numpy as np
import pandas as pd
import joblib
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint

# ============================
# CẤU HÌNH (CONFIG)
# ============================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "model_solar_lstm"
# Đảm bảo thư mục tồn tại
MODEL_DIR.mkdir(parents=True, exist_ok=True)
MODEL_FILE = os.path.join(MODEL_DIR, "solar_lstm_angiang.keras")
SCALER_FILE = os.path.join(MODEL_DIR, "solar_scaler_angiang.pkl")


# CHỈ DÙNG BIẾN NỘI SINH (Univariate)
FEATURE_COLUMNS = ['shortwave_radiation']
TARGET_COLUMN = 'shortwave_radiation'

SEQ_LENGTH = 72  # 3 ngày quá khứ
PREDICT_HORIZON = 1  # Dự báo 1 giờ tiếp theo


# ============================
# 1. HÀM XỬ LÝ DỮ LIỆU
# ============================

def create_sequences_from_array(data, seq_length):
    """
    Hàm phụ: Cắt sequence từ 1 mảng numpy đơn lẻ
    """
    X, y = [], []
    if len(data) <= seq_length + PREDICT_HORIZON:
        return np.array([]), np.array([])

    for i in range(len(data) - seq_length - PREDICT_HORIZON):
        X.append(data[i:(i + seq_length)])
        y.append(data[i + seq_length + PREDICT_HORIZON - 1, 0])

    return np.array(X), np.array(y)


def load_and_process_data_angiang():
    """
    Chỉ tải và xử lý dữ liệu của tỉnh An Giang.
    """
    # 1. Tìm file An Giang
    all_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))

    # Lọc file: Chuyển về chữ thường và thay thế dấu _ bằng khoảng trắng để so sánh
    angiang_files = [f for f in all_files if "an giang" in os.path.basename(f).lower().replace("_", " ")]

    if not angiang_files:
        raise FileNotFoundError(f"❌ Không tìm thấy file CSV nào của An Giang trong {DATA_DIR}.")

    print(f"📂 Đã tìm thấy {len(angiang_files)} file dữ liệu cho An Giang:")
    for f in angiang_files:
        print(f"   - {os.path.basename(f)}")

    # 2. Đọc dữ liệu để fit Scaler
    df_list = []
    for file in angiang_files:
        df = pd.read_csv(file)
        if TARGET_COLUMN in df.columns:
            df_list.append(df[[TARGET_COLUMN]])

    if not df_list:
        raise ValueError("File tìm thấy nhưng không có cột shortwave_radiation!")

    full_df_temp = pd.concat(df_list, ignore_index=True).ffill().bfill()

    # 3. Fit Scaler
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaler.fit(full_df_temp.values)

    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(scaler, SCALER_FILE)
    print(f"💾 Đã lưu Scaler tại: {SCALER_FILE}")

    # 4. Tạo Sequence
    X_list, y_list = [], []

    for file in angiang_files:
        df = pd.read_csv(file)
        data_raw = df[[TARGET_COLUMN]].ffill().bfill().values
        data_scaled = scaler.transform(data_raw)

        # Tạo sequence
        X_part, y_part = create_sequences_from_array(data_scaled, SEQ_LENGTH)

        if len(X_part) > 0:
            X_list.append(X_part)
            y_list.append(y_part)

    if not X_list:
        raise ValueError("Dữ liệu quá ngắn để tạo sequence!")

    X_final = np.concatenate(X_list, axis=0)
    y_final = np.concatenate(y_list, axis=0)

    return X_final, y_final


# ============================
# 2. XÂY DỰNG & TRAIN MODEL
# ============================

def build_lstm_model(input_shape):
    model = Sequential()
    model.add(LSTM(64, return_sequences=True, input_shape=input_shape))
    model.add(Dropout(0.2))
    model.add(LSTM(32, return_sequences=False))
    model.add(Dropout(0.2))
    model.add(Dense(1))

    model.compile(optimizer='adam', loss='mse', metrics=['mae'])
    return model


def main():
    print("🔄 Bắt đầu xử lý dữ liệu cho AN GIANG...")
    try:
        X, y = load_and_process_data_angiang()
    except Exception as e:
        print(e)
        return

    print(f"✅ Kích thước tập dữ liệu An Giang - X: {X.shape}, y: {y.shape}")

    # Chia Train/Test
    # Với dữ liệu 1 tỉnh, ta KHÔNG nên shuffle để giữ tính thứ tự thời gian khi validate
    # Tuy nhiên, nếu file chứa nhiều năm nối tiếp, shuffle=False là bắt buộc để test tương lai.
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

    # Build Model
    model = build_lstm_model((X_train.shape[1], X_train.shape[2]))

    early_stop = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)
    checkpoint = ModelCheckpoint(MODEL_FILE, monitor='val_loss', save_best_only=True)

    print("🚀 Bắt đầu training model An Giang...")
    history = model.fit(
        X_train, y_train,
        epochs=30,  # Tăng epoch lên xíu vì data ít hơn
        batch_size=32,  # Giảm batch size vì data ít hơn
        validation_data=(X_test, y_test),
        callbacks=[early_stop, checkpoint],
        verbose=1
    )

    # Đánh giá
    loss, mae = model.evaluate(X_test, y_test)
    print(f"🏁 Kết quả Test (An Giang) - Loss: {loss:.5f}, MAE: {mae:.5f}")

    # Vẽ biểu đồ
    plt.figure(figsize=(10, 6))
    plt.plot(history.history['loss'], label='Train Loss')
    plt.plot(history.history['val_loss'], label='Val Loss')
    plt.title('Training Loss - An Giang Univariate')
    plt.legend()
    plt.savefig(os.path.join(MODEL_DIR, "training_history_angiang.png"))
    print(f"📊 Đã lưu biểu đồ tại {MODEL_DIR}")


if __name__ == "__main__":
    main()