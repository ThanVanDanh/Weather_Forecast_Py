import os
import glob
import time
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Input
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from concurrent.futures import ProcessPoolExecutor

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models_humidity"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

TARGET_COLUMN = "relative_humidity_2m"
SEQ_LENGTH = 72
PREDICT_HORIZON = 24

BATCH_SIZE = 32
EPOCHS = 50
MAX_WORKERS = 4

def process_humidity_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    time_col = df.columns[0]
    df[time_col] = pd.to_datetime(df[time_col])
    df = df.sort_values(by=time_col).reset_index(drop=True)

    df["hour"] = df[time_col].dt.hour
    df["month"] = df[time_col].dt.month
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)

    return df[[TARGET_COLUMN, "hour_sin", "hour_cos", "month_sin", "month_cos"]]

def create_dataset(X, y, seq_len, horizon):
    Xs, ys = [], []
    for i in range(len(X) - seq_len - horizon + 1):
        Xs.append(X[i:i+seq_len])
        ys.append(y[i+seq_len:i+seq_len+horizon, 0])  # (horizon,)
    return np.asarray(Xs, dtype=np.float32), np.asarray(ys, dtype=np.float32)

def train_one_province(file_path):
    province_name = os.path.splitext(os.path.basename(file_path))[0]
    model_file = MODEL_DIR / f"{province_name}.keras"

    if model_file.exists():
        return f" {province_name}: Đã xong từ trước."

    scaler_y_file = MODEL_DIR / f"scaler_Y_{province_name}.pkl"
    scaler_time_file = MODEL_DIR / f"scaler_TIME_{province_name}.pkl"

    try:
        raw_df = pd.read_csv(file_path)
        if TARGET_COLUMN not in raw_df.columns:
            return f" {province_name}: Thiếu cột {TARGET_COLUMN}."

        df = process_humidity_features(raw_df).ffill().bfill()
        values = df.values.astype("float32")

        y_raw = values[:, [0]]          # (N,1)
        time_raw = values[:, 1:]        # (N,4)

        n = len(values)
        if n < SEQ_LENGTH + PREDICT_HORIZON + 10:
            return f" {province_name}: Không đủ data."


        n_train = int(n * 0.8)
        n_val = int(n * 0.9)

        y_train_raw, y_val_raw, y_test_raw = y_raw[:n_train], y_raw[n_train:n_val], y_raw[n_val:]
        t_train_raw, t_val_raw, t_test_raw = time_raw[:n_train], time_raw[n_train:n_val], time_raw[n_val:]


        scaler_y = MinMaxScaler()
        scaler_t = MinMaxScaler()

        y_train = scaler_y.fit_transform(y_train_raw)
        y_val = scaler_y.transform(y_val_raw)
        y_test = scaler_y.transform(y_test_raw)

        t_train = scaler_t.fit_transform(t_train_raw)
        t_val = scaler_t.transform(t_val_raw)
        t_test = scaler_t.transform(t_test_raw)

        joblib.dump(scaler_y, scaler_y_file)
        joblib.dump(scaler_t, scaler_time_file)


        X_train_all = np.concatenate([y_train, t_train], axis=1)
        X_val_all   = np.concatenate([y_val,   t_val], axis=1)
        X_test_all  = np.concatenate([y_test,  t_test], axis=1)

        X_train, Y_train = create_dataset(X_train_all, y_train, SEQ_LENGTH, PREDICT_HORIZON)
        X_val,   Y_val   = create_dataset(X_val_all,   y_val,   SEQ_LENGTH, PREDICT_HORIZON)
        X_test,  Y_test  = create_dataset(X_test_all,  y_test,  SEQ_LENGTH, PREDICT_HORIZON)

        if len(X_train) == 0 or len(X_val) == 0:
            return f" {province_name}: Không đủ data sau khi tạo sequence."

        model = Sequential([
            Input(shape=(X_train.shape[1], X_train.shape[2])),
            LSTM(128, return_sequences=False),
            Dropout(0.2),
            Dense(PREDICT_HORIZON)
        ])
        model.compile(optimizer="adam", loss="mse")

        early_stop = EarlyStopping(monitor="val_loss", patience=10, restore_best_weights=True)
        checkpoint = ModelCheckpoint(model_file, monitor="val_loss", save_best_only=True, verbose=0)

        model.fit(
            X_train, Y_train,
            epochs=EPOCHS,
            batch_size=BATCH_SIZE,
            validation_data=(X_val, Y_val),
            callbacks=[early_stop, checkpoint],
            verbose=1
        )


        test_loss = model.evaluate(X_test, Y_test, verbose=0)
        return f"{province_name}: Hoàn tất! (test_loss={test_loss:.5f})"

    except Exception as e:
        return f"{province_name}: Lỗi {str(e)}"

def main():
    import tensorflow as tf
    tf.config.set_visible_devices([], "GPU")
    tf.config.threading.set_intra_op_parallelism_threads(1)
    tf.config.threading.set_inter_op_parallelism_threads(1)

    all_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
    print(f" Bắt đầu train humidity với {MAX_WORKERS} process...")
    print(f" Features: humidity lịch sử + time features (sin/cos hour, month)")
    start = time.time()

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for res in executor.map(train_one_province, all_files):
            print(res)

    print(f"\nTỔNG THỜI GIAN: {(time.time() - start)/60:.1f} phút.")
    print(f"  Models lưu tại: {MODEL_DIR}")

if __name__ == "__main__":
    main()
