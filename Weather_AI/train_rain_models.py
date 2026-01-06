"""
FILE 1: TRAIN_RAIN.PY
Chức năng: Huấn luyện model LSTM và SARIMA cho 34 tỉnh
Output: Lưu model vào thư mục 'models/'
"""
import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Input
from tensorflow.keras.callbacks import EarlyStopping
from statsmodels.tsa.statespace.sarimax import SARIMAX
import warnings

warnings.filterwarnings('ignore')

# --- CẤU HÌNH ---
DATA_DIR = Path("data")  # Nơi chứa file csv {tinh}.csv
MODEL_DIR = Path("models")  # Nơi lưu model
MODEL_DIR.mkdir(exist_ok=True)

TARGET = "rain"  # Cột dữ liệu mục tiêu
WINDOW_SIZE = 72  # 72 giờ quá khứ để dự báo tương lai


# ============================
# 1. HÀM CHUẨN BỊ DỮ LIỆU
# ============================
def load_and_process_data(csv_path):
    df = pd.read_csv(csv_path)
    # Đảm bảo có cột time và rain
    if TARGET not in df.columns:
        raise ValueError(f"File {csv_path} thiếu cột '{TARGET}'")

    df['time'] = pd.to_datetime(df['time'])
    df = df.set_index('time').sort_index()
    # Resample theo giờ, điền 0 nếu thiếu (mưa thiếu data thường là không mưa)
    df = df.asfreq('h').fillna(0)
    return df[TARGET]


def create_sequences(data, window_size):
    X, y = [], []
    for i in range(len(data) - window_size):
        X.append(data[i:i + window_size])
        y.append(data[i + window_size])
    return np.array(X), np.array(y)


# ============================
# 2. TRAIN LSTM
# ============================
def train_lstm(province, data_series):
    print(f"[{province}] Dang train LSTM...")

    # Scale dữ liệu (0, 1) vì mưa không âm
    scaler = MinMaxScaler(feature_range=(0, 1))
    # Reshape (-1, 1) để khớp với scaler
    data_values = data_series.values.reshape(-1, 1)
    data_scaled = scaler.fit_transform(data_values)

    # Tạo dữ liệu train
    X, y = create_sequences(data_scaled, WINDOW_SIZE)

    # Reshape X cho LSTM [samples, time steps, features]
    # features = 1 (chỉ có mưa)

    model = Sequential([
        Input(shape=(WINDOW_SIZE, 1)),
        LSTM(64, return_sequences=False),  # Model đơn giản cho nhẹ
        Dropout(0.2),
        Dense(1, activation='relu')  # Relu để output >= 0 (mưa không âm)
    ])

    model.compile(optimizer='adam', loss='mse')

    # Early Stopping để tự dừng khi không học thêm được
    es = EarlyStopping(monitor='loss', patience=5, restore_best_weights=True)

    model.fit(X, y, epochs=20, batch_size=32, verbose=0, callbacks=[es])

    # Lưu Model và Scaler
    model.save(MODEL_DIR / f"{province}_lstm.keras")
    joblib.dump(scaler, MODEL_DIR / f"{province}_scaler.pkl")
    print(f"[{province}] -> Saved LSTM & Scaler.")


# ============================
# 3. TRAIN SARIMA
# ============================
def train_sarima(province, data_series):
    print(f"[{province}] Dang train SARIMA...")
    # Cấu hình đơn giản (1,0,1) x (0,0,1,24) để chạy nhanh
    # Thực tế cần auto_arima hoặc grid search
    try:
        model = SARIMAX(data_series,
                        order=(1, 0, 1),
                        seasonal_order=(0, 0, 1, 24),
                        enforce_stationarity=False,
                        enforce_invertibility=False)
        results = model.fit(disp=False)

        joblib.dump(results, MODEL_DIR / f"{province}_sarima.pkl")
        print(f"[{province}] -> Saved SARIMA.")
    except Exception as e:
        print(f"[{province}] Lỗi SARIMA: {e}")


# ============================
# MAIN LOOP
# ============================
def main():
    csv_files = list(DATA_DIR.glob("*.csv"))
    if not csv_files:
        print("Không tìm thấy file CSV nào trong thư mục data/")
        return

    print(f"Tìm thấy {len(csv_files)} tỉnh thành. Bắt đầu train...")

    for csv_path in csv_files:
        province = csv_path.stem  # Lấy tên file làm tên tỉnh
        try:
            data_series = load_and_process_data(csv_path)

            # Chỉ train nếu đủ dữ liệu
            if len(data_series) > WINDOW_SIZE * 2:
                train_lstm(province, data_series)
                train_sarima(province, data_series)
            else:
                print(f"[{province}] Dữ liệu quá ngắn, bỏ qua.")

        except Exception as e:
            print(f"ERROR tại {province}: {e}")

    print("\nHOÀN TẤT HUẤN LUYỆN TOÀN BỘ!")


if __name__ == "__main__":
    main()