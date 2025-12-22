"""
LSTM v3 – Univariate multi-step temperature forecasting
Input: past 168 hours
Output: next 120 hours
"""

import os
from pathlib import Path
import numpy as np
import pandas as pd
import joblib

from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Input
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from tensorflow.keras.optimizers import Adam


# =====================
# CONFIG
# =====================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SAVE_DIR = BASE_DIR / "models_lstm_v3"
SAVE_DIR.mkdir(exist_ok=True)

TARGET = "temperature_2m"

LOOKBACK = 168   # 7 ngày quá khứ
HORIZON = 120    # dự báo 120 giờ

EPOCHS = 40
BATCH_SIZE = 64
LR = 1e-3


# =====================
# UTILS
# =====================

def load_series(csv_path):
    df = pd.read_csv(csv_path)
    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").sort_index()
    df = df.asfreq("h").ffill().bfill()
    return df[TARGET].values.reshape(-1, 1)


def make_dataset(series, lookback, horizon):
    X, y = [], []
    for i in range(len(series) - lookback - horizon + 1):
        X.append(series[i:i+lookback])
        y.append(series[i+lookback:i+lookback+horizon, 0])
    return np.array(X), np.array(y)


def build_model(lookback, horizon):
    model = Sequential([
        Input(shape=(lookback, 1)),
        LSTM(128, return_sequences=True),
        Dropout(0.2),
        LSTM(64),
        Dropout(0.2),
        Dense(horizon)
    ])
    model.compile(
        optimizer=Adam(learning_rate=LR),
        loss="mse"
    )
    return model


# =====================
# TRAIN ONE PROVINCE
# =====================

def train_province(province, csv_path):
    print(f"\n=== TRAIN LSTM v3 {province} ===")

    series = load_series(csv_path)

    scaler = MinMaxScaler()
    series_scaled = scaler.fit_transform(series)

    X, y = make_dataset(series_scaled, LOOKBACK, HORIZON)

    split = int(len(X) * 0.8)
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]

    print(f"[{province}] Samples: train={len(X_train)}, val={len(X_val)}")

    model = build_model(LOOKBACK, HORIZON)

    callbacks = [
        EarlyStopping(patience=6, restore_best_weights=True),
        ReduceLROnPlateau(patience=3, factor=0.5)
    ]

    model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        callbacks=callbacks,
        verbose=1
    )

    model_path = SAVE_DIR / f"{province}_lstm_v3.keras"
    scaler_path = SAVE_DIR / f"{province}_scaler_v3.pkl"

    model.save(model_path)
    joblib.dump(scaler, scaler_path)

    print(f"[{province}] Model saved → {model_path}")
    print(f"[{province}] Scaler saved → {scaler_path}")


# =====================
# MAIN
# =====================

if __name__ == "__main__":
    print("🚀 TRAIN LSTM v3 – TEMPERATURE (UNIVARIATE, MULTI-STEP)")
    print(f"📁 DATA: {DATA_DIR}")
    print(f"📁 SAVE: {SAVE_DIR}")

    for csv in sorted(DATA_DIR.glob("*.csv")):
        province = csv.stem
        try:
            train_province(province, csv)
        except Exception as e:
            print(f"⚠️ ERROR {province}: {e}")

    print("\n🎉 DONE LSTM v3 TRAINING")
