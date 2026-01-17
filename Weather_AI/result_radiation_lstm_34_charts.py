import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import glob
from pathlib import Path

BASE_DIR = Path(os.getcwd())

ACTUAL_DIR = BASE_DIR / "data_future"

FORECAST_DIR = BASE_DIR / "results_train_shortwave_radiation_lstm"

GRAPH_DIR = BASE_DIR / "final_charts"
GRAPH_DIR.mkdir(exist_ok=True)

def aggregate_data():
    summary_data = []
    forecast_files = glob.glob(os.path.join(FORECAST_DIR, "forecast_*.csv"))

    if not forecast_files:
        print(f" Không tìm thấy file dự báo nào trong: {FORECAST_DIR}")
        return pd.DataFrame()

    print(f" Đang xử lý {len(forecast_files)} tỉnh...")

    for f_path in forecast_files:
        try:
            filename = os.path.basename(f_path)
            province_name = filename.replace("forecast_", "").replace(".csv", "")
            actual_path = ACTUAL_DIR / f"{province_name}.csv"

            if not actual_path.exists():
                print(f"️ Bỏ qua {province_name}: Thiếu file thực tế.")
                continue

            # Đọc dữ liệu
            df_pred = pd.read_csv(f_path)
            df_act = pd.read_csv(actual_path)

            # Xử lý thời gian
            df_pred['Time'] = pd.to_datetime(df_pred['Time'])
            time_col_act = df_act.columns[0]
            df_act[time_col_act] = pd.to_datetime(df_act[time_col_act])

            start_time = df_pred['Time'].min()
            end_time = df_pred['Time'].max()

            mask = (df_act[time_col_act] >= start_time) & (df_act[time_col_act] <= end_time)
            df_act_filtered = df_act.loc[mask]


            total_act = df_act_filtered['shortwave_radiation'].sum()
            total_pred = df_pred['Radiation_Forecast'].sum()

            summary_data.append({
                'Province': province_name,
                'Actual_Sum': total_act,
                'Predicted_Sum': total_pred,
                'Error': abs(total_pred - total_act)
            })

        except Exception as e:
            print(f" Lỗi khi đọc {province_name}: {e}")

    return pd.DataFrame(summary_data)

def plot_comparison_bar(df):
    if df.empty:
        print(" Không có dữ liệu để vẽ.")
        return
    df = df.sort_values('Province')

    # Cấu hình biểu đồ
    num_provinces = len(df)
    fig_width = max(14, num_provinces * 0.4)
    plt.figure(figsize=(fig_width, 8))

    indices = np.arange(num_provinces)
    width = 0.35

    # Vẽ cột
    plt.bar(indices - width / 2, df['Actual_Sum'], width, label='Thực tế (Data Future)', color='#1f77b4', alpha=0.9)
    plt.bar(indices + width / 2, df['Predicted_Sum'], width, label='Dự báo (AI Model)', color='#d62728', alpha=0.9)

    # Trang trí
    plt.title("TỔNG HỢP SO SÁNH BỨC XẠ MẶT TRỜI: THỰC TẾ vs DỰ BÁO (34 TỈNH)", fontsize=16, fontweight='bold', pad=20)
    plt.ylabel("Tổng Bức xạ trong ngày (W/m²)", fontsize=12)
    plt.xlabel("Tỉnh / Thành phố", fontsize=12)

    # Gắn tên tỉnh vào trục X
    plt.xticks(indices, df['Province'], rotation=90, fontsize=10)

    plt.legend(fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()

    # Lưu ảnh
    output_path = GRAPH_DIR / "comparison_all_provinces.png"
    plt.savefig(output_path, dpi=300)


    csv_path = GRAPH_DIR / "comparison_summary.csv"
    df.to_csv(csv_path, index=False)
    print(f" Đã lưu bảng số liệu tại: {csv_path}")
    plt.show()


if __name__ == "__main__":
    print(" Bắt đầu tổng hợp dữ liệu...")
    df_summary = aggregate_data()

    if not df_summary.empty:
        print("\n--- Mẫu dữ liệu ---")
        print(df_summary.head())

        plot_comparison_bar(df_summary)