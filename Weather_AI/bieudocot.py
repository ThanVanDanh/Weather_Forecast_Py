import pandas as pd
import matplotlib.pyplot as plt
import os
import glob
from pathlib import Path
import numpy as np

# =========================================
# 1. CẤU HÌNH & ĐƯỜNG DẪN
# =========================================

BASE_DIR = Path(os.getcwd())
ACTUAL_DIR = BASE_DIR / "data_future"
FORECAST_DIR = BASE_DIR / "results_dual_input"
GRAPH_DIR = BASE_DIR / "comparison_bar_charts"  # Thư mục lưu ảnh mới
GRAPH_DIR.mkdir(exist_ok=True)


# =========================================
# 2. HÀM VẼ BIỂU ĐỒ CỘT
# =========================================
def plot_bar_chart(province_name):
    actual_path = ACTUAL_DIR / f"{province_name}.csv"
    forecast_path = FORECAST_DIR / f"forecast_{province_name}.csv"

    # Kiểm tra file tồn tại
    if not actual_path.exists() or not forecast_path.exists():
        return False

    try:
        # Đọc dữ liệu
        df_act = pd.read_csv(actual_path)
        df_pred = pd.read_csv(forecast_path)

        # Xử lý thời gian
        time_col_act = df_act.columns[0]
        df_act[time_col_act] = pd.to_datetime(df_act[time_col_act])
        df_pred['Time'] = pd.to_datetime(df_pred['Time'])

        # Đồng bộ khung thời gian
        start_time = df_pred['Time'].min()
        end_time = df_pred['Time'].max()

        # Lọc dữ liệu thực tế cho khớp với dự báo
        mask = (df_act[time_col_act] >= start_time) & (df_act[time_col_act] <= end_time)
        df_act_filtered = df_act.loc[mask].copy().reset_index(drop=True)

        # Cắt cho bằng nhau nếu lệch dòng
        min_len = min(len(df_act_filtered), len(df_pred))
        df_act_filtered = df_act_filtered.head(min_len)
        df_pred = df_pred.head(min_len)

        # -----------------------------------------
        # VẼ BIỂU ĐỒ CỘT (BAR CHART)
        # -----------------------------------------
        plt.figure(figsize=(12, 6))

        # Tạo mảng chỉ số cho trục X
        indices = np.arange(len(df_pred))
        width = 0.35  # Độ rộng của cột

        # Vẽ 2 nhóm cột
        plt.bar(indices - width / 2, df_act_filtered['shortwave_radiation'], width, label='Thực tế', color='#1f77b4',
                alpha=0.8)
        plt.bar(indices + width / 2, df_pred['Radiation_Forecast'], width, label='Dự báo', color='#d62728', alpha=0.8)

        # Trang trí
        plt.title(f"So sánh Bức xạ từng giờ: {province_name}", fontsize=14, fontweight='bold')
        plt.ylabel("Bức xạ (W/m²)", fontsize=12)
        plt.xlabel("Thời gian (Giờ)", fontsize=12)

        # Tạo nhãn trục X là giờ (chỉ lấy giờ chẵn để đỡ rối)
        time_labels = df_pred['Time'].dt.strftime('%H:%M')
        plt.xticks(indices[::2], time_labels[::2], rotation=45)

        plt.legend()
        plt.grid(axis='y', linestyle='--', alpha=0.5)
        plt.tight_layout()

        # Lưu ảnh
        output_path = GRAPH_DIR / f"bar_{province_name}.png"
        plt.savefig(output_path, dpi=200)
        plt.close()

        # Tính tổng năng lượng (Sum) để so sánh nhanh
        total_act = df_act_filtered['shortwave_radiation'].sum()
        total_pred = df_pred['Radiation_Forecast'].sum()
        diff_percent = ((total_pred - total_act) / total_act) * 100 if total_act > 0 else 0

        print(f"✅ {province_name}: Tổng thực tế={total_act:.0f}, Dự báo={total_pred:.0f} (Lệch {diff_percent:+.1f}%)")
        return True

    except Exception as e:
        print(f"❌ Lỗi {province_name}: {e}")
        return False


# =========================================
# 3. MAIN
# =========================================
if __name__ == "__main__":
    # Lấy danh sách file dự báo
    forecast_files = glob.glob(str(FORECAST_DIR / "forecast_*.csv"))

    print(f"🚀 Bắt đầu vẽ biểu đồ cột cho {len(forecast_files)} tỉnh...")
    print("-" * 50)

    count = 0
    for f in forecast_files:
        province = os.path.basename(f).replace("forecast_", "").replace(".csv", "")
        if plot_bar_chart(province):
            count += 1

    print("-" * 50)
    print(f"🎉 Đã xong! {count} biểu đồ được lưu tại thư mục: {GRAPH_DIR}")