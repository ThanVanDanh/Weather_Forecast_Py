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
from tensorflow.keras.layers import LSTM, Dense, Dropout, Input
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
import pvlib
from pvlib.location import Location

# ============================
# CẤU HÌNH
# ============================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "model_solar_clearsky"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

MODEL_FILE = MODEL_DIR / "lstm_clearsky.keras"
SCALER_FILE = MODEL_DIR / "scaler_clearsky.pkl"

LAT, LON = 10.01000, 105.08000
TZ = 'Asia/Bangkok'

# SEQ_LENGTH ngắn lại vì 1 ngày chỉ còn 12 tiếng nắng
SEQ_LENGTH = 48
TARGET_COL = 'shortwave_radiation'


def get_clear_sky_index(df, lat, lon, tz):
    site = Location(lat, lon, tz=tz)
    times = pd.to_datetime(df.index)
    cs = site.get_clearsky(times)
    df['clear_sky'] = cs['ghi'].values

    # Tính k
    df['k_index'] = df[TARGET_COL] / df['clear_sky']
    df.loc[df['clear_sky'] < 10, 'k_index'] = 0
    df['k_index'] = df['k_index'].fillna(0).clip(lower=0, upper=1.2)  # Clip trần 1.2

    return df


def create_sequences(data, seq_length):
    X, y = [], []
    for i in range(len(data) - seq_length):
        X.append(data[i:(i + seq_length)])
        y.append(data[i + seq_length])
    return np.array(X), np.array(y)


def main():
    print("🔄 Training V3: Chế độ Daylight-Only...")

    # Load Data
    all_files = glob.glob(str(DATA_DIR / "*.csv"))
    angiang_files = [f for f in all_files if "an giang" in os.path.basename(f).lower().replace("_", " ")]

    if not angiang_files:
        print("❌ Không tìm thấy file data.")
        return

    df_list = []
    for f in angiang_files:
        df = pd.read_csv(f)
        df['time'] = pd.to_datetime(df['time'])
        df = df.set_index('time').sort_index()
        # Resample 'h'
        df = df.resample('h').mean().interpolate()
        df_list.append(df)

    full_df = pd.concat(df_list)
    full_df = get_clear_sky_index(full_df, LAT, LON, TZ)

    # === QUAN TRỌNG: CHỈ LẤY GIỜ CÓ NẮNG ===
    # Lấy các giờ từ 6h sáng đến 17h chiều
    daytime_df = full_df.between_time('06:00', '17:00').copy()
    print(f"☀️ Dữ liệu train (chỉ ban ngày): {len(daytime_df)} dòng")

    data_k = daytime_df[['k_index']].values

    # Scale
    scaler = MinMaxScaler(feature_range=(0, 1))
    data_scaled = scaler.fit_transform(data_k)
    joblib.dump(scaler, SCALER_FILE)

    # Sequence
    X, y = create_sequences(data_scaled, SEQ_LENGTH)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.1, shuffle=False)

    # Model
    model = Sequential([
        Input(shape=(SEQ_LENGTH, 1)),
        LSTM(64, return_sequences=True),
        Dropout(0.2),
        LSTM(32, return_sequences=False),
        Dropout(0.2),
        Dense(1, activation='linear')  # Linear để không bị giới hạn trần
    ])

    model.compile(optimizer='adam', loss='mae')  # Dùng MAE để bớt nhạy cảm với nhiễu

    early_stop = EarlyStopping(monitor='val_loss', patience=15, restore_best_weights=True)
    checkpoint = ModelCheckpoint(str(MODEL_FILE), save_best_only=True)

    history = model.fit(
        X_train, y_train,
        validation_data=(X_test, y_test),
        epochs=20,
        batch_size=16,  # Batch nhỏ để học kỹ hơn
        callbacks=[early_stop, checkpoint],
        verbose=1
    )
    print("🏁 Done Training.")


if __name__ == "__main__":
    main()