import os
import glob
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
import matplotlib.pyplot as plt
from tensorflow.keras.models import load_model
from sklearn.preprocessing import MinMaxScaler

# ============================
# CẤU HÌNH (PHẢI KHỚP FILE TRAIN)
# ============================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "model_solar_lstm"  # Thư mục chứa model An Giang
MODEL_FILE = os.path.join(MODEL_DIR, "solar_lstm_angiang.keras")
SCALER_FILE = os.path.join(MODEL_DIR, "solar_scaler_angiang.pkl")

# Cấu hình Univariate
FEATURE_COLUMNS = ['shortwave_radiation']
TARGET_COLUMN = 'shortwave_radiation'
SEQ_LENGTH = 72
FORECAST_DAYS = 5
FORECAST_STEPS = FORECAST_DAYS * 24


def get_latest_data_angiang():
    """
    Tìm file An Giang và lấy 72 giờ dữ liệu cuối cùng để làm đầu vào dự báo.
    """
    # 1. Tìm file An Giang giống như lúc train
    all_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
    angiang_files = [f for f in all_files if "an giang" in os.path.basename(f).lower().replace("_", " ")]

    if not angiang_files:
        raise FileNotFoundError(f"Không tìm thấy file dữ liệu An Giang trong {DATA_DIR} để lấy dữ liệu đầu vào!")

    # Lấy file đầu tiên tìm được
    target_file = angiang_files[0]
    print(f"📂 Đang lấy dữ liệu quá khứ từ: {os.path.basename(target_file)}")

    df = pd.read_csv(target_file)

    # Đảm bảo có cột cần thiết
    if TARGET_COLUMN not in df.columns:
        raise ValueError(f"File không chứa cột {TARGET_COLUMN}")

    # Lấy đúng cột target
    df = df[[TARGET_COLUMN]]

    # Kiểm tra đủ dữ liệu không
    if len(df) < SEQ_LENGTH:
        raise ValueError(f"Dữ liệu trong file quá ngắn (cần ít nhất {SEQ_LENGTH} dòng).")

    # Lấy SEQ_LENGTH dòng cuối cùng
    return df.tail(SEQ_LENGTH).values


def main():
    # 1. Kiểm tra model và scaler
    if not os.path.exists(MODEL_FILE) or not os.path.exists(SCALER_FILE):
        print(f"Không tìm thấy model hoặc scaler tại {MODEL_DIR}.")
        print("   Hãy chạy file 'train_radiation_model_lstm.py' trước!")
        return

    print("Đang tải model và scaler...")
    model = load_model(MODEL_FILE)
    scaler = joblib.load(SCALER_FILE)

    # 2. Lấy dữ liệu thực tế (72 giờ cuối)
    try:
        raw_data = get_latest_data_angiang()  # Shape: (72, 1)
    except Exception as e:
        print(e)
        return

    # 3. Scale dữ liệu
    # Model Univariate được train với dữ liệu (0,1), nên đầu vào cũng phải scale
    current_seq_scaled = scaler.transform(raw_data)  # Shape: (72, 1)

    # Reshape cho LSTM: (Samples, TimeSteps, Features) -> (1, 72, 1)
    current_seq = np.expand_dims(current_seq_scaled, axis=0)

    print(f"🚀 Bắt đầu dự báo {FORECAST_DAYS} ngày ({FORECAST_STEPS} giờ) cho An Giang...")

    predictions_scaled = []

    # 4. Vòng lặp dự báo (Recursive / Autoregressive)
    # Vì không có biến ngoại sinh (nhiệt độ tương lai...), ta lấy kết quả dự báo
    # nhét ngược lại vào đầu vào để dự báo bước tiếp theo.

    for i in range(FORECAST_STEPS):
        # a. Dự báo bước tiếp theo
        pred = model.predict(current_seq, verbose=0)  # Output shape (1, 1)
        pred_val = pred[0, 0]  # Lấy giá trị scalar

        predictions_scaled.append(pred_val)

        # b. Cập nhật cửa sổ trượt (Sliding Window)
        # current_seq đang là (1, 72, 1)
        # Ta bỏ phần tử đầu tiên (cũ nhất), thêm phần tử vừa dự báo vào cuối

        # Cắt bỏ phần tử đầu tiên: lấy từ index 1 đến hết
        new_seq = current_seq[:, 1:, :]

        # Tạo array cho phần tử mới (cần đúng shape (1, 1, 1))
        new_element = np.array([[[pred_val]]])

        # Nối lại
        current_seq = np.concatenate([new_seq, new_element], axis=1)

    # 5. Inverse Scale (Đưa về đơn vị W/m2)
    # Chuyển list thành mảng numpy (N, 1)
    predictions_scaled_arr = np.array(predictions_scaled).reshape(-1, 1)

    real_predictions = scaler.inverse_transform(predictions_scaled_arr)

    # Xử lý số âm (Bức xạ ko thể âm)
    real_predictions = np.maximum(real_predictions, 0)

    print("✅ Dự báo hoàn tất!")

    # 6. Vẽ biểu đồ và Lưu
    plt.figure(figsize=(12, 6))

    # Tạo trục X (Giờ)
    hours = range(1, FORECAST_STEPS + 1)

    plt.plot(hours, real_predictions, label='Dự báo Solar (Univariate)', color='orangered', linewidth=2)
    plt.title(f'Dự báo Bức xạ mặt trời An Giang - {FORECAST_DAYS} ngày tới (Mô hình đơn biến)')
    plt.xlabel('Giờ tương lai')
    plt.ylabel('Bức xạ (W/m²)')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()

    # Lưu ảnh
    plot_path = os.path.join(MODEL_DIR, "forecast_result_angiang.png")
    plt.savefig(plot_path)
    print(f"📊 Đã lưu biểu đồ tại: {plot_path}")

    # Hiển thị
    plt.show()

    # Xuất ra CSV
    df_result = pd.DataFrame({
        'Hour_Index': hours,
        'Predicted_Solar_Radiation': real_predictions.flatten()
    })
    csv_path = os.path.join(MODEL_DIR, "forecast_angiang.csv")
    df_result.to_csv(csv_path, index=False)
    print(f"📄 Đã lưu file kết quả CSV tại: {csv_path}")


if __name__ == "__main__":
    main()