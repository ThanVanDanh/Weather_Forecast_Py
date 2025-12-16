import matplotlib.pyplot as plt
import pandas as pd
import statsmodels.api as sm
from pathlib import Path

# === CẤU HÌNH TỈNH MUỐN XEM ===
PROVINCE = "An_Giang"

BASE_DIR = Path("Weather_AI")
DATA_PATH = BASE_DIR / "data" / f"{PROVINCE}.csv"
MODEL_PATH = BASE_DIR / "models" / f"{PROVINCE}_radiation_sarimax.pkl"


def show_chart():
    print(f"--- ĐANG KIỂM TRA: {PROVINCE} ---")

    # 1. Kiểm tra file tồn tại
    if not MODEL_PATH.exists():
        print(f"❌ Không tìm thấy model tại: {MODEL_PATH}")
        print("   -> chạy 'python Weather_AI/train_radiation_model.py' chưa?")
        return

    if not DATA_PATH.exists():
        print(f"❌ Không tìm thấy dữ liệu gốc tại: {DATA_PATH}")
        return

    # 2. Load Model
    print("⏳ Đang đọc file model .pkl...")
    model_results = sm.load(str(MODEL_PATH))

    # 3. Load Dữ liệu gốc để so sánh
    print("⏳ Đang đọc dữ liệu gốc...")
    df = pd.read_csv(DATA_PATH)
    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").sort_index()

    # Gộp theo ngày để so khớp
    df_daily = df.resample('D').agg({'shortwave_radiation': 'sum'})

    # 4. Lấy dữ liệu dự báo từ Model
    # fittedvalues là giá trị model "học" được từ quá khứ
    prediction = model_results.fittedvalues

    # Ép kiểu index về datetime nếu cần
    if not isinstance(prediction.index, pd.DatetimeIndex):
        prediction.index = pd.to_datetime(prediction.index)

    # 5. VẼ BIỂU ĐỒ
    print("📈 Đang vẽ biểu đồ...")
    plt.figure(figsize=(12, 6))

    # Vẽ đường Thực tế (Màu xanh dương)
    plt.plot(df_daily.index, df_daily['shortwave_radiation'],
             label='Thực tế (Real Data)', color='blue', alpha=0.5, linewidth=1.5)

    # Vẽ đường AI Dự báo (Màu đỏ đứt đoạn)
    plt.plot(prediction.index, prediction,
             label='AI Dự báo (Model)', color='red', linestyle='--', linewidth=1.5)

    plt.title(f"KIỂM TRA MODEL BỨC XẠ: {PROVINCE}", fontsize=14, fontweight='bold')
    plt.ylabel("Tổng bức xạ ngày (Wh/m²)")
    plt.xlabel("Thời gian")
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    show_chart()