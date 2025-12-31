# train_lstm_daily_maxmin.py
from pathlib import Path
import numpy as np
import pandas as pd
import joblib

from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models_lstm_daily"
MODEL_DIR.mkdir(exist_ok=True)

TARGET = "temperature_2m"

LOOKBACK = 14   # dùng 14 ngày trước
HORIZON = 5     # dự báo 5 ngày
EPOCHS = 40
BATCH = 32


def load_daily_maxmin(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").sort_index()
    df = df.asfreq("h").ffill().bfill()

    daily = df.resample("D")[TARGET].agg(["max", "min"])
    daily.columns = ["temp_max", "temp_min"]
    return daily.astype(float)


def build_sequences(data, lookback, horizon):
    X, y = [], []
    for i in range(len(data) - lookback - horizon + 1):
        X.append(data[i:i+lookback])
        y.append(data[i+lookback:i+lookback+horizon])
    return np.array(X), np.array(y)


def train_province(csv_path: Path):
    province = csv_path.stem
    print(f"\n=== TRAIN LSTM DAILY MAX-MIN: {province} ===")

    daily = load_daily_maxmin(csv_path)

    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(daily.values)

    X, y = build_sequences(scaled, LOOKBACK, HORIZON)

    # y: (samples, horizon, 2) → flatten thành (samples, horizon*2)
    y = y.reshape((y.shape[0], HORIZON * 2))

    split = int(len(X) * 0.8)
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]

    print(f"[{province}] Samples: train={len(X_train)}, val={len(X_val)}")

    model = Sequential([
        LSTM(64, return_sequences=True, input_shape=(LOOKBACK, 2)),
        Dropout(0.2),
        LSTM(32),
        Dense(HORIZON * 2)
    ])

    model.compile(optimizer="adam", loss="mse")

    callbacks = [
        EarlyStopping(patience=6, restore_best_weights=True),
        ReduceLROnPlateau(patience=3, factor=0.5, verbose=1)
    ]

    model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=EPOCHS,
        batch_size=BATCH,
        callbacks=callbacks,
        verbose=1
    )

    model_path = MODEL_DIR / f"{province}_lstm_daily_maxmin.keras"
    scaler_path = MODEL_DIR / f"{province}_daily_scaler.pkl"

    model.save(model_path)
    joblib.dump(scaler, scaler_path)

    print(f"[{province}] Model saved → {model_path}")
    print(f"[{province}] Scaler saved → {scaler_path}")


def main():
    csv_files = sorted(DATA_DIR.glob("*.csv"))
    if not csv_files:
        print("❌ No CSV files found in data/")
        return

    for csv in csv_files:
        try:
            train_province(csv)
        except Exception as e:
            print(f"⚠️ ERROR {csv.stem}: {e}")

    print("\n🎉 TRAINING DAILY MAX-MIN LSTM COMPLETED")


if __name__ == "__main__":
    main()
