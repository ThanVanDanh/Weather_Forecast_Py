"""
FILE 2: PREDICT_RAIN.PY
Chức năng: Load model, dự báo 24h & 5 ngày, xuất JSON
"""
import pandas as pd
import numpy as np
import joblib
import json
import matplotlib.pyplot as plt
from pathlib import Path
from tensorflow.keras.models import load_model
from datetime import timedelta

# --- CẤU HÌNH ---
DATA_DIR = Path("data")
MODEL_DIR = Path("models")
JSON_DIR = Path("json_output")
JSON_DIR.mkdir(exist_ok=True)

WINDOW_SIZE = 72
FORECAST_STEPS = 120  # 5 ngày * 24h = 120h


# ============================
# 1. HÀM DỰ BÁO LSTM (Cuốn chiếu)
# ============================
def predict_lstm(province, last_window_data):
    """
    last_window_data: 72 giá trị thực tế gần nhất
    """
    model_path = MODEL_DIR / f"{province}_lstm.keras"
    scaler_path = MODEL_DIR / f"{province}_scaler.pkl"

    if not model_path.exists() or not scaler_path.exists():
        return np.zeros(FORECAST_STEPS)

    model = load_model(model_path)
    scaler = joblib.load(scaler_path)

    # Scale input
    input_scaled = scaler.transform(last_window_data.reshape(-1, 1))
    current_batch = input_scaled.reshape(1, WINDOW_SIZE, 1)

    predictions_scaled = []

    # Dự báo cuốn chiếu
    for i in range(FORECAST_STEPS):
        pred = model.predict(current_batch, verbose=0)[0, 0]
        predictions_scaled.append(pred)

        # Cập nhật cửa sổ trượt: bỏ cái đầu, thêm cái vừa dự báo vào cuối
        pred_reshaped = np.array([[[pred]]])
        current_batch = np.append(current_batch[:, 1:, :], pred_reshaped, axis=1)

    # Inverse scale về giá trị thực
    predictions = scaler.inverse_transform(np.array(predictions_scaled).reshape(-1, 1))
    return predictions.flatten()


# ============================
# 2. HÀM DỰ BÁO SARIMA
# ============================
def predict_sarima(province, steps):
    path = MODEL_DIR / f"{province}_sarima.pkl"
    if not path.exists():
        return np.zeros(steps)

    model_res = joblib.load(path)
    # Forecast tiếp theo (lưu ý: SARIMA tĩnh cần refit nếu muốn cập nhật data mới nhất vào trạng thái)
    # Ở đây ta dùng hàm forecast đơn giản từ trạng thái đã lưu
    forecast = model_res.forecast(steps=steps)
    return forecast.values


# ============================
# 3. XỬ LÝ & XUẤT JSON
# ============================
def process_province(province, plot_chart=False):
    csv_path = DATA_DIR / f"{province}.csv"
    if not csv_path.exists():
        return

    # Đọc dữ liệu mô phỏng "Real-time"
    df = pd.read_csv(csv_path)
    df['time'] = pd.to_datetime(df['time'])
    df = df.set_index('time').sort_index().asfreq('h').fillna(0)

    # Lấy dữ liệu cuối cùng để dự báo
    last_time = df.index[-1]
    if len(df) < WINDOW_SIZE:
        print(f"[{province}] Không đủ dữ liệu.")
        return

    last_window = df['rain'].values[-WINDOW_SIZE:]

    # --- DỰ BÁO ---
    pred_lstm = predict_lstm(province, last_window)
    pred_sarima = predict_sarima(province, FORECAST_STEPS)

    # Kết hợp (Ensemble): Lấy trung bình cộng, chặn dưới 0
    final_pred = (pred_lstm + pred_sarima) / 2
    final_pred = np.maximum(final_pred, 0)  # Mưa không âm

    # Tạo khung thời gian tương lai
    future_times = [last_time + timedelta(hours=i + 1) for i in range(FORECAST_STEPS)]

    # --- XUẤT JSON 1: 24 GIỜ TỚI ---
    json_24h = []
    for i in range(24):
        json_24h.append({
            "time": future_times[i].strftime("%Y-%m-%d %H:%M:%S"),
            "rain_forecast": round(float(final_pred[i]), 2),
            "model_lstm": round(float(pred_lstm[i]), 2),
            "model_sarima": round(float(pred_sarima[i]), 2)
        })

    with open(JSON_DIR / f"{province}_24h.json", "w", encoding='utf-8') as f:
        json.dump(json_24h, f, indent=4)

    # --- XUẤT JSON 2: 5 NGÀY TỚI ---
    json_5days = []
    # Gom nhóm theo ngày
    df_future = pd.DataFrame({'time': future_times, 'rain': final_pred})
    df_future['date'] = df_future['time'].dt.date
    daily_sum = df_future.groupby('date')['rain'].sum()

    for date, val in daily_sum.items():
        json_5days.append({
            "date": str(date),
            "total_rain": round(float(val), 2)
        })

    with open(JSON_DIR / f"{province}_5d.json", "w", encoding='utf-8') as f:
        json.dump(json_5days, f, indent=4)

    print(f"[{province}] Đã xuất JSON xong.")

    # --- VẼ BIỂU ĐỒ KIỂM TRA (Nếu cần) ---
    if plot_chart:
        plt.figure(figsize=(10, 5))
        # Vẽ 72h quá khứ
        plt.plot(df.index[-72:], df['rain'][-72:], label='Quá khứ (Thực tế)', color='black')
        # Vẽ dự báo
        plt.plot(future_times, final_pred, label='Dự báo (Gộp)', color='green')
        plt.plot(future_times, pred_lstm, label='LSTM', linestyle='--', alpha=0.5)
        plt.plot(future_times, pred_sarima, label='SARIMA', linestyle=':', alpha=0.5)

        plt.title(f"Dự báo Mưa: {province}")
        plt.legend()
        plt.grid(True)
        # Lưu ảnh thay vì show để server chạy ngầm
        plt.savefig(JSON_DIR / f"{province}_chart.png")
        plt.close()


# ============================
# MAIN
# ============================
def main():
    print("BẮT ĐẦU CẬP NHẬT DỰ BÁO...")
    csv_files = list(DATA_DIR.glob("*.csv"))

    for csv in csv_files:
        # Thêm tham số True để vẽ biểu đồ kiểm tra
        process_province(csv.stem, plot_chart=True)

    print("HOÀN TẤT CẬP NHẬT.")


if __name__ == "__main__":
    main()