# compare_with_actual.py - So sánh dự báo với dữ liệu thực
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.metrics import mean_absolute_error, mean_squared_error

# Cấu hình
PROVINCE = "Ca_Mau"  # Thay tên tỉnh ở đây
RESULT_DIR = Path("result_demo")
DATA_TEST_DIR = Path("data_test")

print(f"\n{'=' * 70}")
print(f"SO SÁNH DỰ BÁO VỚI DỮ LIỆU THỰC - {PROVINCE}")
print(f"{'=' * 70}\n")

# ============================================================================
# 1. ĐỌC DỮ LIỆU
# ============================================================================

# Dữ liệu thực
actual = pd.read_csv(DATA_TEST_DIR / f"{PROVINCE}.csv")
actual['time'] = pd.to_datetime(actual['time'])
actual = actual.sort_values('time')

print(f"📅 Dữ liệu thực: {actual['time'].min()} → {actual['time'].max()}")
print(f"   Tổng số: {len(actual)} giờ\n")

# Dự báo SARIMA Daily
sarima_daily = pd.read_csv(RESULT_DIR / f"result_daily_{PROVINCE}.csv")
sarima_daily['date'] = pd.to_datetime(sarima_daily['date'])

# Dự báo LSTM Daily
lstm_daily = pd.read_csv(RESULT_DIR / f"result_lstm_daily_maxmin_{PROVINCE}.csv")
lstm_daily['date'] = pd.to_datetime(lstm_daily['date'])

# Dự báo SARIMA Hourly
sarima_hourly = pd.read_csv(RESULT_DIR / f"result_hourly_{PROVINCE}.csv")
sarima_hourly['time'] = pd.to_datetime(sarima_hourly['time'])

# Dự báo LSTM Hourly
lstm_hourly = pd.read_csv(RESULT_DIR / f"result_lstm_hourly_{PROVINCE}.csv")
lstm_hourly['time'] = pd.to_datetime(lstm_hourly['time'])

# ============================================================================
# 2. SO SÁNH DAILY (MIN/MAX)
# ============================================================================

print("📊 SO SÁNH DAILY (5 NGÀY)")
print("-" * 70)

# Tính min/max thực tế từng ngày
actual['date'] = actual['time'].dt.date
daily_actual = actual.groupby('date')['temperature_2m'].agg(['min', 'max']).reset_index()
daily_actual['date'] = pd.to_datetime(daily_actual['date'])

# Merge với dự báo
daily_compare = daily_actual.merge(
    sarima_daily[['date', 'temp_min_forecast', 'temp_max_forecast']],
    on='date',
    how='inner',
    suffixes=('_actual', '_sarima')
)
daily_compare = daily_compare.merge(
    lstm_daily[['date', 'temp_min_forecast', 'temp_max_forecast']],
    on='date',
    how='inner'
)
daily_compare.columns = ['date', 'min_actual', 'max_actual',
                         'min_sarima', 'max_sarima',
                         'min_lstm', 'max_lstm']

if len(daily_compare) > 0:
    # Tính MAE và RMSE cho SARIMA
    sarima_mae_max = mean_absolute_error(daily_compare['max_actual'], daily_compare['max_sarima'])
    sarima_rmse_max = np.sqrt(mean_squared_error(daily_compare['max_actual'], daily_compare['max_sarima']))
    sarima_mae_min = mean_absolute_error(daily_compare['min_actual'], daily_compare['min_sarima'])
    sarima_rmse_min = np.sqrt(mean_squared_error(daily_compare['min_actual'], daily_compare['min_sarima']))

    # Tính MAE và RMSE cho LSTM
    lstm_mae_max = mean_absolute_error(daily_compare['max_actual'], daily_compare['max_lstm'])
    lstm_rmse_max = np.sqrt(mean_squared_error(daily_compare['max_actual'], daily_compare['max_lstm']))
    lstm_mae_min = mean_absolute_error(daily_compare['min_actual'], daily_compare['min_lstm'])
    lstm_rmse_min = np.sqrt(mean_squared_error(daily_compare['min_actual'], daily_compare['min_lstm']))

    print("🔴 TEMP MAX:")
    print(f"   SARIMA: MAE={sarima_mae_max:.2f}°C, RMSE={sarima_rmse_max:.2f}°C")
    print(f"   LSTM:   MAE={lstm_mae_max:.2f}°C, RMSE={lstm_rmse_max:.2f}°C")

    print("\n🔵 TEMP MIN:")
    print(f"   SARIMA: MAE={sarima_mae_min:.2f}°C, RMSE={sarima_rmse_min:.2f}°C")
    print(f"   LSTM:   MAE={lstm_mae_min:.2f}°C, RMSE={lstm_rmse_min:.2f}°C")

    print("\n📋 BẢNG CHI TIẾT:")
    print(daily_compare.to_string(index=False))
else:
    print("⚠️  Không có ngày trùng khớp giữa dự báo và dữ liệu thực")

# ============================================================================
# 3. SO SÁNH HOURLY
# ============================================================================

print(f"\n{'=' * 70}")
print("⏰ SO SÁNH HOURLY (24 GIỜ)")
print("-" * 70)

# Merge với dữ liệu thực
hourly_compare = actual[['time', 'temperature_2m']].merge(
    sarima_hourly[['time', 'temp_forecast']],
    on='time',
    how='inner'
)
hourly_compare = hourly_compare.merge(
    lstm_hourly[['time', 'temp_forecast']],
    on='time',
    how='inner'
)
hourly_compare.columns = ['time', 'actual', 'sarima', 'lstm']

