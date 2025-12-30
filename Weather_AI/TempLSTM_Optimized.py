# -*- coding: utf-8 -*-
"""
Vietnam Temperature Forecasting - Optimized for Low RAM
Train model dự báo nhiệt độ với 34 tỉnh thành Việt Nam
"""

import tensorflow as tf
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os
from glob import glob
import json
import gc
import os

# Đường dẫn thư mục chứa file train_lstm.py
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Đi lên 1 cấp (PROJECT_ROOT)
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

# Thư mục train_AI/dataLSTM
SAVE_DIR = os.path.join(PROJECT_ROOT, "train_AI", "dataLSTM")

os.makedirs(SAVE_DIR, exist_ok=True)

print("📁 Save directory:", SAVE_DIR)

# Config
tf.random.set_seed(42)
np.random.seed(42)

# Cấu hình TensorFlow để tiết kiệm RAM
gpus = tf.config.list_physical_devices('GPU')
if gpus:
    try:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
    except RuntimeError as e:
        print(e)

tf.config.set_soft_device_placement(True)

plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.family'] = 'DejaVu Sans'

print("=" * 100)
print("🌡️  VIETNAM TEMPERATURE FORECASTING - 34 PROVINCES (RAM OPTIMIZED)")
print("=" * 100)
print(f"TensorFlow version: {tf.__version__}\n")

# ==============================================================================
# CẤU HÌNH QUAN TRỌNG - ĐIỀU CHỈNH ĐỂ GIẢM RAM
# ==============================================================================

# Lấy mẫu dữ liệu để giảm RAM
# 1 = 100% data, 2 = 50%, 3 = 33%, 4 = 25%
SAMPLE_RATE = 2  # ← ĐIỀU CHỈNH Ở ĐÂY

# Hyperparameters
PAST_HISTORY = 168  # 7 ngày
FUTURE_TARGET = 24  # Dự đoán 1 ngày
BATCH_SIZE = 128
EPOCHS = 50

print(f"⚙️  SAMPLE_RATE: {SAMPLE_RATE}x (Dùng {100 / SAMPLE_RATE:.0f}% data)")
print(f"⚙️  BATCH_SIZE: {BATCH_SIZE}")
print(f"⚙️  EPOCHS: {EPOCHS}\n")

print("🔥 SAMPLE_RATE ĐANG CHẠY =", SAMPLE_RATE)

# ==============================================================================
# BƯỚC 1: LOAD DỮ LIỆU
# ==============================================================================

def load_all_provinces(data_folder):
    """Load tất cả CSV files với sampling"""

    # Thử nhiều đường dẫn
    possible_paths = [
        data_folder,
        './data',
        '../data',
        '../train_AI/data',
        './train_AI/data',
    ]

    csv_files = []
    actual_path = None

    for path in possible_paths:
        if os.path.exists(path):
            files = glob(os.path.join(path, '*.csv'))
            if files:
                csv_files = files
                actual_path = path
                break

    if len(csv_files) == 0:
        print(f"⚠️  Không tìm thấy file CSV nào!")
        print(f"\n🔍 Các path đã thử:")
        for p in possible_paths:
            exists = "✓" if os.path.exists(p) else "✗"
            print(f"   {exists} {os.path.abspath(p)}")
        return None, None

    print(f"✓ Tìm thấy folder: {actual_path}")
    print(f"📁 Loading {len(csv_files)} files...\n")

    all_data = []
    province_names = []

    for file in csv_files:
        province_name = os.path.basename(file).replace('.csv', '').replace('_3years_hourly', '')
        province_names.append(province_name)

        # Đọc và lấy mẫu
        df = pd.read_csv(file, low_memory=True)

        if SAMPLE_RATE > 1:
            df = df.iloc[::SAMPLE_RATE].reset_index(drop=True)

        df['province'] = province_name
        all_data.append(df)

        print(f"   ✓ {province_name}: {len(df):,} records")

        del df

    combined_df = pd.concat(all_data, ignore_index=True)
    del all_data
    gc.collect()

    print(f"\n✅ Tổng: {len(combined_df):,} records từ {len(province_names)} tỉnh")

    return combined_df, province_names


# Load data
df_all, provinces = load_all_provinces('../train_AI/data')

if df_all is None:
    print("\n❌ Không tìm thấy data! Thoát...")
    exit()

print(f"\n📋 Các cột: {df_all.columns.tolist()}\n")

# ==============================================================================
# BƯỚC 2: CẤU HÌNH FEATURES
# ==============================================================================

TARGET_COLUMN = 'temperature_2m'

