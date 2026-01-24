import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
import glob
from pathlib import Path
from sklearn.metrics import mean_absolute_error, root_mean_squared_error

# --- CẤU HÌNH ---
TARGET_DATE = "2026-01-23"  # Ngày cần so sánh
BASE_DIR = Path(os.getcwd())

# 1. Thư mục dữ liệu Thực tế (Ground Truth)
ACTUAL_DIR = BASE_DIR / "data_test"

# 2. Thư mục kết quả LSTM
FORECAST_LSTM_DIR = BASE_DIR / "results_train_shortwave_radiation_lstm"

# 3. Thư mục kết quả SARIMAX (Cập nhật theo hình ảnh)
FORECAST_SARIMAX_DIR = BASE_DIR / "predictions_sarimax_24h"

# Thư mục lưu biểu đồ
GRAPH_DIR = BASE_DIR / "comparison_charts_3_models"
GRAPH_DIR.mkdir(exist_ok=True)

summary_metrics = []


def process_comparison(province_name, lstm_file_path):
    # --- 1. ĐƯỜNG DẪN FILE ---
    actual_path = ACTUAL_DIR / f"{province_name}.csv"

    # CẬP NHẬT LOGIC TÊN FILE SARIMAX: {Ten_Tinh}_predicted.csv
    sarimax_filename = f"{province_name}_predicted.csv"
    sarimax_path = FORECAST_SARIMAX_DIR / sarimax_filename

    if not actual_path.exists():
        print(f"⚠️ {province_name}: Thiếu file thực tế. Bỏ qua.")
        return None

    try:
        # --- 2. ĐỌC DỮ LIỆU ---

        # A. Thực tế (Ground Truth)
        df_actual = pd.read_csv(actual_path)
        time_col_act = df_actual.columns[0]
        df_actual[time_col_act] = pd.to_datetime(df_actual[time_col_act])

        # B. LSTM
        df_lstm = pd.read_csv(lstm_file_path)
        time_col_lstm = 'Time' if 'Time' in df_lstm.columns else df_lstm.columns[0]
        val_col_lstm = 'Radiation_Forecast'
        df_lstm[time_col_lstm] = pd.to_datetime(df_lstm[time_col_lstm])

        # C. SARIMAX (Đọc cột time và predicted_radiation)
        has_sarimax = False
        df_sarimax = pd.DataFrame()

        # Tên cột trong file SARIMAX theo hình ảnh bạn gửi
        val_col_sarima = 'predicted_radiation'
        time_col_sarima = 'time'

        if sarimax_path.exists():
            df_sarimax = pd.read_csv(sarimax_path)

            # Kiểm tra tên cột
            if time_col_sarima in df_sarimax.columns and val_col_sarima in df_sarimax.columns:
                df_sarimax[time_col_sarima] = pd.to_datetime(df_sarimax[time_col_sarima])
                has_sarimax = True
            else:
                print(f"ℹ️ {province_name}: File SARIMAX tìm thấy nhưng sai tên cột.")
        else:
            print(f"ℹ️ {province_name}: Không tìm thấy file SARIMAX: {sarimax_filename}")

        # --- 3. LỌC NGÀY TARGET ---
        target_date_obj = pd.to_datetime(TARGET_DATE).date()

        # Lọc Actual
        df_actual = df_actual[df_actual[time_col_act].dt.date == target_date_obj].copy()
        df_actual.rename(columns={time_col_act: "Time_Merge", "shortwave_radiation": "Actual"}, inplace=True)

        # Lọc LSTM
        df_lstm = df_lstm[df_lstm[time_col_lstm].dt.date == target_date_obj].copy()
        df_lstm.rename(columns={time_col_lstm: "Time_Merge", val_col_lstm: "LSTM_Pred"}, inplace=True)

        # Lọc SARIMAX
        if has_sarimax:
            df_sarimax = df_sarimax[df_sarimax[time_col_sarima].dt.date == target_date_obj].copy()
            df_sarimax.rename(columns={
                time_col_sarima: "Time_Merge",
                val_col_sarima: "SARIMAX_Pred"
            }, inplace=True)

        # --- 4. MERGE DỮ LIỆU ---
        # Merge Actual & LSTM
        df_merged = pd.merge(df_actual[['Time_Merge', 'Actual']],
                             df_lstm[['Time_Merge', 'LSTM_Pred']],
                             on='Time_Merge', how='inner')

        # Merge SARIMAX nếu có
        if has_sarimax and not df_sarimax.empty:
            df_merged = pd.merge(df_merged,
                                 df_sarimax[['Time_Merge', 'SARIMAX_Pred']],
                                 on='Time_Merge', how='inner')

        if df_merged.empty:
            print(f"⚠️ {province_name}: Không có dữ liệu trùng khớp giờ cho ngày {TARGET_DATE}.")
            return None

        # --- 5. TÍNH TOÁN SAI SỐ ---
        y_true = df_merged['Actual']

        # LSTM Metrics
        lstm_rmse = root_mean_squared_error(y_true, df_merged['LSTM_Pred'])

        # SARIMAX Metrics
        sarimax_rmse = None
        best_model = "LSTM"  # Mặc định

        if has_sarimax:
            sarimax_rmse = root_mean_squared_error(y_true, df_merged['SARIMAX_Pred'])
            if sarimax_rmse < lstm_rmse:
                best_model = "SARIMAX"

        # --- 6. VẼ BIỂU ĐỒ ---
        plt.figure(figsize=(12, 6))

        # Line 1: Thực tế
        plt.plot(df_merged['Time_Merge'], df_merged['Actual'],
                 label='Thực tế', color='#1f77b4', linewidth=2.5, alpha=0.7)

        # Line 2: LSTM
        plt.plot(df_merged['Time_Merge'], df_merged['LSTM_Pred'],
                 label=f'LSTM (RMSE={lstm_rmse:.1f})',
                 color='#d62728', linestyle='--', linewidth=2, marker='o', markersize=4)

        # Line 3: SARIMAX
        if has_sarimax:
            plt.plot(df_merged['Time_Merge'], df_merged['SARIMAX_Pred'],
                     label=f'SARIMAX (RMSE={sarimax_rmse:.1f})',
                     color='#2ca02c', linestyle='-.', linewidth=2, marker='x', markersize=4)

        plt.title(f"So sánh: {province_name} ({TARGET_DATE})", fontsize=14, fontweight='bold')
        plt.ylabel("Bức xạ (W/m²)")
        plt.xlabel("Giờ")
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        plt.legend(loc='upper right')
        plt.tight_layout()

        # Lưu ảnh
        plt.savefig(GRAPH_DIR / f"compare_3models_{province_name}.png", dpi=150)
        plt.close()

        print(f"✅ {province_name}: LSTM={lstm_rmse:.1f} | SARIMAX={sarimax_rmse if sarimax_rmse else 'N/A'}")

        return {
            "Province": province_name,
            "LSTM_RMSE": lstm_rmse,
            "SARIMAX_RMSE": sarimax_rmse if sarimax_rmse else 9999,
            "Best_Model": best_model
        }

    except Exception as e:
        print(f"❌ Lỗi {province_name}: {e}")
        return None


