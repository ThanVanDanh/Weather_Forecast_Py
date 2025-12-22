"""
TRAIN LSTM v2 – TEMPERATURE FORECAST (HOURLY)
===========================================

✔ Univariate: temperature_2m
✔ Window: 72 giờ quá khứ → dự báo 1 giờ tiếp theo
✔ Model: Bidirectional LSTM + BN + Dropout
✔ Callbacks: EarlyStopping + ReduceLR
✔ Save:
    - models_lstm/{province}_lstm_temp.h5
    - models_lstm/{province}_scaler.pkl
"""

from pathlib import Path
import numpy as np
import pandas as pd
import joblib

from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization, Bidirectional, Input
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from tensorflow.keras.losses import Huber


# =========================
# PATH CONFIG
# =========================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models_lstm"
MODEL_DIR.mkdir(exist_ok=True)

TARGET = "temperature_2m"

# =========================
# CONFIG
# =========================
WINDOW_SIZE = 72        # 3 ngày
BATCH_SIZE = 64
EPOCHS = 50
VAL_RATIO = 0.2


# =========================
# LOAD DATA
# =========================
def load_dataset(csv_path: Path) -> np.ndarray:
    df = pd.read_csv(csv_path)

    if TARGET not in df.columns:
        raise ValueError(f"{csv_path.name} missing {TARGET}")

    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").sort_index()
    df = df.asfreq("h")
    df = df.ffill().bfill()

    return df[TARGET].values.reshape(-1, 1)


# =========================
# CREATE SEQUENCES
# =========================
def create_sequences(data: np.ndarray, window: int):
    X, y = [], []
    for i in range(len(data) - window):
        X.append(data[i:i + window])
        y.append(data[i + window])
    return np.array(X), np.array(y)


# =========================
# BUILD MODEL
# =========================
def build_model(window: int):
    model = Sequential([
        Input(shape=(window, 1)),

        Bidirectional(LSTM(64, return_sequences=True)),
        BatchNormalization(),
        Dropout(0.2),

        Bidirectional(LSTM(32)),
        BatchNormalization(),
        Dropout(0.2),

        Dense(1)
    ])

    model.compile(
        optimizer="adam",
        loss=Huber()
    )
    return model


# =========================
# TRAIN ONE PROVINCE
# =========================
def train_province(province: str, csv_path: Path):
    print(f"\n=== TRAIN LSTM v2 {province} ===")

    data = load_dataset(csv_path)

    scaler = MinMaxScaler()
    data_scaled = scaler.fit_transform(data)

    X, y = create_sequences(data_scaled, WINDOW_SIZE)

    split = int(len(X) * (1 - VAL_RATIO))
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]

    print(f"[{province}] Samples: train={len(X_train)}, val={len(X_val)}")

    model = build_model(WINDOW_SIZE)

    early_stop = EarlyStopping(
        monitor="val_loss",
        patience=8,
        restore_best_weights=True
    )

    reduce_lr = ReduceLROnPlateau(
        monitor="val_loss",
        factor=0.5,
        patience=4,
        min_lr=1e-5,
        verbose=1
    )

    model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        callbacks=[early_stop, reduce_lr],
        verbose=1
    )

    model_path = MODEL_DIR / f"{province}_lstm_temp.h5"
    scaler_path = MODEL_DIR / f"{province}_scaler.pkl"

    model.save(model_path, include_optimizer=False)
    joblib.dump(scaler, scaler_path)

    print(f"[{province}] Model saved → {model_path}")
    print(f"[{province}] Scaler saved → {scaler_path}")


# =========================
# TRAIN ALL
# =========================
def train_all():
    csv_files = sorted(DATA_DIR.glob("*.csv"))
    if not csv_files:
        print("❌ No CSV files in data/")
        return

    for csv in csv_files:
        try:
            train_province(csv.stem, csv)
        except Exception as e:
            print(f"⚠️ ERROR {csv.stem}: {e}")

    print("\n🎉 LSTM v2 TRAINING COMPLETED")


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    print("🚀 TRAIN LSTM v2 – TEMPERATURE")
    print(f"📁 DATA: {DATA_DIR}")
    print(f"📁 SAVE: {MODEL_DIR}")

    train_all()