FEATURES = [
    'temperature_2m',
    'relative_humidity_2m',
    'dewpoint_2m',
    'surface_pressure',
    'pressure_msl',
    'cloudcover',
    'wind_speed_10m',
    'shortwave_radiation',
]

print(f"🎯 Target: {TARGET_COLUMN}")
print(f"📊 Features: {FEATURES}\n")

# Kiểm tra features
available_features = [f for f in FEATURES if f in df_all.columns]
missing = [f for f in FEATURES if f not in df_all.columns]

if missing:
    print(f"⚠️  Thiếu: {missing}")
    print(f"✓ Dùng: {available_features}")

if TARGET_COLUMN not in df_all.columns:
    print(f"❌ Không có target column: {TARGET_COLUMN}")
    exit()

# ==============================================================================
# BƯỚC 3: XỬ LÝ DỮ LIỆU
# ==============================================================================

print("\n🔧 Xử lý dữ liệu...")

features_df = df_all[available_features].copy()
target_series = df_all[TARGET_COLUMN].copy()

# Xử lý missing
features_df = features_df.interpolate(method='linear').fillna(method='ffill').fillna(method='bfill')
target_series = target_series.interpolate(method='linear').fillna(method='ffill').fillna(method='bfill')

# Convert sang float32 để giảm RAM
features_array = features_df.values.astype(np.float32)
target_array = target_series.values.astype(np.float32)

# Giải phóng RAM
del features_df, target_series, df_all
gc.collect()

print(f"✓ Features shape: {features_array.shape}")
print(f"✓ Target shape: {target_array.shape}")

# Split train/val
train_size = int(len(features_array) * 0.8)
print(f"✓ Train: {train_size:,} | Val: {len(features_array) - train_size:,}")

# Normalize
train_mean = features_array[:train_size].mean(axis=0)
train_std = features_array[:train_size].std(axis=0)
train_std[train_std == 0] = 1

features_normalized = (features_array - train_mean) / train_std

target_mean = target_array[:train_size].mean()
target_std = target_array[:train_size].std()
if target_std == 0:
    target_std = 1
target_normalized = (target_array - target_mean) / target_std

print(f"✓ Normalized")

# Giải phóng
del features_array, target_array
gc.collect()

# ==============================================================================
# BƯỚC 4: TẠO SEQUENCES
# ==============================================================================

print("\n🔨 Tạo sequences...")


def create_sequences(data, target, past_history, future_target):
    X, y = [], []
    for i in range(past_history, len(data) - future_target):
        X.append(data[i - past_history:i])
        y.append(target[i + future_target])
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


X, y = create_sequences(features_normalized, target_normalized, PAST_HISTORY, FUTURE_TARGET)

print(f"✓ X shape: {X.shape}")
print(f"✓ y shape: {y.shape}")
seq_train_size = int(len(X) * 0.8)

X_train, y_train = X[:seq_train_size], y[:seq_train_size]
X_val, y_val = X[seq_train_size:], y[seq_train_size:]
del X, y, features_normalized, target_normalized
gc.collect()

print(f"✓ Train: {X_train.shape}, Val: {X_val.shape}")

# ==============================================================================
# BƯỚC 5: XÂY DỰNG MODEL
# ==============================================================================

print("\n🏗️  Building model...")

model = tf.keras.Sequential([
    tf.keras.layers.LSTM(64, return_sequences=True, input_shape=X_train.shape[-2:]),
    tf.keras.layers.Dropout(0.3),
    tf.keras.layers.LSTM(32),
    tf.keras.layers.Dropout(0.3),
    tf.keras.layers.Dense(32, activation='relu'),
    tf.keras.layers.Dense(1)
])

model.compile(
    optimizer=tf.keras.optimizers.Adam(0.001),
    loss='mse',
    metrics=['mae']
)

model.summary()

# ==============================================================================
# BƯỚC 6: TRAINING
# ==============================================================================

print("\n🚀 Training...")

callbacks = [
    tf.keras.callbacks.EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True),
    tf.keras.callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=5, min_lr=1e-6)
]

history = model.fit(

    X_train, y_train,
    validation_data=(X_val, y_val),
    epochs=EPOCHS,
    batch_size=BATCH_SIZE,
    callbacks=callbacks,
    verbose=1
)
val_loss, val_mae = model.evaluate(X_val, y_val, verbose=0)
val_mae_actual = val_mae * target_std
# ==============================================================================
# BƯỚC 7: ĐÁNH GIÁ
# ==============================================================================

print("\n🧪 Creating prediction dataset...")

pred_records = []

