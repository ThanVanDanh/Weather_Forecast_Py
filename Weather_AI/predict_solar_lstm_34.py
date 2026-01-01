import os
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from tensorflow.keras.models import load_model

# ============================
# CẤU HÌNH ĐƯỜNG DẪN
# ============================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models_solar_multi_provinces"
RESULT_DIR = BASE_DIR / "results_34_solar_lstm"

# Tạo thư mục results nếu chưa có
RESULT_DIR.mkdir(exist_ok=True)

SEQ_LENGTH = 72
FORECAST_HORIZON = 24


def predict_for_province(province_name):
    """
    Hàm dự báo và xuất CSV cho 1 tỉnh cụ thể
    """
    # Đường dẫn file input và model
    csv_path = DATA_DIR / f"{province_name}.csv"
    model_path = MODEL_DIR / f"{province_name}.keras"
    scaler_x_path = MODEL_DIR / f"scaler_X_{province_name}.pkl"
    scaler_y_path = MODEL_DIR / f"scaler_Y_{province_name}.pkl"

    # 1. Kiểm tra file tồn tại
    if not csv_path.exists():
        # Trường hợp này ít xảy ra nếu quét từ folder data, nhưng cứ để
        return

    if not model_path.exists():
        print(f"⚠️ Bỏ qua {province_name}: Chưa có file model (.keras)")
        return

    print(f"\n🔮 Đang xử lý: {province_name}...")

    # 2. Load Resources (Model & Scalers)
    try:
        model = load_model(model_path)
        scaler_X = joblib.load(scaler_x_path)
        scaler_Y = joblib.load(scaler_y_path)
    except Exception as e:
        print(f"❌ Lỗi load model/scaler cho {province_name}: {e}")
        return

    # 3. Load & Process Data
    df = pd.read_csv(csv_path)

    # Xử lý Datetime
    time_col = df.columns[0]
    df[time_col] = pd.to_datetime(df[time_col])
    df = df.sort_values(by=time_col).reset_index(drop=True)

    # Feature Engineering
    df['hour'] = df[time_col].dt.hour
    df['month'] = df[time_col].dt.month
    df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
    df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
    df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)

    # Kiểm tra đủ dữ liệu không
    if len(df) < SEQ_LENGTH:
        print(f"❌ {province_name}: Dữ liệu không đủ {SEQ_LENGTH} dòng.")
        return

    # Lấy chuỗi dữ liệu cuối
    last_sequence = df.tail(SEQ_LENGTH)
    features = last_sequence[[
        'shortwave_radiation', 'hour_sin', 'hour_cos', 'month_sin', 'month_cos'
    ]].values

    last_time = df[time_col].iloc[-1]

    # 4. Predict
    input_scaled = scaler_X.transform(features)
    input_seq = np.expand_dims(input_scaled, axis=0)

    # verbose=0 để không hiện thanh loading của keras, tránh rối màn hình
    pred_scaled = model.predict(input_seq, verbose=0)

    pred_values = scaler_Y.inverse_transform(pred_scaled.reshape(-1, 1)).flatten()
    pred_values = np.maximum(pred_values, 0)  # Xử lý số âm

    # 5. Xuất CSV
    future_timeline = pd.date_range(start=last_time + pd.Timedelta(hours=1), periods=FORECAST_HORIZON, freq='h')

    result_df = pd.DataFrame({
        'Time': future_timeline,
        'Radiation_Forecast': pred_values,
        'Province': province_name
    })

    output_filename = f"forecast_{province_name}.csv"
    output_path = RESULT_DIR / output_filename
    result_df.to_csv(output_path, index=False)

    print(f"--> ✅ Đã lưu: {output_filename}")


if __name__ == "__main__":
    # Tự động quét tất cả file .csv trong folder data
    # glob("*.csv") sẽ tìm mọi file có đuôi csv
    all_csv_files = list(DATA_DIR.glob("*.csv"))

    print(f"📂 Tìm thấy {len(all_csv_files)} file dữ liệu trong thư mục data.")
    print("🚀 Bắt đầu chạy dự báo hàng loạt...")

    for csv_file in all_csv_files:
        # csv_file.stem sẽ lấy tên file mà không có đuôi (ví dụ: 'An_Giang.csv' -> 'An_Giang')
        province_name = csv_file.stem
        predict_for_province(province_name)

    print("\n🎉 === HOÀN TẤT TOÀN BỘ ===")
    print(f"Kiểm tra kết quả tại thư mục: {RESULT_DIR}")