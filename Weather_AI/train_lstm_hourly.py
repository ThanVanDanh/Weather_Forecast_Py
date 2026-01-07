# train_lstm_hourly.py
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Input
from tensorflow.keras.callbacks import EarlyStopping

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SAVE_DIR = BASE_DIR / "models_lstm_hourly"
SAVE_DIR.mkdir(exist_ok=True)

TARGET = "temperature_2m"
LOOKBACK = 48
EPOCHS = 30
BATCH = 64


def load_series(csv: Path) -> np.ndarray:
    df = pd.read_csv(csv)
    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").sort_index()
    df = df.asfreq("h").ffill().bfill()
    return df[TARGET].astype(float).values.reshape(-1, 1)


def make_dataset(data, lookback):
    X, y = [], []
    for i in range(len(data) - lookback):
        X.append(data[i:i+lookback])
        y.append(data[i+lookback])
    return np.array(X), np.array(y)


def train_one(province: str, csv: Path):
    print(f"\n=== TRAIN LSTM HOURLY {province} ===")

    series = load_series(csv)

    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(series)

    X, y = make_dataset(scaled, LOOKBACK)
    X = X.reshape((X.shape[0], LOOKBACK, 1))

    split = int(len(X) * 0.8)
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]

    model = Sequential([
        Input(shape=(LOOKBACK, 1)),
        LSTM(64, return_sequences=True),
        LSTM(32),
        Dense(1)
    ])
    model.compile(optimizer="adam", loss="mse")

    es = EarlyStopping(patience=5, restore_best_weights=True)

    model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=EPOCHS,
        batch_size=BATCH,
        callbacks=[es],
        verbose=1
    )

    model.save(SAVE_DIR / f"{province}_hourly.keras")
    joblib.dump(scaler, SAVE_DIR / f"{province}_scaler.pkl")

    print(f"[{province}] Saved → {province}_hourly.keras")


def main():
    for csv in DATA_DIR.glob("*.csv"):
        train_one(csv.stem, csv)


if __name__ == "__main__":
    print("🚀 TRAIN LSTM HOURLY (24h forecast via recursion)")
    main()
