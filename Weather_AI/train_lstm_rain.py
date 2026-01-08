# train_rain_forecast.py - Huấn luyện model dự báo mưa 5 ngày tới
"""
Model dự báo:
- Xác suất có mưa (0-100%)
- Lượng mưa dự kiến (mm)
"""
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping
import joblib
import warnings

warnings.filterwarnings('ignore')

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models_rain"
MODEL_DIR.mkdir(exist_ok=True)

# Cấu hình
LOOKBACK = 30  # Dùng 30 ngày để dự đoán 5 ngày tiếp theo
HORIZON = 5  # Dự báo 5 ngày


def prepare_rain_data(csv_path: Path):
    """
    Chuẩn bị dữ liệu mưa từ file CSV
    Returns: daily data với precipitation và weather_code
    """
    df = pd.read_csv(csv_path)
    df["time"] = pd.to_datetime(df["time"], format='mixed')
    df = df.set_index("time").sort_index()

    # Fill missing values
    df = df.fillna(method='ffill').fillna(method='bfill')

    # Đảm bảo frequency hourly
    df = df.asfreq("h", method='ffill')

    # Tính toán daily
    daily = df.resample("D").agg({
        'temperature_2m': ['max', 'min', 'mean'],
        'precipitation': 'sum',  # Tổng lượng mưa trong ngày
        'weathercode': 'max',  # Weather code cao nhất (thường là mưa lớn nhất)
        'relative_humidity_2m': 'mean',
        'surface_pressure': 'mean',
        'cloudcover': 'mean'
    })

    # Flatten columns
    daily.columns = ['temp_max', 'temp_min', 'temp_mean',
                     'precipitation', 'weather_code',
                     'humidity', 'pressure', 'cloudcover']

    # Tạo target: có mưa hay không (1 = có mưa, 0 = không mưa)
    daily['has_rain'] = (daily['precipitation'] > 0.1).astype(int)  # >0.1mm = có mưa

    # Tạo xác suất mưa dựa trên lượng mưa
    # Công thức: sigmoid-like transformation
    daily['rain_probability'] = daily['precipitation'].apply(
        lambda x: min(95, max(5, 100 * (1 - np.exp(-x / 10)))) if x > 0 else 0
    )

    return daily.astype(float)


def create_rain_sequences(data, lookback=30, horizon=5):
    """
    Tạo sequences để training
    X: [lookback days] → Y: [horizon days]
    """
    # Features để predict
    feature_cols = ['temp_max', 'temp_min', 'temp_mean',
                    'precipitation', 'humidity', 'pressure', 'cloudcover', 'has_rain']

    # Targets: precipitation và has_rain cho 5 ngày tới
    target_cols = ['precipitation', 'has_rain']

    X, Y = [], []

    for i in range(len(data) - lookback - horizon + 1):
        # Input: lookback ngày
        x_window = data[feature_cols].iloc[i:i + lookback].values

        # Output: horizon ngày (chỉ lấy precipitation và has_rain)
        y_window = data[target_cols].iloc[i + lookback:i + lookback + horizon].values

        X.append(x_window)
        Y.append(y_window)

    return np.array(X), np.array(Y)


def build_rain_model(input_shape, output_shape):
    """
    Build LSTM model cho dự báo mưa
    Input: (lookback, features)
    Output: (horizon, 2) - [precipitation, has_rain]
    """
    model = Sequential([
        LSTM(128, return_sequences=True, input_shape=input_shape),
        Dropout(0.2),
        LSTM(64, return_sequences=False),
        Dropout(0.2),
        Dense(64, activation='relu'),
        Dense(output_shape[0] * output_shape[1])
    ])

    model.compile(optimizer='adam', loss='mse', metrics=['mae'])
    return model


