import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
import glob
from pathlib import Path
from sklearn.metrics import mean_absolute_error, root_mean_squared_error

BASE_DIR = Path(os.getcwd())
ACTUAL_DIR = BASE_DIR / "data_future"
FORECAST_DIR = BASE_DIR / "results_train_shortwave_radiation_lstm"

GRAPH_DIR = BASE_DIR / "comparison_charts_shortwave_radiation"
GRAPH_DIR.mkdir(exist_ok=True)

summary_metrics = []


def process_one_province(province_name):
    actual_path = ACTUAL_DIR / f"{province_name}.csv"
    forecast_path = FORECAST_DIR / f"forecast_{province_name}.csv"

    if not actual_path.exists():
        print(f"{province_name}: Thiếu file (data_future). Bỏ qua.")
        return None

    if not forecast_path.exists():
        print(f" {province_name}: Thiếu file dự báo. Bỏ qua.")
        return None

    try:
        df_actual_raw = pd.read_csv(actual_path)
        time_col_act = df_actual_raw.columns[0]
        df_actual_raw[time_col_act] = pd.to_datetime(df_actual_raw[time_col_act])

        df_pred = pd.read_csv(forecast_path)
        df_pred['Time'] = pd.to_datetime(df_pred['Time'])

        # đồng bộ thời gian
        start_time = df_pred['Time'].min()
        end_time = df_pred['Time'].max()


        mask = (df_actual_raw[time_col_act] >= start_time) & (df_actual_raw[time_col_act] <= end_time)
        df_actual_filtered = df_actual_raw.loc[mask].copy().reset_index(drop=True)

        if df_actual_filtered.empty:
            print(f"️ {province_name}: Không tìm thấy dữ liệu thực tế trong khoảng {start_time} - {end_time}")
            return None

        min_len = min(len(df_actual_filtered), len(df_pred))
        df_actual_filtered = df_actual_filtered.head(min_len)
        df_pred = df_pred.head(min_len)

        # Tính toán sai số
        y_true = df_actual_filtered['shortwave_radiation']
        y_pred = df_pred['Radiation_Forecast']

        mae = mean_absolute_error(y_true, y_pred)
        rmse = root_mean_squared_error(y_true, y_pred)

        # Vẽ biểu đồ
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
        plt.close()

        print(f" {province_name}: MAE={mae:.2f}, RMSE={rmse:.2f} -> Đã lưu ảnh.")

        return {
            "Province": province_name,
            "MAE": mae,
            "RMSE": rmse
        }

    except Exception as e:
        print(f" Lỗi xử lý {province_name}: {e}")
        return None

if __name__ == "__main__":
    forecast_files = glob.glob(os.path.join(FORECAST_DIR, "forecast_*.csv"))

    if not forecast_files:
        print(" Không tìm thấy file dự báo ")
        exit()

    print(f" Tìm thấy {len(forecast_files)} file dự báo. Bắt đầu vẽ biểu đồ \n")

    for f_path in sorted(forecast_files):
        filename = os.path.basename(f_path)
        province_name = filename.replace("forecast_", "").replace(".csv", "")

        result = process_one_province(province_name)
        if result:
            summary_metrics.append(result)

    if summary_metrics:
        df_summary = pd.DataFrame(summary_metrics)

        df_summary = df_summary.sort_values(by="RMSE")

        print(df_summary.to_string(index=False))

        summary_path = GRAPH_DIR / "summary_metrics.csv"
        df_summary.to_csv(summary_path, index=False)
        print(f"\n Đã lưu bảng tổng hợp tại: {summary_path}")
    else:
        print("Không có dữ liệu tổng hợp.")

    print("\n HOÀN TẤT! ")