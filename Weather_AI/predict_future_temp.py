"""
PREDICT TEMPERATURE FROM SAVED PARAMS
====================================

✔ KHÔNG load SARIMAXResults
✔ KHÔNG file GB
✔ Rebuild model khi forecast
✔ Chuẩn dùng cho Django / Web

Function chính:
    forecast_temperature(province, steps=120)

"""

from pathlib import Path
import pandas as pd
import joblib
from statsmodels.tsa.statespace.sarimax import SARIMAX


# ==============================
# PATH CONFIG
# ==============================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PARAM_DIR = BASE_DIR / "model_params"


# ==============================
# CONFIG
# ==============================

TARGET_COL = "temperature_2m"

# Phải giống file train
EXOG_COLS = [
    "relative_humidity_2m",
    "dewpoint_2m",
    "wind_speed_10m",
    "surface_pressure",
    "precipitation",
    "cloudcover",
    "shortwave_radiation",
]


# ==============================
# UTILS
# ==============================

def normalize_province(name: str) -> str:
    """Chuẩn hóa tên tỉnh"""
    return name.strip().replace(" ", "_")


def load_recent_history(province: str, history_hours: int = 24 * 7) -> pd.DataFrame:
    """
    Load dữ liệu gần nhất để rebuild model state.
    7 ngày là đủ cho Kalman filter ổn định.
    """
    csv_path = DATA_DIR / f"{province}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Không tìm thấy dữ liệu tỉnh {province}")

    df = pd.read_csv(csv_path)
    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").sort_index()
    df = df.asfreq("h")
    df = df.ffill().bfill()

    return df.iloc[-history_hours:]


def build_future_exog(last_row: pd.Series, steps: int) -> pd.DataFrame:
    """
    Persistence assumption:
    giữ nguyên exogenous hiện tại cho tương lai gần
    """
    future = pd.DataFrame(
        {col: [last_row[col]] * steps for col in EXOG_COLS}
    )
    return future


# ==============================
# FORECAST FUNCTION
# ==============================

def forecast_temperature(province: str, steps: int = 120) -> pd.DataFrame:
    province = normalize_province(province)

    param_path = PARAM_DIR / f"{province}_temp_params.pkl"
    if not param_path.exists():
        raise FileNotFoundError(f"Không tìm thấy params cho tỉnh {province}")

    payload = joblib.load(param_path)

    order = payload["order"]
    seasonal_order = payload["seasonal_order"]
    exog_cols = payload["exog_cols"]

    # Load recent history
    history = load_recent_history(province)
    y_hist = history[TARGET_COL].astype(float)
    exog_hist = history[exog_cols].astype(float)

    # Rebuild model
    model = SARIMAX(
        y_hist,
        exog=exog_hist,
        order=order,
        seasonal_order=seasonal_order,
        enforce_stationarity=False,
        enforce_invertibility=False,
    )

    # Restore parameters
    results = model.filter(payload["params"])

    # Future exogenous
    future_exog = build_future_exog(history.iloc[-1], steps)

    # Forecast
    forecast_res = results.get_forecast(steps=steps, exog=future_exog)
    mean_forecast = forecast_res.predicted_mean
    conf_int = forecast_res.conf_int()

    # Build time index
    start_time = history.index[-1] + pd.Timedelta(hours=1)
    future_index = pd.date_range(start=start_time, periods=steps, freq="h")

    df_forecast = pd.DataFrame({
        "time": future_index,
        "temperature_forecast": mean_forecast.values,
        "lower_95": conf_int.iloc[:, 0].values,
        "upper_95": conf_int.iloc[:, 1].values,
    })

    return df_forecast


# ==============================
# TEST
# ==============================

if __name__ == "__main__":
    df = forecast_temperature("Tuyen_Quang", steps=120)
    print(df)
