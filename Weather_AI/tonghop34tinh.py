import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import glob
from pathlib import Path

# =========================================
# 1. CẤU HÌNH ĐƯỜNG DẪN
# =========================================
BASE_DIR = Path(os.getcwd())

# Thư mục dữ liệu Thực tế
ACTUAL_DIR = BASE_DIR / "data_future"

# Thư mục dự báo LSTM
FORECAST_LSTM_DIR = BASE_DIR / "results_train_shortwave_radiation_lstm"

# Thư mục dự báo SARIMAX
FORECAST_SARIMAX_DIR = BASE_DIR / "predictions_sarimax_solar_24h"

# Thư mục dự báo HYBRID (Cập nhật theo ảnh: predictions_v2_hybrid)
FORECAST_HYBRID_DIR = BASE_DIR / "predictions_v2_hybrid"

# Thư mục lưu biểu đồ
GRAPH_DIR = BASE_DIR / "final_charts"
GRAPH_DIR.mkdir(parents=True, exist_ok=True)


# =========================================
# 2. HÀM TỔNG HỢP DỮ LIỆU
# =========================================
def aggregate_data():
    summary_data = []

    # Lấy danh sách tỉnh dựa trên folder LSTM
    lstm_files = glob.glob(str(FORECAST_LSTM_DIR / "forecast_*.csv"))

    if not lstm_files:
        print(f"❌ Không tìm thấy file LSTM trong: {FORECAST_LSTM_DIR}")
        return pd.DataFrame()

    print(f"🔄 Đang xử lý {len(lstm_files)} tỉnh...")

    for f_path in lstm_files:
        try:
            # Lấy tên tỉnh
            filename = os.path.basename(f_path)
            province_name = filename.replace("forecast_", "").replace(".csv", "")

            # --- 1. Đọc LSTM (Làm mốc thời gian) ---
            df_lstm = pd.read_csv(f_path)
            df_lstm['Time'] = pd.to_datetime(df_lstm['Time'])
            start_time = df_lstm['Time'].min()
            end_time = df_lstm['Time'].max()

            # Cột LSTM là 'Radiation_Forecast'
            total_lstm = df_lstm['Radiation_Forecast'].sum()

            # --- 2. Đọc THỰC TẾ ---
            actual_path = ACTUAL_DIR / f"{province_name}.csv"
            total_act = 0
            if actual_path.exists():
                df_act = pd.read_csv(actual_path)
                # Lấy tên cột thời gian đầu tiên
                time_col = df_act.columns[0]
                df_act[time_col] = pd.to_datetime(df_act[time_col])

                # Lọc theo khung giờ
                mask = (df_act[time_col] >= start_time) & (df_act[time_col] <= end_time)
                total_act = df_act.loc[mask, 'shortwave_radiation'].sum()

            # --- 3. Đọc SARIMAX ---
            # File mẫu: Bac_Ninh_predicted.csv
            sarimax_path = FORECAST_SARIMAX_DIR / f"{province_name}_predicted.csv"
            total_sarimax = 0
            if sarimax_path.exists():
                df_sari = pd.read_csv(sarimax_path)
                # Cột thời gian: 'time', Giá trị: 'predicted_radiation'
                if 'time' in df_sari.columns:
                    df_sari['time'] = pd.to_datetime(df_sari['time'])
                    mask = (df_sari['time'] >= start_time) & (df_sari['time'] <= end_time)
                    if 'predicted_radiation' in df_sari.columns:
                        total_sarimax = df_sari.loc[mask, 'predicted_radiation'].sum()

            # --- 4. Đọc HYBRID (Cập nhật) ---
            # Theo ảnh bạn gửi: File nằm trong predictions_v2_hybrid, tên là forecast_{Tên_Tỉnh}.csv
            # Cột dữ liệu là 'predicted_radiation'
            hybrid_path = FORECAST_HYBRID_DIR / f"forecast_{province_name}.csv"
            total_hybrid = 0

            if hybrid_path.exists():
                df_hyb = pd.read_csv(hybrid_path)

                # Kiểm tra tên cột thời gian (có thể là 'time' hoặc 'Time')
                t_col = 'time' if 'time' in df_hyb.columns else 'Time'

                if t_col in df_hyb.columns and 'predicted_radiation' in df_hyb.columns:
                    df_hyb[t_col] = pd.to_datetime(df_hyb[t_col])
                    mask = (df_hyb[t_col] >= start_time) & (df_hyb[t_col] <= end_time)
                    total_hybrid = df_hyb.loc[mask, 'predicted_radiation'].sum()
                else:
                    print(f"⚠️ {province_name}: File Hybrid thiếu cột 'time' hoặc 'predicted_radiation'")
            else:
                # Fallback: Thử tìm file dạng cũ {Tên}_hybrid_predicted.csv nếu file mới không có
                old_hybrid_path = FORECAST_HYBRID_DIR / f"{province_name}_hybrid_predicted.csv"
                if old_hybrid_path.exists():
                    df_hyb = pd.read_csv(old_hybrid_path)
                    if 'time' in df_hyb.columns:
                        df_hyb['time'] = pd.to_datetime(df_hyb['time'])
                        mask = (df_hyb['time'] >= start_time) & (df_hyb['time'] <= end_time)
                        total_hybrid = df_hyb.loc[mask, 'predicted_radiation'].sum()

            # --- Tổng hợp ---
            summary_data.append({
                'Province': province_name,
                'Actual': total_act,
                'LSTM': total_lstm,
                'SARIMAX': total_sarimax,
                'Hybrid': total_hybrid
            })

        except Exception as e:
            print(f"❌ Lỗi {province_name}: {e}")

    return pd.DataFrame(summary_data)