num_samples = min(100, len(X_val))  # tránh out of range
temp_idx = available_features.index(TARGET_COLUMN)

for i in range(num_samples):
    x_input = X_val[i:i+1]

    y_true = y_val[i] * target_std + target_mean
    y_pred = model.predict(x_input, verbose=0)[0][0] * target_std + target_mean

    last_temp = (
        X_val[i, -1, temp_idx] * train_std[temp_idx] + train_mean[temp_idx]
    )

    pred_records.append({
        "last_known_temp": float(last_temp),
        "true_temp_future": float(y_true),
        "predicted_temp_future": float(y_pred),
        "error": float(abs(y_true - y_pred))
    })

df_pred = pd.DataFrame(pred_records)

print(f"✓ Prediction rows created: {len(df_pred)}")


# ==============================================================================
# BƯỚC 8: SAVE
# ==============================================================================

print("\n💾 Saving model & data...")

# 1. Save model
model_path = os.path.join(SAVE_DIR, "temperature_model.h5")
model.save(model_path)

# 2. Save scaler
scaler = {
    "features": available_features,
    "train_mean": train_mean.tolist(),
    "train_std": train_std.tolist(),
    "target_mean": float(target_mean),
    "target_std": float(target_std),
    "past_history": PAST_HISTORY,
    "future_target": FUTURE_TARGET,
    "sample_rate": SAMPLE_RATE
}

scaler_path = os.path.join(SAVE_DIR, "temperature_scaler.json")
with open(scaler_path, "w", encoding="utf-8") as f:
    json.dump(scaler, f, indent=2)

# 3. Save prediction dataset
csv_path = os.path.join(SAVE_DIR, "temperature_predictions.csv")
json_path = os.path.join(SAVE_DIR, "temperature_predictions.json")

df_pred.to_csv(csv_path, index=False)
df_pred.to_json(json_path, orient="records", indent=2)

print("✓ Saved model, scaler & predictions")


# ==============================================================================
# BƯỚC 9: VISUALIZATION
# ==============================================================================

print("\n📈 Creating plots...")

# Training history
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))

ax1.plot(history.history['loss'], label='Train Loss', linewidth=2)
ax1.plot(history.history['val_loss'], label='Val Loss', linewidth=2)
ax1.set_title('Loss', fontweight='bold')
ax1.legend()
ax1.grid(alpha=0.3)

ax2.plot(history.history['mae'], label='Train MAE', linewidth=2)
ax2.plot(history.history['val_mae'], label='Val MAE', linewidth=2)
ax2.set_title('MAE', fontweight='bold')
ax2.legend()
ax2.grid(alpha=0.3)

plt.tight_layout()
plt.savefig('training_history.png', dpi=300, bbox_inches='tight')
print("✓ Saved: training_history.png")

# Predictions
n = 3
indices = np.random.choice(len(X_val), n, replace=False)

fig, axes = plt.subplots(n, 1, figsize=(15, 4 * n))
if n == 1:
    axes = [axes]

for i, idx in enumerate(indices):
    y_true = y_val[idx] * target_std + target_mean
    y_pred = model.predict(X_val[idx:idx + 1], verbose=0)[0][0] * target_std + target_mean

    temp_idx = available_features.index(TARGET_COLUMN)
    history = X_val[idx, :, temp_idx] * train_std[temp_idx] + train_mean[temp_idx]

    axes[i].plot(range(-len(history), 0), history, 'b.-', label='History')
    axes[i].plot(FUTURE_TARGET, y_true, 'ro', markersize=10, label=f'True: {y_true:.1f}°C')
    axes[i].plot(FUTURE_TARGET, y_pred, 'g^', markersize=10, label=f'Pred: {y_pred:.1f}°C')
    axes[i].set_title(f'Error: {abs(y_true - y_pred):.2f}°C')
    axes[i].legend()
    axes[i].grid(alpha=0.3)

plt.tight_layout()
plt.savefig('predictions.png', dpi=300, bbox_inches='tight')
print("✓ Saved: predictions.png")

plt.show()
csv_path = os.path.join(SAVE_DIR, "temperature_predictions.csv")

print("\n" + "=" * 100)
print("✅ DONE!")
print("=" * 100)
print(f"""
📊 Summary:
   - Provinces: {len(provinces)}
   - Sample rate: {SAMPLE_RATE}x ({100 / SAMPLE_RATE:.0f}% data)
   - Training samples: {len(X_train):,}
   - Validation MAE: {val_mae_actual:.2f}°C

📁 Files:
   - temperature_model.h5
   - temperature_scaler.json
   - training_history.png
   - predictions.png
""")