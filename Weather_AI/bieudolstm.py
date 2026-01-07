import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
import glob
from pathlib import Path
from sklearn.metrics import mean_absolute_error, root_mean_squared_error

# =========================================
# 1. CẤU HÌNH & ĐƯỜNG DẪN
# =========================================

BASE_DIR = Path(os.getcwd())
ACTUAL_DIR = BASE_DIR / "data_future"
FORECAST_DIR = BASE_DIR / "results_dual_input"

# Thư mục lưu ảnh biểu đồ
GRAPH_DIR = BASE_DIR / "comparison_charts"
GRAPH_DIR.mkdir(exist_ok=True)

# Danh sách lưu kết quả tổng hợp
summary_metrics = []


# =========================================
# 2. HÀM XỬ LÝ CHO 1 TỈNH
# =========================================
def process_one_province(province_name):
    actual_path = ACTUAL_DIR / f"{province_name}.csv"
    forecast_path = FORECAST_DIR / f"forecast_{province_name}.csv"

    # --- Kiểm tra file ---
    if not actual_path.exists():
        print(f"⚠️ {province_name}: Thiếu file thực tế (data_future). Bỏ qua.")
        return None

    if not forecast_path.exists():
        print(f"⚠️ {province_name}: Thiếu file dự báo. Bỏ qua.")
        return None

    # --- Đọc dữ liệu ---
    try:
        df_actual_raw = pd.read_csv(actual_path)
        time_col_act = df_actual_raw.columns[0]
        df_actual_raw[time_col_act] = pd.to_datetime(df_actual_raw[time_col_act])

        df_pred = pd.read_csv(forecast_path)
        df_pred['Time'] = pd.to_datetime(df_pred['Time'])

        # --- Đồng bộ thời gian ---
        start_time = df_pred['Time'].min()
        end_time = df_pred['Time'].max()

        # Lọc bản THỰC TẾ theo khung dự báo
        mask = (df_actual_raw[time_col_act] >= start_time) & (df_actual_raw[time_col_act] <= end_time)
        df_actual_filtered = df_actual_raw.loc[mask].copy().reset_index(drop=True)

        # Kiểm tra dữ liệu rỗng sau khi lọc
        if df_actual_filtered.empty:
            print(f"⚠️ {province_name}: Không tìm thấy dữ liệu thực tế trong khoảng {start_time} - {end_time}")
            return None

        # Cắt cho bằng dòng nhau (Trường hợp lệch 1-2 dòng)
        min_len = min(len(df_actual_filtered), len(df_pred))
        df_actual_filtered = df_actual_filtered.head(min_len)
        df_pred = df_pred.head(min_len)

        # --- Tính toán sai số ---
        y_true = df_actual_filtered['shortwave_radiation']
        y_pred = df_pred['Radiation_Forecast']

        mae = mean_absolute_error(y_true, y_pred)
        rmse = root_mean_squared_error(y_true, y_pred)

        # --- Vẽ biểu đồ ---
        plt.figure(figsize=(14, 7))

        plt.plot(df_actual_filtered[time_col_act],
                 df_actual_filtered['shortwave_radiation'],
                 label='Thực tế (Ground Truth)',
                 color='#1f77b4', linewidth=2.5, alpha=0.8)

        plt.plot(df_pred['Time'],
                 df_pred['Radiation_Forecast'],
                 label='Dự báo (AI Prediction)',
                 color='#d62728', linestyle='--', linewidth=2, marker='o', markersize=5)

        plt.title(f"Dự báo vs Thực tế: {province_name}", fontsize=16, fontweight='bold')
        plt.ylabel("Bức xạ (W/m²)", fontsize=12)
        plt.xlabel("Thời gian", fontsize=12)
        plt.grid(True, which='both', linestyle='--', alpha=0.6)

        # Format trục thời gian
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M\n%d/%m'))
        plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=3))

        # Hộp thông tin lỗi
        textstr = f'MAE: {mae:.2f}\nRMSE: {rmse:.2f}'
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        plt.text(0.02, 0.95, textstr, transform=plt.gca().transAxes, fontsize=12,
                 verticalalignment='top', bbox=props)

        plt.legend(fontsize=12, loc='upper right')
        plt.tight_layout()

        # Lưu ảnh
        output_img = GRAPH_DIR / f"comparison_{province_name}.png"
        plt.savefig(output_img, dpi=300)
        plt.close()  # Quan trọng: Đóng plot để giải phóng RAM

        print(f"✅ {province_name}: MAE={mae:.2f}, RMSE={rmse:.2f} -> Đã lưu ảnh.")

        return {
            "Province": province_name,
            "MAE": mae,
            "RMSE": rmse
        }

    except Exception as e:
        print(f"❌ Lỗi xử lý {province_name}: {e}")
        return None


# =========================================
# 3. CHƯƠNG TRÌNH CHÍNH
# =========================================
if __name__ == "__main__":
    # Tìm tất cả file forecast_*.csv
    forecast_files = glob.glob(os.path.join(FORECAST_DIR, "forecast_*.csv"))

    if not forecast_files:
        print("❌ Không tìm thấy file dự báo nào trong folder results_dual_input!")
        exit()

    print(f"🚀 Tìm thấy {len(forecast_files)} file dự báo. Bắt đầu vẽ biểu đồ hàng loạt...\n")

    for f_path in sorted(forecast_files):
        # Lấy tên file (VD: forecast_Ha_Noi.csv -> Ha_Noi)
        filename = os.path.basename(f_path)
        province_name = filename.replace("forecast_", "").replace(".csv", "")

        # Xử lý từng tỉnh
        result = process_one_province(province_name)
        if result:
            summary_metrics.append(result)

    # --- In bảng tổng hợp ---
    print("\n" + "=" * 40)
    print("📊 BẢNG TỔNG HỢP SAI SỐ (Sắp xếp theo RMSE)")
    print("=" * 40)

    if summary_metrics:
        df_summary = pd.DataFrame(summary_metrics)
        # Sắp xếp từ lỗi thấp đến lỗi cao
        df_summary = df_summary.sort_values(by="RMSE")

        # In đẹp
        print(df_summary.to_string(index=False))

        # Lưu bảng tổng hợp ra file CSV luôn
        summary_path = GRAPH_DIR / "summary_metrics.csv"
        df_summary.to_csv(summary_path, index=False)
        print(f"\n✅ Đã lưu bảng tổng hợp tại: {summary_path}")
    else:
        print("Không có dữ liệu tổng hợp.")

    print(f"\n🎉 HOÀN TẤT! Kiểm tra thư mục '{GRAPH_DIR}' để xem ảnh.")