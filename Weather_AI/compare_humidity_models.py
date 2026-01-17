#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
compare_humidity_models.py
=========================
So sánh dự báo độ ẩm 24h tới giữa SARIMA và LSTM cho 1 tỉnh.

Yêu cầu thư mục (đúng theo scripts train/predict bạn đã có):
- data/{province}.csv
- data_test/{province}.csv   (ground truth 24h sau mốc cuối của data)
- artifacts_humidity/{province}/{province}_humidity_sarima.pkl
- models_humidity/{province}.keras
- models_humidity/scaler_X_{province}.pkl
- models_humidity/scaler_Y_{province}.pkl

Chạy:
    python compare_humidity_models.py
"""
from sklearn.metrics import mean_absolute_error, mean_squared_error

import numpy as np
import pandas as pd
import joblib
import matplotlib.pyplot as plt
from pathlib import Path
import pickle

from statsmodels.tsa.statespace.sarimax import SARIMAX

try:
    from tensorflow.keras.models import load_model
except Exception as e:
    load_model = None
    _TF_IMPORT_ERROR = e


# ============================
# CẤU HÌNH CHUNG
# ============================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"  # Dữ liệu cũ (để model học)
DATA_TEST_DIR = BASE_DIR / "data_test"  # Dữ liệu mới (để chấm điểm model)

# ĐÚNG với train_humidity_sarima.py (ARTIFACTS_DIR = BASE_DIR / "artifacts_humidity")
ARTIFACTS_SARIMA_DIR = BASE_DIR / "artifacts_humidity"

# ĐÚNG với train_humidity_lstm.py (MODEL_DIR = BASE_DIR / "models_humidity")
MODEL_LSTM_DIR = BASE_DIR / "models_humidity"

TARGET_COLUMN = "relative_humidity_2m"
PREDICT_HORIZON = 24  # So sánh 24 giờ tới

# Cấu hình context (SARIMA dùng tail lịch sử để re-fit nhanh)
SARIMA_CONTEXT = 500
LSTM_SEQ_LEN = 72


# ============================
# 1. SARIMA (đúng theo artifacts)
# ============================
def get_sarima_forecast(province_name: str, raw_df: pd.DataFrame):
    province_dir = ARTIFACTS_SARIMA_DIR / province_name
    model_path = province_dir / f"{province_name}_humidity_sarima.pkl"

    if not model_path.exists():
        print(f"⚠️ Không tìm thấy SARIMA artifacts: {model_path}")
        return None, None

    # model_data là dict lưu order, seasonal_order, params... (theo train_humidity_sarima.py)
    with open(model_path, "rb") as f:
        model_data = pickle.load(f)

    # Chuẩn hoá dữ liệu theo giờ
    df = raw_df.copy()
    time_col = df.columns[0]
    df[time_col] = pd.to_datetime(df[time_col])
    df = df.sort_values(time_col).set_index(time_col)

    df = df.asfreq("H")
    df[TARGET_COLUMN] = df[TARGET_COLUMN].interpolate(method="time").ffill().bfill()

    # Lấy recent data để model ổn định (ít nhất 30 ngày hoặc SARIMA_CONTEXT)
    recent_len = max(SARIMA_CONTEXT, 24 * 30)
    recent_data = df[TARGET_COLUMN].tail(recent_len)
    if len(recent_data) < 48:
        print("⚠️ Dữ liệu quá ít để forecast SARIMA ổn định.")
        return None, None

    order = tuple(model_data["order"])
    seasonal_order = tuple(model_data["seasonal_order"])

    model = SARIMAX(
        recent_data,
        order=order,
        seasonal_order=seasonal_order,
        enforce_stationarity=False,
        enforce_invertibility=False,
        initialization="approximate_diffuse",
    )

    start_params = model_data.get("params", None)
    try:
        if start_params is not None:
            fit = model.fit(disp=False, start_params=start_params, maxiter=100)
        else:
            fit = model.fit(disp=False, maxiter=200)
    except Exception as e:
        print(f"❌ SARIMA fit lỗi: {e}")
        return None, None

    forecast = fit.get_forecast(steps=PREDICT_HORIZON).predicted_mean.clip(0, 100)

    last_timestamp = recent_data.index.max()
    future_dates = pd.date_range(
        start=last_timestamp + pd.Timedelta(hours=1),
        periods=PREDICT_HORIZON,
        freq="H",
    )

    return future_dates, forecast.values


# ============================
# 2. LSTM
# ============================
def get_lstm_forecast(province_name: str, raw_df: pd.DataFrame):
    if load_model is None:
        print(f"❌ Không import được TensorFlow/Keras: {_TF_IMPORT_ERROR}")
        return None

    model_file = MODEL_LSTM_DIR / f"{province_name}.keras"
    scaler_x_file = MODEL_LSTM_DIR / f"scaler_X_{province_name}.pkl"
    scaler_y_file = MODEL_LSTM_DIR / f"scaler_Y_{province_name}.pkl"

    for p in [model_file, scaler_x_file, scaler_y_file]:
        if not p.exists():
            print(f"⚠️ Thiếu file LSTM: {p}")
            return None

    # Load Model & Scalers
    model = load_model(model_file)
    scaler_X = joblib.load(scaler_x_file)
    scaler_Y = joblib.load(scaler_y_file)

    # Xử lý dữ liệu (PHẢI giống train_humidity_lstm.py)
    df = raw_df.copy()
    time_col = df.columns[0]
    df[time_col] = pd.to_datetime(df[time_col])
    df = df.sort_values(by=time_col).reset_index(drop=True)

    df["hour"] = df[time_col].dt.hour
    df["month"] = df[time_col].dt.month
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)

    features = [TARGET_COLUMN, "hour_sin", "hour_cos", "month_sin", "month_cos"]
    df = df[features].ffill().bfill()

    data_values = df.values.astype("float32")
    if len(data_values) < LSTM_SEQ_LEN:
        print(f"⚠️ Không đủ dữ liệu cho LSTM: cần {LSTM_SEQ_LEN} dòng, hiện có {len(data_values)}")
        return None

    last_sequence = data_values[-LSTM_SEQ_LEN:]
    last_sequence_scaled = scaler_X.transform(last_sequence)
    X_pred = last_sequence_scaled.reshape(1, LSTM_SEQ_LEN, -1)

    y_pred_scaled = model.predict(X_pred, verbose=0)
    y_pred = scaler_Y.inverse_transform(y_pred_scaled)  # Shape (1, 24)

    return y_pred[0]


# ============================
# 3. GROUND TRUTH (data_test)
# ============================
def get_ground_truth(province_name: str, start_forecast_time: pd.Timestamp):
    test_file = DATA_TEST_DIR / f"{province_name}.csv"
    if not test_file.exists():
        print(f"⚠️ Không tìm thấy file kiểm chứng: {test_file}")
        return None, None

    df = pd.read_csv(test_file)
    time_col = df.columns[0]
    df[time_col] = pd.to_datetime(df[time_col])

    # Đảm bảo khớp theo giờ (tránh lệch phút/giây)
    df[time_col] = df[time_col].dt.floor("H")
    start_forecast_time = pd.to_datetime(start_forecast_time).floor("H")

    end_forecast_time = start_forecast_time + pd.Timedelta(hours=PREDICT_HORIZON - 1)

    mask = (df[time_col] >= start_forecast_time) & (df[time_col] <= end_forecast_time)
    filtered_df = df.loc[mask].sort_values(time_col)

    if filtered_df.empty:
        print("⚠️ data_test có nhưng không khớp thời gian dự báo.")
        return None, None

    return filtered_df[time_col], filtered_df[TARGET_COLUMN]


# ============================
# 4. MAIN
# ============================
def align_by_time(true_dates, true_values, pred_dates, pred_values):
    """
    Căn theo timestamp để so sánh đúng từng giờ.
    Hỗ trợ true_dates/pred_dates là Series, list, DatetimeIndex...
    """
    if true_dates is None or pred_dates is None:
        return None, None

    # true ts
    true_ts = pd.to_datetime(true_dates)
    if isinstance(true_ts, pd.DatetimeIndex):
        true_ts = true_ts.floor("h")
    else:
        true_ts = true_ts.dt.floor("h")

    # pred ts
    pred_ts = pd.to_datetime(pred_dates)
    if isinstance(pred_ts, pd.DatetimeIndex):
        pred_ts = pred_ts.floor("h")
    else:
        pred_ts = pred_ts.dt.floor("h")

    df_true = pd.DataFrame({
        "ts": true_ts,
        "y_true": np.asarray(true_values, dtype=float)
    })
    df_pred = pd.DataFrame({
        "ts": pred_ts,
        "y_pred": np.asarray(pred_values, dtype=float)
    })

    merged = df_true.merge(df_pred, on="ts", how="inner").sort_values("ts")
    if merged.empty:
        return None, None
    return merged["y_true"].values, merged["y_pred"].values



def evaluate_model(y_true, y_pred, name):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    print(f"📊 {name}: MAE={mae:.3f} | RMSE={rmse:.3f} | N={len(y_true)}")
    return mae, rmse

def main():
    province = "Ha_Noi"  # Đổi tên tỉnh tại đây

    print(f"🔥 BẮT ĐẦU SO SÁNH MODEL ĐỘ ẨM: {province}")
    print(f"📂 Dữ liệu học: {DATA_DIR / (province + '.csv')}")
    print(f"📂 Dữ liệu test: {DATA_TEST_DIR / (province + '.csv')}")
    print("-" * 60)

    data_file = DATA_DIR / f"{province}.csv"
    if not data_file.exists():
        print(f"❌ Không tìm thấy file dữ liệu gốc: {data_file}")
        return

    raw_df = pd.read_csv(data_file)
    time_col = raw_df.columns[0]
    raw_df[time_col] = pd.to_datetime(raw_df[time_col])

    # Lấy 48 giờ cuối của lịch sử để vẽ
    history_df = raw_df.iloc[-48:].copy()
    last_hist_date = pd.to_datetime(history_df[time_col].iloc[-1]).floor("H")
    last_hist_val = float(history_df[TARGET_COLUMN].iloc[-1])

    start_forecast_time = last_hist_date + pd.Timedelta(hours=1)
    print(f"⏰ Thời điểm dự báo bắt đầu từ: {start_forecast_time}")

    # Chạy model
    print("🔹 Đang chạy SARIMA...")
    sarima_dates, sarima_values = get_sarima_forecast(province, raw_df)

    print("🔹 Đang chạy LSTM...")
    lstm_values = get_lstm_forecast(province, raw_df)

    # Ground truth
    print("🔹 Đang lấy Ground Truth...")
    true_dates, true_values = get_ground_truth(province, start_forecast_time)

    # Dates cho LSTM (độc lập SARIMA)
    lstm_dates = pd.date_range(start=start_forecast_time, periods=PREDICT_HORIZON, freq="H")

    # Vẽ
    print("\n📈 Đang vẽ biểu đồ so sánh...")
    plt.figure(figsize=(14, 7))

    plt.plot(
        history_df[time_col],
        history_df[TARGET_COLUMN],
        label="Lịch sử (Training Data)",
        color="black",
        linewidth=2,
    )

    if true_dates is not None and len(true_dates) > 0:
        plot_true_dates = [last_hist_date] + list(true_dates)
        plot_true_vals = [last_hist_val] + list(true_values)
        plt.plot(plot_true_dates, plot_true_vals, label="THỰC TẾ (Đáp án)", color="green", linewidth=3, alpha=0.7)

    if sarima_dates is not None and sarima_values is not None:
        plot_dates = [last_hist_date] + list(sarima_dates)
        plot_vals = [last_hist_val] + list(sarima_values)
        plt.plot(plot_dates, plot_vals, label="SARIMA Forecast", color="blue", linestyle="--", marker="o")

    if lstm_values is not None:
        plot_dates = [last_hist_date] + list(lstm_dates)
        plot_vals = [last_hist_val] + list(lstm_values)
        plt.plot(plot_dates, plot_vals, label="LSTM Forecast", color="red", linestyle="-.", marker="x")

    plt.title(f"CUỘC CHIẾN MODEL: SARIMA vs LSTM ({province})", fontsize=16, fontweight="bold")
    plt.xlabel("Thời gian")
    plt.ylabel("Độ ẩm (%)")
    plt.legend(loc="upper left", frameon=True, shadow=True)
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    # ============================
    # 5. ĐÁNH GIÁ ĐỘ CHÍNH XÁC
    # ============================
    print("\n📏 ĐÁNH GIÁ (so với Ground Truth):")

    if true_dates is None or true_values is None:
        print("⚠️ Không có Ground Truth -> không tính được metrics.")
    else:
        # SARIMA metrics
        if sarima_dates is not None and sarima_values is not None:
            y_true_s, y_pred_s = align_by_time(true_dates, true_values, sarima_dates, sarima_values)
            if y_true_s is None:
                print("⚠️ SARIMA: không align được theo timestamp.")
            else:
                evaluate_model(y_true_s, y_pred_s, "SARIMA")

        # LSTM metrics
        if lstm_values is not None:
            y_true_l, y_pred_l = align_by_time(true_dates, true_values, lstm_dates, lstm_values)
            if y_true_l is None:
                print("⚠️ LSTM: không align được theo timestamp.")
            else:
                evaluate_model(y_true_l, y_pred_l, "LSTM")
    plt.show()



if __name__ == "__main__":
    main()
