# plot_compare_sarima_lstm.py
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).resolve().parent

# ==== Đường dẫn file ====
truth_path = BASE_DIR / "data_test" / "An_Giang.csv"
sarima_path = BASE_DIR / "result_demo" / "result_hourly_An_Giang.csv"
lstm_path = BASE_DIR / "result_demo" / "result_lstm_hourly_An_Giang.csv"

TARGET_COL = "temperature_2m"          # cột nhiệt độ thực tế
SARIMA_COL = "temp_forecast"    # cột dự báo SARIMA
LSTM_COL = "temperature_forecast"      # cột dự báo LSTM


def main():
    # ==== Load data ====
    df_truth = pd.read_csv(truth_path, parse_dates=["time"])
    df_sarima = pd.read_csv(sarima_path, parse_dates=["time"])
    df_lstm = pd.read_csv(lstm_path, parse_dates=["time"])

    # ==== Chỉ lấy đoạn thời gian forecast để so ====
    start = df_sarima["time"].min()
    end = df_sarima["time"].max()

    df_truth = df_truth[(df_truth["time"] >= start) & (df_truth["time"] <= end)]

    # ==== Merge ====
    df = df_truth.merge(df_sarima[["time", SARIMA_COL]], on="time", how="inner")
    df = df.merge(df_lstm[["time", LSTM_COL]], on="time", how="inner")

    # ==== Plot ====
    plt.figure(figsize=(14, 6))

    plt.plot(df["time"], df[TARGET_COL], label="Thực tế", linewidth=2)
    plt.plot(df["time"], df[SARIMA_COL], label="SARIMA", linestyle="--")
    plt.plot(df["time"], df[LSTM_COL], label="LSTM", linestyle=":")

    plt.title("So sánh dự báo nhiệt độ 24h: Thực tế vs SARIMA vs LSTM")
    plt.xlabel("Thời gian")
    plt.ylabel("Nhiệt độ (°C)")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    # ==== In thêm MAE để so định lượng ====
    mae_sarima = (df[TARGET_COL] - df[SARIMA_COL]).abs().mean()
    mae_lstm = (df[TARGET_COL] - df[LSTM_COL]).abs().mean()

    print(f"MAE SARIMA = {mae_sarima:.3f}")
    print(f"MAE LSTM   = {mae_lstm:.3f}")


if __name__ == "__main__":
    main()