if __name__ == "__main__":
    # Tìm file LSTM để làm mốc (forecast_Ha_Noi_2026-01-23.csv)
    search_pattern = os.path.join(FORECAST_LSTM_DIR, f"forecast_*_{TARGET_DATE}.csv")
    forecast_files = glob.glob(search_pattern)

    if not forecast_files:
        print(f"⛔ Không tìm thấy file LSTM nào cho ngày {TARGET_DATE}.")
        exit()

    print(f"--> Tìm thấy {len(forecast_files)} tỉnh. Đang so sánh...\n")

    for f_path in sorted(forecast_files):
        filename = os.path.basename(f_path)
        # Tách tên tỉnh: forecast_Ha_Noi_2026-01-23.csv -> Ha_Noi
        province_name = filename.replace("forecast_", "").replace(f"_{TARGET_DATE}.csv", "")

        result = process_comparison(province_name, f_path)
        if result:
            summary_metrics.append(result)

    # Tổng kết
    if summary_metrics:
        df_summary = pd.DataFrame(summary_metrics)
        df_summary = df_summary.sort_values(by="Province")

        print("\n" + "=" * 40)
        print("   KẾT QUẢ SO SÁNH (RMSE)")
        print("=" * 40)
        # Chỉ hiển thị cột cần thiết
        print(df_summary[['Province', 'Best_Model', 'LSTM_RMSE', 'SARIMAX_RMSE']].to_string(index=False))

        df_summary.to_csv(GRAPH_DIR / "summary_comparison.csv", index=False)
        print(f"\n📁 Đã lưu kết quả tại: {GRAPH_DIR}")