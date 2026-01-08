#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
compare_humidity_models_34.py
============================

So sánh độ chính xác dự báo độ ẩm 24h tới giữa SARIMA và LSTM cho NHIỀU TỈNH (mặc định: tất cả file trong data/).

Yêu cầu thư mục (đúng theo scripts train/predict bạn đã có):
- data/{province}.csv
- data_test/{province}.csv   (ground truth 24h sau mốc cuối của data)
- artifacts_humidity/{province}/{province}_humidity_sarima.pkl
- models_humidity/{province}.keras
- models_humidity/scaler_X_{province}.pkl
- models_humidity/scaler_Y_{province}.pkl

Chạy:
    python compare_humidity_models_34.py
    python compare_humidity_models_34.py --provinces Ha_Noi Hai_Phong
    python compare_humidity_models_34.py --horizon 24 --seq-len 72 --sarima-context 500

Output:
- compare_34_provinces.csv (hoặc tên bạn đặt --out)
- In ra tổng hợp thắng/thua + MAE/RMSE trung bình
"""

import argparse
import traceback
from pathlib import Path
import pickle

import numpy as np
import pandas as pd
import joblib

from sklearn.metrics import mean_absolute_error, mean_squared_error
from statsmodels.tsa.statespace.sarimax import SARIMAX

try:
    from tensorflow.keras.models import load_model
except Exception as e:
    load_model = None
    _TF_IMPORT_ERROR = e


# ============================
# CẤU HÌNH MẶC ĐỊNH
# ============================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_TEST_DIR = BASE_DIR / "data_test"
ARTIFACTS_SARIMA_DIR = BASE_DIR / "artifacts_humidity"
MODEL_LSTM_DIR = BASE_DIR / "models_humidity"

TARGET_COLUMN = "relative_humidity_2m"


# ============================
# UTILS: METRICS + ALIGN
# ============================
def evaluate_metrics(y_true, y_pred):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    return float(mae), rmse


def _floor_hour(ts):
    """Hỗ trợ Series/DatetimeIndex/list -> floor về giờ."""
    t = pd.to_datetime(ts)
    if isinstance(t, pd.DatetimeIndex):
        return t.floor("h")
    return t.dt.floor("h")


def align_by_time(true_dates, true_values, pred_dates, pred_values):
    """
    Căn theo timestamp để so sánh đúng từng giờ.
    Trả về y_true, y_pred (numpy arrays) đã align.
    """
    if true_dates is None or pred_dates is None:
        return None, None

    true_ts = _floor_hour(true_dates)
    pred_ts = _floor_hour(pred_dates)

    df_true = pd.DataFrame({"ts": true_ts, "y_true": np.asarray(true_values, dtype=float)})
    df_pred = pd.DataFrame({"ts": pred_ts, "y_pred": np.asarray(pred_values, dtype=float)})

    merged = df_true.merge(df_pred, on="ts", how="inner").sort_values("ts")
    if merged.empty:
        return None, None
    return merged["y_true"].values, merged["y_pred"].values


# ============================
# SARIMA FORECAST
# ============================
def get_sarima_forecast(province_name: str, raw_df: pd.DataFrame, horizon: int, sarima_context: int):
    province_dir = ARTIFACTS_SARIMA_DIR / province_name
    model_path = province_dir / f"{province_name}_humidity_sarima.pkl"

    if not model_path.exists():
        return None, None, f"missing_sarima_artifact:{model_path.name}"

    with open(model_path, "rb") as f:
        model_data = pickle.load(f)

    df = raw_df.copy()
    time_col = df.columns[0]
    df[time_col] = pd.to_datetime(df[time_col])
    df = df.sort_values(time_col).set_index(time_col)

    df = df.asfreq("h")
    df[TARGET_COLUMN] = df[TARGET_COLUMN].interpolate(method="time").ffill().bfill()

    # recent history: đủ dài để mùa vụ ngày ổn
    recent_len = max(sarima_context, 24 * 30)
    recent_data = df[TARGET_COLUMN].tail(recent_len)
    if len(recent_data) < 48:
        return None, None, "too_little_history_for_sarima"

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
        return None, None, f"sarima_fit_error:{e}"

    forecast = fit.get_forecast(steps=horizon).predicted_mean.clip(0, 100)

    last_timestamp = recent_data.index.max()
    future_dates = pd.date_range(
        start=last_timestamp + pd.Timedelta(hours=1),
        periods=horizon,
        freq="h",
    )

    return future_dates, forecast.values, None


# ============================
# LSTM FORECAST
# ============================
def get_lstm_forecast(province_name: str, raw_df: pd.DataFrame, horizon: int, seq_len: int):
    if load_model is None:
        return None, f"no_tensorflow:{_TF_IMPORT_ERROR}"

    model_file = MODEL_LSTM_DIR / f"{province_name}.keras"
    scaler_x_file = MODEL_LSTM_DIR / f"scaler_X_{province_name}.pkl"
    scaler_y_file = MODEL_LSTM_DIR / f"scaler_Y_{province_name}.pkl"

    for p in [model_file, scaler_x_file, scaler_y_file]:
        if not p.exists():
            return None, f"missing_lstm_file:{p.name}"

    model = load_model(model_file)
    scaler_X = joblib.load(scaler_x_file)
    scaler_Y = joblib.load(scaler_y_file)

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
    if len(data_values) < seq_len:
        return None, f"too_little_history_for_lstm:{len(data_values)}<{seq_len}"

    last_sequence = data_values[-seq_len:]
    last_sequence_scaled = scaler_X.transform(last_sequence)
    X_pred = last_sequence_scaled.reshape(1, seq_len, -1)

    y_pred_scaled = model.predict(X_pred, verbose=0)
    y_pred = scaler_Y.inverse_transform(y_pred_scaled)  # (1, horizon) theo training của bạn

    # đảm bảo đúng horizon
    y = y_pred[0]
    if y.shape[0] != horizon:
        # nếu model ra khác horizon, vẫn cố cắt/pad
        if y.shape[0] > horizon:
            y = y[:horizon]
        else:
            y = np.pad(y, (0, horizon - y.shape[0]), mode="edge")
    return y, None


# ============================
# GROUND TRUTH
# ============================
def get_ground_truth(province_name: str, start_forecast_time: pd.Timestamp, horizon: int):
    test_file = DATA_TEST_DIR / f"{province_name}.csv"
    if not test_file.exists():
        return None, None, f"missing_test_file:{test_file.name}"

    df = pd.read_csv(test_file)
    time_col = df.columns[0]
    df[time_col] = pd.to_datetime(df[time_col])

    df[time_col] = df[time_col].dt.floor("h")
    start_forecast_time = pd.to_datetime(start_forecast_time).floor("h")
    end_forecast_time = start_forecast_time + pd.Timedelta(hours=horizon - 1)

    mask = (df[time_col] >= start_forecast_time) & (df[time_col] <= end_forecast_time)
    filtered_df = df.loc[mask].sort_values(time_col)

    if filtered_df.empty:
        return None, None, "test_time_not_match"

    return filtered_df[time_col], filtered_df[TARGET_COLUMN], None


# ============================
# ONE PROVINCE EVAL
# ============================
def evaluate_one_province(province: str, horizon: int, seq_len: int, sarima_context: int, verbose: bool):
    row = {
        "province": province,
        "sarima_mae": np.nan,
        "sarima_rmse": np.nan,
        "lstm_mae": np.nan,
        "lstm_rmse": np.nan,
        "winner": None,
        "status": "ok",
        "note": "",
    }

    data_file = DATA_DIR / f"{province}.csv"
    if not data_file.exists():
        row["status"] = "skip"
        row["note"] = f"missing_data_file:{data_file.name}"
        return row

    raw_df = pd.read_csv(data_file)
    time_col = raw_df.columns[0]
    raw_df[time_col] = pd.to_datetime(raw_df[time_col])

    last_hist_date = pd.to_datetime(raw_df[time_col].iloc[-1]).floor("h")
    start_forecast_time = last_hist_date + pd.Timedelta(hours=1)

    # Ground truth
    true_dates, true_values, gt_err = get_ground_truth(province, start_forecast_time, horizon)
    if gt_err is not None:
        row["status"] = "skip"
        row["note"] = gt_err
        return row

    # SARIMA
    sarima_dates, sarima_values, sar_err = get_sarima_forecast(province, raw_df, horizon, sarima_context)
    if sar_err is None:
        y_true_s, y_pred_s = align_by_time(true_dates, true_values, sarima_dates, sarima_values)
        if y_true_s is None:
            row["note"] += "sarima_align_empty;"
        else:
            mae_s, rmse_s = evaluate_metrics(y_true_s, y_pred_s)
            row["sarima_mae"] = mae_s
            row["sarima_rmse"] = rmse_s
    else:
        row["note"] += sar_err + ";"

    # LSTM
    lstm_values, lstm_err = get_lstm_forecast(province, raw_df, horizon, seq_len)
    lstm_dates = pd.date_range(start=start_forecast_time, periods=horizon, freq="h")
    if lstm_err is None:
        y_true_l, y_pred_l = align_by_time(true_dates, true_values, lstm_dates, lstm_values)
        if y_true_l is None:
            row["note"] += "lstm_align_empty;"
        else:
            mae_l, rmse_l = evaluate_metrics(y_true_l, y_pred_l)
            row["lstm_mae"] = mae_l
            row["lstm_rmse"] = rmse_l
    else:
        row["note"] += lstm_err + ";"

    # winner (theo MAE)
    if np.isfinite(row["sarima_mae"]) and np.isfinite(row["lstm_mae"]):
        row["winner"] = "SARIMA" if row["sarima_mae"] < row["lstm_mae"] else "LSTM"
    elif np.isfinite(row["sarima_mae"]):
        row["winner"] = "SARIMA_only"
    elif np.isfinite(row["lstm_mae"]):
        row["winner"] = "LSTM_only"
    else:
        row["winner"] = "none"
        row["status"] = "fail"

    if verbose:
        print(f"✅ {province} | SARIMA(MAE={row['sarima_mae']}) | LSTM(MAE={row['lstm_mae']}) | winner={row['winner']} | note={row['note']}")
    return row


# ============================
# MAIN
# ============================
def discover_provinces():
    if not DATA_DIR.exists():
        return []
    return sorted([p.stem for p in DATA_DIR.glob("*.csv")])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provinces", nargs="*", default=None, help="Danh sách tỉnh (tên file không đuôi .csv). Nếu bỏ trống -> tự quét trong data/.")
    parser.add_argument("--horizon", type=int, default=24, help="Số giờ dự báo (mặc định 24).")
    parser.add_argument("--seq-len", type=int, default=72, help="LSTM sequence length (mặc định 72).")
    parser.add_argument("--sarima-context", type=int, default=500, help="SARIMA context length (mặc định 500).")
    parser.add_argument("--out", type=str, default="compare_34_provinces.csv", help="File CSV output.")
    parser.add_argument("--verbose", action="store_true", help="In log từng tỉnh.")
    args = parser.parse_args()

    provinces = args.provinces if args.provinces else discover_provinces()
    if not provinces:
        print("❌ Không tìm thấy tỉnh nào. Hãy kiểm tra thư mục data/*.csv")
        return

    results = []
    for prov in provinces:
        try:
            results.append(evaluate_one_province(prov, args.horizon, args.seq_len, args.sarima_context, args.verbose))
        except Exception as e:
            results.append({
                "province": prov,
                "sarima_mae": np.nan, "sarima_rmse": np.nan,
                "lstm_mae": np.nan, "lstm_rmse": np.nan,
                "winner": "none",
                "status": "exception",
                "note": str(e),
            })

    df = pd.DataFrame(results)
    df.to_csv(args.out, index=False, encoding="utf-8-sig")

    print("\n================= TỔNG HỢP =================")
    ok_df = df[(df["status"] == "ok") & (df["winner"].isin(["SARIMA", "LSTM"]))].copy()

    if ok_df.empty:
        print("⚠️ Không có tỉnh nào đủ dữ liệu để so sánh cả 2 mô hình.")
        print(f"Đã lưu chi tiết vào: {args.out}")
        print(df[["province", "status", "note"]].head(20))
        return

    wins = ok_df["winner"].value_counts()
    print("🏆 Số tỉnh thắng (theo MAE):")
    print(wins.to_string())

    sarima_mae_mean = float(ok_df["sarima_mae"].mean())
    lstm_mae_mean = float(ok_df["lstm_mae"].mean())
    sarima_rmse_mean = float(ok_df["sarima_rmse"].mean())
    lstm_rmse_mean = float(ok_df["lstm_rmse"].mean())

    improve = (lstm_mae_mean - sarima_mae_mean) / max(lstm_mae_mean, 1e-9) * 100.0

    print("\n📉 Trung bình (chỉ các tỉnh so được cả 2 mô hình):")
    print(f"   SARIMA: MAE={sarima_mae_mean:.3f} | RMSE={sarima_rmse_mean:.3f}")
    print(f"   LSTM  : MAE={lstm_mae_mean:.3f} | RMSE={lstm_rmse_mean:.3f}")
    print(f"   👉 SARIMA tốt hơn ~{improve:.1f}% theo MAE (trung bình).")

    # Top tỉnh khó nhất / dễ nhất (theo best MAE)
    ok_df["best_mae"] = ok_df[["sarima_mae", "lstm_mae"]].min(axis=1)
    hardest = ok_df.sort_values("best_mae", ascending=False).head(10)[["province", "sarima_mae", "lstm_mae", "winner", "best_mae"]]
    easiest = ok_df.sort_values("best_mae", ascending=True).head(10)[["province", "sarima_mae", "lstm_mae", "winner", "best_mae"]]

    print("\n🔥 10 tỉnh khó nhất (best MAE cao):")
    print(hardest.to_string(index=False))

    print("\n✅ 10 tỉnh dễ nhất (best MAE thấp):")
    print(easiest.to_string(index=False))

    print(f"\n💾 Đã lưu bảng chi tiết vào: {args.out}")


if __name__ == "__main__":
    main()
