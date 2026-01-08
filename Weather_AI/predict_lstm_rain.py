# predict_rain_5days.py - Dự báo mưa 5 ngày tới
"""
Output:
- Ngày 1-5: Xác suất mưa (%), Lượng mưa dự kiến (mm)
"""
from pathlib import Path
import pandas as pd
import numpy as np
import joblib
from tensorflow.keras.models import load_model

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models_rain"

LOOKBACK = 30
HORIZON = 5


def load_recent_daily(csv_path: Path):
    """Load 30 ngày gần nhất"""
    df = pd.read_csv(csv_path)
    df["time"] = pd.to_datetime(df["time"], format='mixed')
    df = df.set_index("time").sort_index()

    # Fill missing values
    df = df.fillna(method='ffill').fillna(method='bfill')
    df = df.asfreq("h", method='ffill')

    # Aggregate to daily
    daily = df.resample("D").agg({
        'temperature_2m': ['max', 'min', 'mean'],
        'precipitation': 'sum',
        'weathercode': 'max',
        'relative_humidity_2m': 'mean',
        'surface_pressure': 'mean',
        'cloudcover': 'mean'
    })

    daily.columns = ['temp_max', 'temp_min', 'temp_mean',
                     'precipitation', 'weather_code',
                     'humidity', 'pressure', 'cloudcover']

    daily['has_rain'] = (daily['precipitation'] > 0.1).astype(int)

    return daily.iloc[-LOOKBACK:].astype(float)


def forecast_rain_5days(province: str) -> pd.DataFrame:
    """
    Dự báo mưa 5 ngày tới
    """
    csv_path = DATA_DIR / f"{province}.csv"
    model_path = MODEL_DIR / f"{province}_rain.keras"
    scaler_X_path = MODEL_DIR / f"{province}_rain_scaler_X.pkl"
    scaler_Y_path = MODEL_DIR / f"{province}_rain_scaler_Y.pkl"

    # Check files exist
    if not model_path.exists():
        raise FileNotFoundError(f"Chưa train model cho {province}")

    # Load model và scalers
    model = load_model(model_path, compile=False)
    scaler_X = joblib.load(scaler_X_path)
    scaler_Y = joblib.load(scaler_Y_path)

    # Load data
    daily = load_recent_daily(csv_path)
    last_date = daily.index[-1]

    # Chuẩn bị input
    feature_cols = ['temp_max', 'temp_min', 'temp_mean',
                    'precipitation', 'humidity', 'pressure', 'cloudcover', 'has_rain']

    values = daily[feature_cols].values
    scaled = scaler_X.transform(values)

    # Predict
    X = scaled.reshape(1, LOOKBACK, len(feature_cols))
    pred_scaled = model.predict(X, verbose=0)[0]

    # Reshape và inverse transform
    pred_scaled = pred_scaled.reshape(HORIZON, 2)  # (5, 2) - [precipitation, has_rain]
    pred = scaler_Y.inverse_transform(pred_scaled)

    # Tạo dates
    forecast_dates = pd.date_range(
        start=last_date + pd.Timedelta(days=1),
        periods=HORIZON,
        freq='D'
    )

    # Xử lý kết quả
    precipitations = pred[:, 0]
    has_rains = pred[:, 1]

    # Clip giá trị
    precipitations = np.clip(precipitations, 0, None)  # Không âm
    has_rains = np.clip(has_rains, 0, 1)  # 0-1

    # Tính xác suất mưa (%)
    rain_probabilities = (has_rains * 100).round(0).astype(int)

    # Nếu xác suất thấp, giảm lượng mưa
    for i in range(len(precipitations)):
        if rain_probabilities[i] < 30:
            precipitations[i] *= 0.5
        elif rain_probabilities[i] < 50:
            precipitations[i] *= 0.7

    # Tạo weather description
    descriptions = []
    for prob, precip in zip(rain_probabilities, precipitations):
        if prob < 20:
            desc = "Nắng"
        elif prob < 40:
            desc = "Có thể có mưa nhẹ"
        elif prob < 60:
            desc = "Mưa nhẹ"
        elif prob < 80:
            desc = "Mưa vừa"
        else:
            if precip > 50:
                desc = "Mưa to"
            elif precip > 100:
                desc = "Mưa rất to"
            else:
                desc = "Mưa"
        descriptions.append(desc)

    # Tạo DataFrame kết quả
    result = pd.DataFrame({
        'date': forecast_dates.date,
        'rain_probability': rain_probabilities,
        'precipitation_mm': precipitations.round(1),
        'description': descriptions
    })

    return result


if __name__ == "__main__":
    import sys

    province = sys.argv[1] if len(sys.argv) > 1 else "An_Giang"

    print(f"\n{'=' * 70}")
    print(f"DỰ BÁO MƯA 5 NGÀY TỚI - {province}")
    print(f"{'=' * 70}\n")

    try:
        result = forecast_rain_5days(province)

        print("📅 BẢNG DỰ BÁO:")
        print("-" * 70)
        for _, row in result.iterrows():
            print(f"📆 {row['date']}")
            print(f"   💧 Xác suất mưa: {row['rain_probability']}%")
            print(f"   🌧️  Lượng mưa dự kiến: {row['precipitation_mm']:.1f}mm")
            print(f"   ☁️  {row['description']}")
            print()

        # Lưu file
        output_dir = Path("result_demo")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"result_rain_{province}.csv"
        result.to_csv(output_path, index=False)
        print(f"✅ Đã lưu kết quả: {output_path}")

    except FileNotFoundError as e:
        print(f"❌ {e}")
        print("\n💡 Hãy chạy train_rain_forecast.py trước!")
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback

        traceback.print_exc()