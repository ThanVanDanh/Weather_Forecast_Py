import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path

# =========================
# 1. CẤU HÌNH ĐƯỜNG DẪN
# =========================
BASE_DIR = Path(__file__).resolve().parent

# Cập nhật đường dẫn đến các file kết quả
# LƯU Ý: Đảm bảo tên file và thư mục đúng với máy của bạn
TRUTH_PATH = BASE_DIR.parent / "data_test" / "An_Giang.csv"
SARIMA_PATH = BASE_DIR / "model_solar_sarima" / "An_Giang.csv"
LSTM_STD_PATH = BASE_DIR / "model_solar_lstm" / "forecast_angiang.csv"
LSTM_CS_PATH = BASE_DIR / "model_solar_clearsky" / "forecast_clearsky_angiang.csv"


def normalize_time_col(df, col_name='time'):
    """
    Hàm chuẩn hóa cột thời gian:
    1. Chuyển về datetime.
    2. Nếu có múi giờ (UTC+7...), loại bỏ múi giờ để về dạng Naive (giữ nguyên giờ đồng hồ).
    """
    if col_name not in df.columns:
        return df

    df[col_name] = pd.to_datetime(df[col_name])

    # Kiểm tra xem cột có thông tin múi giờ không
    if df[col_name].dt.tz is not None:
        # Chuyển về giờ địa phương rồi bỏ nhãn timezone
        # (Giả sử dữ liệu đã là giờ VN hoặc UTC+7)
        df[col_name] = df[col_name].dt.tz_convert('Asia/Bangkok').dt.tz_localize(None)

    return df


def load_truth_data():
    """Load dữ liệu thực tế (Hourly) -> Daily Sum"""
    if not TRUTH_PATH.exists():
        print(f"⚠️ Không tìm thấy file thực tế: {TRUTH_PATH}")
        return None

    try:
        df = pd.read_csv(TRUTH_PATH)
        df = normalize_time_col(df, 'time')  # Chuẩn hóa thời gian ngay

        col = 'shortwave_radiation'
        if col not in df.columns:
            return None

        # Resample theo ngày (Sum)
        df_daily = df.set_index('time')[col].resample('D').sum().reset_index()
        df_daily.rename(columns={col: 'Thực Tế (Actual)'}, inplace=True)
        return df_daily
    except Exception as e:
        print(f"❌ Lỗi load Truth: {e}")
        return None


def load_sarima_data():
    """Load dữ liệu SARIMA (Đã là Daily)"""
    if not SARIMA_PATH.exists():
        print(f"⚠️ Không tìm thấy file SARIMA: {SARIMA_PATH}")
        return None

    try:
        df = pd.read_csv(SARIMA_PATH)
        df.rename(columns={'Date': 'time', 'Solar_Radiation_Wh_m2': 'SARIMA'}, inplace=True)
        df = normalize_time_col(df, 'time')  # Chuẩn hóa thời gian ngay

        return df[['time', 'SARIMA']]
    except Exception as e:
        print(f"❌ Lỗi load SARIMA: {e}")
        return None


def load_lstm_clearsky_data():
    """Load dữ liệu LSTM ClearSky"""
    if not LSTM_CS_PATH.exists():
        print(f"⚠️ Không tìm thấy file LSTM ClearSky: {LSTM_CS_PATH}")
        return None

    try:
        df = pd.read_csv(LSTM_CS_PATH)
        df = normalize_time_col(df, 'time')  # <--- QUAN TRỌNG: Loại bỏ UTC+7 ở đây

        if 'Predicted_Radiation' not in df.columns:
            return None

        # Resample Daily Sum
        df_daily = df.set_index('time')['Predicted_Radiation'].resample('D').sum().reset_index()
        df_daily.rename(columns={'Predicted_Radiation': 'LSTM ClearSky'}, inplace=True)
        return df_daily
    except Exception as e:
        print(f"❌ Lỗi load LSTM ClearSky: {e}")
        return None


