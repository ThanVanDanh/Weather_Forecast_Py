import os
import glob
import numpy as np
import pandas as pd
import joblib
import matplotlib.pyplot as plt
from pathlib import Path
from tensorflow.keras.models import load_model
from pvlib.location import Location

# ============================
# CẤU HÌNH
# ============================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "model_solar_clearsky"

MODEL_FILE = MODEL_DIR / "lstm_clearsky.keras"
SCALER_FILE = MODEL_DIR / "scaler_clearsky.pkl"

LAT, LON = 10.01000, 105.08000
TZ = 'Asia/Bangkok'
SEQ_LENGTH = 48  # Phải khớp với file train
FORECAST_DAYS = 5
FORECAST_STEPS = FORECAST_DAYS * 24


def get_latest_daytime_sequence(seq_length):
    """
    Lấy chuỗi dữ liệu lịch sử NHƯNG chỉ lấy các giờ ban ngày (06:00-17:00)
    để khớp với cách model được train.
    """
    all_files = glob.glob(str(DATA_DIR / "*.csv"))
    angiang_files = [f for f in all_files if "an giang" in os.path.basename(f).lower().replace("_", " ")]
    target_file = angiang_files[0]

    df = pd.read_csv(target_file)
    df['time'] = pd.to_datetime(df['time'])
    df = df.set_index('time').sort_index()
    df = df.resample('h').mean().interpolate()

    # Tính k index lịch sử
    site = Location(LAT, LON, tz=TZ)
    cs = site.get_clearsky(df.index)
    df['clear_sky'] = cs['ghi'].values
    df['k_index'] = df['shortwave_radiation'] / df['clear_sky'].replace(0, np.nan)
    df['k_index'] = df['k_index'].fillna(0).clip(0, 1.2)

    # Lọc chỉ lấy ban ngày
    daytime_df = df.between_time('06:00', '17:00')

    # Lấy SEQ_LENGTH điểm dữ liệu cuối cùng của ban ngày
    if len(daytime_df) < seq_length:
        raise ValueError("Dữ liệu lịch sử không đủ dài.")

    last_k = daytime_df['k_index'].values[-seq_length:]
    last_time = df.index[-1]  # Mốc thời gian thực cuối cùng (để bắt đầu dự báo)

    return last_k.reshape(-1, 1), last_time


def main():
    if not MODEL_FILE.exists():
        print("Chưa có model Clear Sky.")
        return

    # 1. Load Resources
    model = load_model(MODEL_FILE)
    scaler = joblib.load(SCALER_FILE)

    # 2. Chuẩn bị dữ liệu đầu vào (Chỉ sequence ban ngày)
    k_past_raw, last_time_history = get_latest_daytime_sequence(SEQ_LENGTH)

    # Scale đầu vào
    # sequence_queue: Chứa các giá trị k đã scale, dùng để cuộn (rolling)
    sequence_queue = scaler.transform(k_past_raw).flatten().tolist()

    # 3. Tạo khung thời gian tương lai (5 ngày tới)
    start_future = last_time_history + pd.Timedelta(hours=1)
    future_times = pd.date_range(start=start_future, periods=FORECAST_STEPS, freq='h', tz=TZ)

    # Tính Clear Sky lý thuyết cho tương lai
    site = Location(LAT, LON, tz=TZ)
    future_cs = site.get_clearsky(future_times)
    ghi_clear_future = future_cs['ghi'].values

    final_predictions = []
    predicted_k_values = []

    print(f"🚀 Bắt đầu dự báo thông minh ({FORECAST_DAYS} ngày)...")

    # 4. Vòng lặp dự báo từng giờ
    for i, current_time in enumerate(future_times):
        hour = current_time.hour

        # Kiểm tra xem giờ này có phải ban ngày không?
        is_daytime = 6 <= hour <= 17

        if is_daytime:
            # === BAN NGÀY: DÙNG AI DỰ BÁO ===

            # Lấy sequence hiện tại để dự báo
            current_seq_array = np.array(sequence_queue[-SEQ_LENGTH:]).reshape(1, SEQ_LENGTH, 1)

            # Predict
            pred_scaled = model.predict(current_seq_array, verbose=0)[0, 0]

            # Cập nhật hàng đợi: Thêm giá trị vừa dự báo vào cuối
            # (Để dùng cho dự báo giờ ban ngày tiếp theo)
            sequence_queue.append(pred_scaled)

            # Inverse scale để lấy k thật
            k_val = scaler.inverse_transform([[pred_scaled]])[0, 0]
            k_val = max(0, k_val)  # Không âm

        else:
            # === BAN ĐÊM: KHÔNG CẦN AI ===
            k_val = 0.0
            # Lưu ý: Không thêm số 0 vào sequence_queue!
            # Vì model chỉ được train trên chuỗi liên tục các giờ nắng.
            # Việc bỏ qua đêm giúp model "nhảy" từ 17h hôm nay sang 6h sáng mai mượt mà.

        predicted_k_values.append(k_val)

        # Tính bức xạ: Actual = k * ClearSky
        # Nếu là ban đêm, ghi_clear_future[i] tự động ~ 0, nên kết quả cũng là 0
        final_rad = k_val * ghi_clear_future[i]
        final_predictions.append(final_rad)

    # 5. Lưu kết quả
    df_result = pd.DataFrame({
        'time': future_times,
        'k_index_pred': predicted_k_values,
        'ClearSky_Theoretical': ghi_clear_future,
        'Predicted_Radiation': final_predictions
    })

    save_path = MODEL_DIR / "forecast_clearsky_angiang.csv"
    df_result.to_csv(save_path, index=False)
    print(f"📄 Đã lưu kết quả: {save_path}")

    # 6. Vẽ lại biểu đồ kiểm tra
    plt.figure(figsize=(12, 6))
    plt.plot(df_result['time'], df_result['ClearSky_Theoretical'], 'k--', alpha=0.3, label='Clear Sky (Lý thuyết)')
    plt.plot(df_result['time'], df_result['Predicted_Radiation'], 'r-', linewidth=2, label='Dự báo AI (Mới)')
    plt.title('Dự báo Bức xạ (Daytime-Only Logic)')
    plt.legend()
    plt.savefig(MODEL_DIR / "check_forecast.png")
    plt.show()


if __name__ == "__main__":
    main()