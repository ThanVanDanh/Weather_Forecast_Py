import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path

# =========================
# 1. CẤU HÌNH ĐƯỜNG DẪN
# =========================
BASE_DIR = Path(__file__).resolve().parent

# Đường dẫn đến các file dữ liệu
TRUTH_PATH = BASE_DIR.parent / "data_test" / "An_Giang.csv"
SARIMA_PATH = BASE_DIR / "model_solar_sarima" / "An_Giang.csv"
LSTM_PATH = BASE_DIR / "model_solar_lstm" / "forecast_angiang.csv"


def load_truth_data():
    """Load dữ liệu thực tế (Hourly) và gom lại thành Daily Sum"""
    if not TRUTH_PATH.exists():
        print(f"⚠️ Không tìm thấy file thực tế: {TRUTH_PATH}")
        return None

    df = pd.read_csv(TRUTH_PATH)
    df['time'] = pd.to_datetime(df['time'])

    # Chỉ lấy cột bức xạ
    if 'shortwave_radiation' not in df.columns:
        print("⚠️ File thực tế thiếu cột 'shortwave_radiation'")
        return None

    # Resample theo ngày (Sum)
    df_daily = df.set_index('time').resample('D')['shortwave_radiation'].sum().reset_index()
    df_daily.rename(columns={'shortwave_radiation': 'Thực Tế (Actual)'}, inplace=True)
    return df_daily


def load_sarima_data():
    """Load dữ liệu SARIMA (Đã là Daily)"""
    if not SARIMA_PATH.exists():
        print(f"⚠️ Không tìm thấy file SARIMA: {SARIMA_PATH}")
        return None

    df = pd.read_csv(SARIMA_PATH)
    df.rename(columns={'Date': 'time', 'Solar_Radiation_Wh_m2': 'SARIMA'}, inplace=True)
    df['time'] = pd.to_datetime(df['time'])
    return df[['time', 'SARIMA']]


def load_lstm_data(ref_dates):
    """
    Load dữ liệu LSTM (Hourly Index) và map ngày từ SARIMA.
    """
    if not LSTM_PATH.exists():
        print(f"⚠️ Không tìm thấy file LSTM: {LSTM_PATH}")
        return None

    df = pd.read_csv(LSTM_PATH)

    # Gom nhóm theo ngày (24h = 1 ngày)
    df['day_idx'] = (df['Hour_Index'] - 1) // 24
    df_daily = df.groupby('day_idx')['Predicted_Solar_Radiation'].sum().reset_index()

    # Gán ngày tháng
    if len(df_daily) <= len(ref_dates):
        df_daily['time'] = ref_dates.values[:len(df_daily)]
    else:
        start_date = ref_dates.values[0]
        df_daily['time'] = pd.date_range(start=start_date, periods=len(df_daily))

    df_daily.rename(columns={'Predicted_Solar_Radiation': 'LSTM'}, inplace=True)
    return df_daily[['time', 'LSTM']]


# =========================
# 2. XỬ LÝ CHÍNH
# =========================
def main():
    print("🔄 Đang tải dữ liệu...")

    # 1. Load Data
    df_sarima = load_sarima_data()
    if df_sarima is None:
        print("❌ Thiếu dữ liệu SARIMA.")
        return

    forecast_dates = df_sarima['time']
    df_lstm = load_lstm_data(forecast_dates)
    df_truth = load_truth_data()

    # 2. Merge Data
    df_final = df_sarima.copy()
    if df_lstm is not None:
        df_final = pd.merge(df_final, df_lstm, on='time', how='left')
    if df_truth is not None:
        df_final = pd.merge(df_final, df_truth, on='time', how='left')

    print("\n📊 Dữ liệu tổng hợp (Theo ngày):")
    print(df_final)

    # =========================
    # 3. VẼ BIỂU ĐỒ ĐƯỜNG
    # =========================
    plt.figure(figsize=(12, 6))

    # --- Vẽ đường Thực tế ---
    if 'Thực Tế (Actual)' in df_final.columns and df_final['Thực Tế (Actual)'].notna().any():
        plt.plot(df_final['time'], df_final['Thực Tế (Actual)'],
                 label='Thực Tế', color='gray', linestyle='--', marker='o', linewidth=2)

    # --- Vẽ đường SARIMA ---
    plt.plot(df_final['time'], df_final['SARIMA'],
             label='SARIMA', color='blue', linestyle='-', marker='s', linewidth=2)

    # --- Vẽ đường LSTM ---
    if 'LSTM' in df_final.columns:
        plt.plot(df_final['time'], df_final['LSTM'],
                 label='LSTM', color='orange', linestyle='-', marker='^', linewidth=2)

    # Trang trí biểu đồ
    plt.xlabel('Ngày')
    plt.ylabel('Tổng Bức Xạ (Wh/m²)')
    plt.title('So sánh Bức Xạ Mặt Trời: Thực tế vs SARIMA vs LSTM (Line Chart)')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.6)

    # Format ngày tháng trục X
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator()) # Hiển thị từng ngày

    plt.tight_layout()

    # Lưu và hiển thị
    save_path = BASE_DIR / "bieudo_so_sanh_solar_line.png"
    plt.savefig(save_path)
    print(f"\n✅ Đã lưu biểu đồ tại: {save_path}")
    plt.show()


if __name__ == "__main__":
    main()