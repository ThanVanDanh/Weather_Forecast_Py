# predict_hourly_24h.py
from pathlib import Path
import pandas as pd
import joblib
from statsmodels.tsa.statespace.sarimax import SARIMAX

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models_hourly_sarima"

TARGET = "temperature_2m"


def load_recent_hourly(province: str, hours: int = 24 * 3) -> pd.Series:
    """
    Lấy vài ngày gần nhất để làm history cho filter.
    """
    csv_path = DATA_DIR / f"{province}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"No data for {province}")

    df = pd.read_csv(csv_path)
    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").sort_index()
    df = df.asfreq("h").ffill().bfill()

    return df[TARGET].iloc[-hours:].astype(float)


def forecast_hourly_24h(province: str) -> pd.DataFrame:
    model_path = MODEL_DIR / f"{province}_hourly.pkl"
    if not model_path.exists():
        raise FileNotFoundError(f"No hourly model for {province}")

    payload = joblib.load(model_path)

    y_hist = load_recent_hourly(province)

    model = SARIMAX(
        y_hist,
        order=payload["order"],
        seasonal_order=payload["seasonal_order"],
        enforce_stationarity=False,
        enforce_invertibility=False
    )

    results = model.filter(payload["params"])

    steps = 24
    forecast = results.get_forecast(steps=steps)

    mean = forecast.predicted_mean
    ci = forecast.conf_int()

    start = y_hist.index[-1] + pd.Timedelta(hours=1)
    idx = pd.date_range(start=start, periods=steps, freq="h")

    return pd.DataFrame({
        "time": idx,
        "temp_forecast": mean.values,
        "lower_95": ci.iloc[:, 0].values,
        "upper_95": ci.iloc[:, 1].values
    })


if __name__ == "__main__":
    df = forecast_hourly_24h("Ca_Mau")
    df.to_csv("result_demo/result_hourly_Ca_Mau.csv", index=False)
    print(df.head())