# =========================================
# 3. VẼ BIỂU ĐỒ 4 CỘT
# =========================================
def plot_comparison_4_cols(df):
    if df.empty:
        print("⚠️ Không có dữ liệu để vẽ.")
        return

    df = df.sort_values('Province')
    num_provinces = len(df)

    # Tự động chỉnh kích thước ảnh
    fig_width = max(20, num_provinces * 0.7)
    plt.figure(figsize=(fig_width, 10))

    indices = np.arange(num_provinces)
    width = 0.2  # Độ rộng cột

    # Vẽ 4 cột
    plt.bar(indices - 1.5 * width, df['Actual'], width, label='Thực tế', color='#1f77b4', edgecolor='white')
    plt.bar(indices - 0.5 * width, df['LSTM'], width, label='LSTM', color='#d62728', edgecolor='white')
    plt.bar(indices + 0.5 * width, df['SARIMAX'], width, label='SARIMAX', color='#2ca02c', edgecolor='white')

    # Cột Hybrid (Màu Tím đậm)
    plt.bar(indices + 1.5 * width, df['Hybrid'], width, label='Hybrid (LSTM+SARIMAX)', color='#9467bd',
            edgecolor='white')

    # Trang trí
    plt.title("SO SÁNH TỔNG BỨC XẠ: THỰC TẾ vs CÁC MÔ HÌNH (34 TỈNH)", fontsize=18, fontweight='bold', pad=20)
    plt.ylabel("Tổng Bức xạ (W/m²)", fontsize=14)
    plt.xlabel("Tỉnh / Thành phố", fontsize=14)
    plt.xticks(indices, df['Province'], rotation=90, fontsize=11)

    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.legend(fontsize=14, loc='upper right')
    plt.tight_layout()

    # Lưu ảnh
    output_path = GRAPH_DIR / "comparison_4_models_final.png"
    plt.savefig(output_path, dpi=300)
    print(f"\n✅ Đã lưu biểu đồ: {output_path}")

    # Lưu CSV số liệu
    df.to_csv(GRAPH_DIR / "comparison_4_models_data.csv", index=False)
    plt.show()


# =========================================
# MAIN
# =========================================
if __name__ == "__main__":
    # Kiểm tra folder
    if not FORECAST_HYBRID_DIR.exists():
        print(f"⚠️ Cảnh báo: Không tìm thấy thư mục Hybrid: {FORECAST_HYBRID_DIR}")
        print("👉 Vui lòng kiểm tra lại tên thư mục chứa kết quả Hybrid.")

    df_sum = aggregate_data()

    if not df_sum.empty:
        print("\n--- Mẫu dữ liệu ---")
        print(df_sum.head())
        plot_comparison_4_cols(df_sum)