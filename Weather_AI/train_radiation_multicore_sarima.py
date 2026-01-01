import pandas as pd
import numpy as np
from pathlib import Path
from statsmodels.tsa.statespace.sarimax import SARIMAX
import warnings
import time
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import ProcessPoolExecutor, as_completed
import os
import multiprocessing

warnings.filterwarnings("ignore")

# ================== CẤU HÌNH HỆ THỐNG ==================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "model_solar_sarima_full"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

TARGET_COL = "shortwave_radiation"

# Cấu hình SARIMA "Hạng nặng" (High Accuracy)
# Tăng order lên để mô hình phức tạp hơn, học kỹ hơn
ORDER = (3, 0, 3)  # Tăng từ (2,0,2) lên (3,0,3) để bắt sóng tốt hơn
SEASONAL_ORDER = (1, 0, 1, 24)  # Chu kỳ ngày

# Cấu hình Fourier (Quan trọng khi không có biến thời tiết)
# K = số cặp sin/cos. Số càng lớn thì đường cong càng uốn lượn chi tiết.
FOURIER_K_DAY = 2  # Chu kỳ ngày (đủ để vẽ hình quả chuông)
FOURIER_K_YEAR = 5  # Tăng lên 5 để bắt kỹ sự thay đổi mùa trong 3 năm


def add_fourier_terms(df, time_col_name='time'):
    """Tạo bộ biến Fourier phức tạp hơn để bù đắp việc thiếu biến thời tiết"""
    df_exog = df.copy()
    if time_col_name in df_exog.columns:
        times = df_exog[time_col_name]
    else:
        times = df_exog.index

    # 1. Chu kỳ Ngày (24h)
    for k in range(1, FOURIER_K_DAY + 1):
        df_exog[f'sin_day_{k}'] = np.sin(2 * np.pi * k * times.hour / 24)
        df_exog[f'cos_day_{k}'] = np.cos(2 * np.pi * k * times.hour / 24)

    # 2. Chu kỳ Năm (365.25 ngày) - Quan trọng vì có 3 năm dữ liệu
    day_of_year = times.dayofyear
    for k in range(1, FOURIER_K_YEAR + 1):
        df_exog[f'sin_year_{k}'] = np.sin(2 * np.pi * k * day_of_year / 365.25)
        df_exog[f'cos_year_{k}'] = np.cos(2 * np.pi * k * day_of_year / 365.25)

    # Chỉ giữ lại các cột Fourier
    fourier_cols = [c for c in df_exog.columns if 'sin_' in c or 'cos_' in c]
    return df_exog[fourier_cols]


def load_and_prep_data(csv_path: Path):
    df = pd.read_csv(csv_path)
    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").sort_index()

    # Resample 1H và Interpolate
    df_hourly = df[[TARGET_COL]].resample('h').mean().interpolate(method='linear')
    df_hourly[df_hourly < 0] = 0

    # Tạo Exog
    exog = add_fourier_terms(df_hourly, time_col_name=None)

    # Đảm bảo index khớp nhau
    common_idx = df_hourly.index.intersection(exog.index)
    return df_hourly.loc[common_idx], exog.loc[common_idx]