def load_lstm_std_data(ref_dates):
    """Load LSTM Thường (Hourly Index)"""
    if not LSTM_STD_PATH.exists():
        print(f"⚠️ Không tìm thấy file LSTM thường: {LSTM_STD_PATH}")
        return None

    try:
        df = pd.read_csv(LSTM_STD_PATH)

        # Gom nhóm theo ngày
        # Giả sử Hour_Index bắt đầu từ 1. (Index-1)//24 sẽ nhóm 1-24 thành ngày 0.
        df['day_idx'] = (df['Hour_Index'] - 1) // 24
        df_daily = df.groupby('day_idx')['Predicted_Solar_Radiation'].sum().reset_index()

        # Gán ngày tháng dựa trên dữ liệu tham chiếu (đã normalize)
        if len(ref_dates) > 0:
            start_date = ref_dates.min()
            # Tạo range ngày mới, đảm bảo cũng Naive (do start_date đã Naive)
            df_daily['time'] = pd.date_range(start=start_date, periods=len(df_daily))
        else:
            print("⚠️ Không có ngày tham chiếu cho LSTM thường.")
            return None

        df_daily.rename(columns={'Predicted_Solar_Radiation': 'LSTM Thường'}, inplace=True)
        return df_daily[['time', 'LSTM Thường']]
    except Exception as e:
        print(f"❌ Lỗi load LSTM Std: {e}")
        return None


# =========================
# 2. XỬ LÝ CHÍNH
# =========================
def main():
    print("🔄 Đang tải và tổng hợp dữ liệu...")

    # 1. Load các nguồn có ngày tháng chuẩn trước
    df_sarima = load_sarima_data()
    df_clearsky = load_lstm_clearsky_data()
    df_truth = load_truth_data()

    # Tạo khung thời gian tham chiếu
    ref_dates = pd.Series(dtype='datetime64[ns]')
    if df_clearsky is not None and not df_clearsky.empty:
        ref_dates = df_clearsky['time']
    elif df_sarima is not None and not df_sarima.empty:
        ref_dates = df_sarima['time']

    # 2. Load LSTM thường (cần mượn ngày)
    df_lstm_std = load_lstm_std_data(ref_dates)

    # 3. Merge Data
    dfs = [d for d in [df_truth, df_sarima, df_lstm_std, df_clearsky] if d is not None]

    if not dfs:
        print("❌ Không có dữ liệu nào để vẽ.")
        return

    df_final = dfs[0]
    for df in dfs[1:]:
        # Bây giờ tất cả cột 'time' đều là Naive datetime, merge sẽ không lỗi
        df_final = pd.merge(df_final, df, on='time', how='outer')

    df_final.sort_values('time', inplace=True)

    # Lọc bỏ ngày không có dự báo
    cols_check = [c for c in ['SARIMA', 'LSTM Thường', 'LSTM ClearSky'] if c in df_final.columns]
    if cols_check:
        df_final = df_final.dropna(subset=cols_check, how='all')

    print("\n📊 BẢNG DỮ LIỆU TỔNG HỢP (DAILY SUM - Wh/m²):")
    print(df_final.round(0))

    # =========================
    # 3. VẼ BIỂU ĐỒ ĐƯỜNG
    # =========================
    plt.figure(figsize=(12, 6))

    if 'Thực Tế (Actual)' in df_final.columns:
        plt.plot(df_final['time'], df_final['Thực Tế (Actual)'],
                 label='Thực Tế', color='gray', linestyle='--', marker='o', linewidth=2.5, alpha=0.7)

    if 'SARIMA' in df_final.columns:
        plt.plot(df_final['time'], df_final['SARIMA'],
                 label='SARIMA', color='blue', linestyle='-', marker='s', linewidth=2)

    if 'LSTM Thường' in df_final.columns:
        plt.plot(df_final['time'], df_final['LSTM Thường'],
                 label='LSTM Thường', color='orange', linestyle='-.', marker='x', linewidth=2)

    if 'LSTM ClearSky' in df_final.columns:
        plt.plot(df_final['time'], df_final['LSTM ClearSky'],
                 label='LSTM ClearSky (Đề xuất)', color='red', linestyle='-', marker='*', linewidth=3, markersize=10)

    plt.xlabel('Ngày')
    plt.ylabel('Tổng Bức Xạ Ngày (Wh/m²)')
    plt.title('So sánh Hiệu quả Dự báo: Thực tế vs SARIMA vs LSTM vs ClearSky')
    plt.legend(loc='best', shadow=True)
    plt.grid(True, linestyle='--', alpha=0.6)

    # Format ngày
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator())
    plt.xticks(rotation=0)

    plt.tight_layout()

    save_path = BASE_DIR / "bieudo_so_sanh_full_models.png"
    plt.savefig(save_path)
    print(f"\n✅ Đã lưu biểu đồ tại: {save_path}")
    plt.show()


if __name__ == "__main__":
    main()