if len(hourly_compare) > 0:
    # Tính MAE và RMSE
    sarima_mae = mean_absolute_error(hourly_compare['actual'], hourly_compare['sarima'])
    sarima_rmse = np.sqrt(mean_squared_error(hourly_compare['actual'], hourly_compare['sarima']))

    lstm_mae = mean_absolute_error(hourly_compare['actual'], hourly_compare['lstm'])
    lstm_rmse = np.sqrt(mean_squared_error(hourly_compare['actual'], hourly_compare['lstm']))

    print(f"SARIMA: MAE={sarima_mae:.2f}°C, RMSE={sarima_rmse:.2f}°C")
    print(f"LSTM:   MAE={lstm_mae:.2f}°C, RMSE={lstm_rmse:.2f}°C")

    print(f"\n📋 BẢNG CHI TIẾT ({len(hourly_compare)} giờ trùng khớp):")
    print(hourly_compare.head(10).to_string(index=False))
    if len(hourly_compare) > 10:
        print("...")
else:
    print("⚠️  Không có giờ trùng khớp giữa dự báo và dữ liệu thực")

# ============================================================================
# 4. VẼ BIỂU ĐỒ
# ============================================================================

fig = plt.figure(figsize=(16, 10))

# === BIỂU ĐỒ 1: DAILY MAX ===
ax1 = plt.subplot(2, 2, 1)
if len(daily_compare) > 0:
    ax1.plot(daily_compare['date'], daily_compare['max_actual'],
             marker='o', label='Thực tế', linewidth=3, markersize=10, color='black')
    ax1.plot(daily_compare['date'], daily_compare['max_sarima'],
             marker='s', label='SARIMA', linewidth=2, markersize=8, color='red', linestyle='--')
    ax1.plot(daily_compare['date'], daily_compare['max_lstm'],
             marker='^', label='LSTM', linewidth=2, markersize=8, color='blue', linestyle='--')
    ax1.set_title(f'TEMP MAX (Daily)\nSARIMA: MAE={sarima_mae_max:.2f}°C | LSTM: MAE={lstm_mae_max:.2f}°C',
                  fontweight='bold')
ax1.set_ylabel('Nhiệt độ (°C)')
ax1.legend()
ax1.grid(True, alpha=0.3)
ax1.tick_params(axis='x', rotation=45)

# === BIỂU ĐỒ 2: DAILY MIN ===
ax2 = plt.subplot(2, 2, 2)
if len(daily_compare) > 0:
    ax2.plot(daily_compare['date'], daily_compare['min_actual'],
             marker='o', label='Thực tế', linewidth=3, markersize=10, color='black')
    ax2.plot(daily_compare['date'], daily_compare['min_sarima'],
             marker='s', label='SARIMA', linewidth=2, markersize=8, color='red', linestyle='--')
    ax2.plot(daily_compare['date'], daily_compare['min_lstm'],
             marker='^', label='LSTM', linewidth=2, markersize=8, color='blue', linestyle='--')
    ax2.set_title(f'TEMP MIN (Daily)\nSARIMA: MAE={sarima_mae_min:.2f}°C | LSTM: MAE={lstm_mae_min:.2f}°C',
                  fontweight='bold')
ax2.set_ylabel('Nhiệt độ (°C)')
ax2.legend()
ax2.grid(True, alpha=0.3)
ax2.tick_params(axis='x', rotation=45)

# === BIỂU ĐỒ 3: HOURLY ===
ax3 = plt.subplot(2, 1, 2)
if len(hourly_compare) > 0:
    ax3.plot(hourly_compare['time'], hourly_compare['actual'],
             marker='o', label='Thực tế', linewidth=3, markersize=6, color='black')
    ax3.plot(hourly_compare['time'], hourly_compare['sarima'],
             marker='s', label='SARIMA', linewidth=2, markersize=4, color='red', linestyle='--')
    ax3.plot(hourly_compare['time'], hourly_compare['lstm'],
             marker='^', label='LSTM', linewidth=2, markersize=4, color='blue', linestyle='--')
    ax3.set_title(f'TEMP HOURLY\nSARIMA: MAE={sarima_mae:.2f}°C | LSTM: MAE={lstm_mae:.2f}°C',
                  fontweight='bold')
ax3.set_xlabel('Thời gian')
ax3.set_ylabel('Nhiệt độ (°C)')
ax3.legend()
ax3.grid(True, alpha=0.3)
ax3.tick_params(axis='x', rotation=45)

plt.suptitle(f'SO SÁNH DỰ BÁO VỚI DỮ LIỆU THỰC - {PROVINCE}',
             fontsize=16, fontweight='bold', y=0.995)
plt.tight_layout()

# Lưu biểu đồ
output_dir = Path("comparison_results")
output_dir.mkdir(exist_ok=True)
save_path = output_dir / f"compare_actual_{PROVINCE}.png"
plt.savefig(save_path, dpi=300, bbox_inches='tight')
print(f"\n✅ Đã lưu biểu đồ: {save_path}")

# Lưu dữ liệu
if len(daily_compare) > 0:
    daily_compare.to_csv(output_dir / f"compare_actual_daily_{PROVINCE}.csv", index=False)
    print(f"✅ Đã lưu dữ liệu daily: compare_actual_daily_{PROVINCE}.csv")

if len(hourly_compare) > 0:
    hourly_compare.to_csv(output_dir / f"compare_actual_hourly_{PROVINCE}.csv", index=False)
    print(f"✅ Đã lưu dữ liệu hourly: compare_actual_hourly_{PROVINCE}.csv")

print(f"\n{'=' * 70}\n")
plt.show()