def train_province_rain(province: str):
    """
    Train model dự báo mưa cho 1 tỉnh
    """
    print(f"\n{'=' * 70}")
    print(f"TRAIN MƯA MODEL - {province}")
    print(f"{'=' * 70}\n")

    csv_path = DATA_DIR / f"{province}.csv"
    if not csv_path.exists():
        print(f"❌ Không tìm thấy file: {csv_path}")
        return

    # 1. Load và chuẩn bị dữ liệu
    print("📊 Đang load dữ liệu...")
    daily = prepare_rain_data(csv_path)
    print(f"   Tổng số ngày: {len(daily)}")
    print(f"   Số ngày có mưa: {daily['has_rain'].sum()} ({daily['has_rain'].mean() * 100:.1f}%)")
    print(f"   Lượng mưa TB/ngày: {daily['precipitation'].mean():.2f}mm")

    # 2. Scale dữ liệu
    print("\n🔧 Scaling dữ liệu...")
    feature_cols = ['temp_max', 'temp_min', 'temp_mean',
                    'precipitation', 'humidity', 'pressure', 'cloudcover', 'has_rain']

    scaler_X = MinMaxScaler()
    daily_scaled = daily.copy()
    daily_scaled[feature_cols] = scaler_X.fit_transform(daily[feature_cols])

    # Target scaler (chỉ cho precipitation và has_rain)
    target_cols = ['precipitation', 'has_rain']
    scaler_Y = MinMaxScaler()
    daily_scaled[target_cols] = scaler_Y.fit_transform(daily[target_cols])

    # 3. Tạo sequences
    print("🔨 Tạo training sequences...")
    X, Y = create_rain_sequences(daily_scaled, LOOKBACK, HORIZON)
    print(f"   X shape: {X.shape}")  # (samples, lookback, features)
    print(f"   Y shape: {Y.shape}")  # (samples, horizon, 2)

    # Reshape Y để phù hợp với model output
    Y_flat = Y.reshape(Y.shape[0], -1)  # (samples, horizon*2)

    # 4. Split train/val
    split = int(len(X) * 0.8)
    X_train, X_val = X[:split], X[split:]
    Y_train, Y_val = Y_flat[:split], Y_flat[split:]

    print(f"\n📈 Train: {len(X_train)} samples")
    print(f"📉 Val:   {len(X_val)} samples")

    # 5. Build và train model
    print("\n🏗️ Building model...")
    model = build_rain_model(
        input_shape=(LOOKBACK, len(feature_cols)),
        output_shape=(HORIZON, 2)
    )

    print(model.summary())

    print("\n🚀 Training...")
    early_stop = EarlyStopping(
        monitor='val_loss',
        patience=10,
        restore_best_weights=True
    )

    history = model.fit(
        X_train, Y_train,
        validation_data=(X_val, Y_val),
        epochs=100,
        batch_size=32,
        callbacks=[early_stop],
        verbose=1
    )

    # 6. Lưu model và scalers
    model_path = MODEL_DIR / f"{province}_rain.keras"
    scaler_X_path = MODEL_DIR / f"{province}_rain_scaler_X.pkl"
    scaler_Y_path = MODEL_DIR / f"{province}_rain_scaler_Y.pkl"

    model.save(model_path)
    joblib.dump(scaler_X, scaler_X_path)
    joblib.dump(scaler_Y, scaler_Y_path)

    print(f"\n✅ Đã lưu model: {model_path}")
    print(f"✅ Đã lưu scaler X: {scaler_X_path}")
    print(f"✅ Đã lưu scaler Y: {scaler_Y_path}")

    # 7. Evaluate
    val_loss, val_mae = model.evaluate(X_val, Y_val, verbose=0)
    print(f"\n📊 Validation Loss: {val_loss:.4f}")
    print(f"📊 Validation MAE:  {val_mae:.4f}")

    return history


if __name__ == "__main__":
    # Danh sách tỉnh cần train
    provinces = [
        "An_Giang",
        "Ha_Noi",
        "TP_HCM",
        "Da_Nang",
        # Thêm tỉnh khác...
    ]

    for province in provinces:
        try:
            train_province_rain(province)
        except Exception as e:
            print(f"\n❌ Lỗi khi train {province}: {e}")
            continue

    print("\n" + "=" * 70)
    print("✅ HOÀN THÀNH TẤT CẢ!")
    print("=" * 70)