def train_one_province(csv_file):
    """
    Hàm train phiên bản 'Robust' (Chống lỗi):
    - Tự động đổi thuật toán nếu thuật toán đầu tiên thất bại.
    - Kiểm tra kỹ biến results trước khi truy cập.
    """
    start_time = time.time()
    province_name = csv_file.stem

    try:
        # 1. Load Data
        df, exog = load_and_prep_data(csv_file)
        y_train = df[TARGET_COL]
        X_train = exog

        # QUAN TRỌNG: Cộng nhiễu nhỏ để phá vỡ chuỗi số 0 tuyệt đối
        y_train = y_train + 0.001

        # 2. Định nghĩa Model
        # initialization='approximate_diffuse': Giúp tránh lỗi ma trận ngay từ bước đầu
        model = SARIMAX(
            endog=y_train,
            exog=X_train,
            order=ORDER,
            seasonal_order=SEASONAL_ORDER,
            enforce_stationarity=False,
            enforce_invertibility=False,
            initialization='approximate_diffuse'
        )

        # 3. Fit Model (Cơ chế 2 lớp)
        results = None
        method_used = "lbfgs"

        try:
            # Lần 1: Thử lbfgs (Nhanh, chuẩn)
            results = model.fit(disp=False, method='lbfgs', maxiter=200)
        except:
            # Lần 2: Nếu lỗi, dùng Nelder-Mead (Chậm nhưng lỳ đòn, ít lỗi ma trận)
            try:
                method_used = "nm"
                results = model.fit(disp=False, method='nm', maxiter=500)
            except Exception as e:
                return f"❌ [{province_name}] Thất bại cả 2 thuật toán. Lỗi cuối: {str(e)}"

        # 4. Kiểm tra tính hợp lệ của kết quả
        # Đây là đoạn chặn lỗi 'NoneType object has no attribute llf'
        if results is None:
            return f"❌ [{province_name}] Kết quả là None."

        # Kiểm tra xem Log-likelihood có tồn tại không (dấu hiệu model bị gãy)
        if hasattr(results, 'llf') and results.llf is None:
            return f"⚠️ [{province_name}] Fit xong nhưng không tính được LLF (Ma trận suy biến)."

        # Nếu model quá tệ (AIC là NaN), cũng bỏ qua
        if np.isnan(results.aic):
            return f"⚠️ [{province_name}] Fit xong nhưng AIC là NaN."

        # 5. Lưu Model
        save_path = MODELS_DIR / f"{province_name}_sarimax_full.pkl"
        results.save(save_path, remove_data=True)

        duration = time.time() - start_time
        return f"✅ [{province_name}] Xong ({method_used}): {duration / 60:.1f}p | AIC: {results.aic:.0f}"

    except Exception as e:
        # Bắt mọi lỗi còn sót lại để không dừng luồng
        return f"❌ [{province_name}] Lỗi hệ thống: {str(e)}"


def main_multicore():
    # Lấy danh sách tất cả file csv trong folder data
    csv_files = list(DATA_DIR.glob("*.csv"))
    total_files = len(csv_files)

    if not csv_files:
        print("Không tìm thấy file .csv nào trong thư mục data!")
        return

    # Số lượng CPU core có thể dùng (chừa 1 core cho OS)
    max_workers = max(1, os.cpu_count() - 1)

    print(f"=== BẮT ĐẦU TRAINING ĐA LUỒNG (Sử dụng {max_workers} nhân CPU) ===")
    print(f"Tổng số tỉnh cần train: {total_files}")
    print(f"Order cấu hình: {ORDER}")
    print("-" * 50)

    # Kích hoạt ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # 1. Gửi (Submit) tất cả các job vào pool
        # Tạo một từ điển để lưu vết: {future: tên_file}
        future_to_file = {executor.submit(train_one_province, f): f for f in csv_files}

        print(f"🚀 Đã gửi {total_files} task vào hàng đợi xử lý...")

        # 2. Xử lý kết quả ngay khi có task hoàn thành (as_completed)
        # enumerate giúp đếm số thứ tự: 1, 2, 3...
        for i, future in enumerate(as_completed(future_to_file), 1):
            try:
                # Lấy kết quả trả về từ hàm train_one_province
                result = future.result()

                # In ra màn hình ngay lập tức (flush=True để không bị delay)
                print(f"[{i}/{total_files}] {result}", flush=True)

            except Exception as exc:
                # Trường hợp lỗi quá nặng mà hàm train chưa bắt được
                file_name = future_to_file[future].stem
                print(f"[{i}/{total_files}] ❌ [{file_name}] Lỗi nghiêm trọng (Exception): {exc}", flush=True)

    print("-" * 50)
    print("=== TỔNG KẾT: ĐÃ HOÀN THÀNH TOÀN BỘ ===")


if __name__ == "__main__":
    # Windows cần cái này để chạy multiprocessing an toàn
    multiprocessing.freeze_support()
    main_multicore()