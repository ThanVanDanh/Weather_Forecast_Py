import pandas as pd
import matplotlib.pyplot as plt

# =========================
# ĐƯỜNG DẪN FILE CSV
# =========================
truth_path = r"data_test/An_Giang.csv"      # file nhiệt độ thực tế
sarima_path = r"result_demo/An_Giang_Sarima.csv"   # file dự báo SARIMA
lstm_path = r"result_demo/An_Giang_LSTM_v3.csv"       # file dự báo LSTM


# =========================
# LOAD DATA
# =========================
df_truth = pd.read_csv(truth_path)
df_sarima = pd.read_csv(sarima_path)
df_lstm = pd.read_csv(lstm_path)

# Parse time
df_truth["time"] = pd.to_datetime(df_truth["time"])
df_sarima["time"] = pd.to_datetime(df_sarima["time"])
df_lstm["time"] = pd.to_datetime(df_lstm["time"])

# Giả sử mỗi file chỉ có 2 cột: time và giá trị
truth_col = [c for c in df_truth.columns if c != "time"][0]
sarima_col = [c for c in df_sarima.columns if c not in ["time", "lower_95", "upper_95"]][0]
lstm_col = [c for c in df_lstm.columns if c != "time"][0]

df_truth = df_truth.rename(columns={truth_col: "actual"})
df_sarima = df_sarima.rename(columns={sarima_col: "sarima"})
df_lstm = df_lstm.rename(columns={lstm_col: "lstm"})

# =========================
# MERGE THEO TIME
# =========================
df = df_truth.merge(df_sarima[["time", "sarima"]], on="time", how="inner")
df = df.merge(df_lstm[["time", "lstm"]], on="time", how="inner")
df = df.sort_values("time")

print(df.head())

# =========================
# PLOT
# =========================
plt.figure()
plt.plot(df["time"], df["actual"], label="Actual")
plt.plot(df["time"], df["sarima"], label="SARIMA")
plt.plot(df["time"], df["lstm"], label="LSTM")

plt.xlabel("Time")
plt.ylabel("Temperature (°C)")
plt.title("Temperature Forecast: Actual vs SARIMA vs LSTM")
plt.legend()
plt.tight_layout()
plt.show()

# Nếu muốn lưu ảnh:
# plt.savefig("compare_actual_sarima_lstm.png", dpi=150)
