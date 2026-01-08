from pathlib import Path
import pandas as pd
import joblib
from statsmodels.tsa.statespace.sarimax import SARIMAX

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models_daily_sarima"

TARGET = "temperature_2m"


def load_recent_daily(province: str, days: int = 30) -> pd.DataFrame:
    csv_path = DATA_DIR / f"{province}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"No data for {province}")

    df = pd.read_csv(csv_path)
    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").sort_index()
    df = df.asfreq("h").ffill().bfill()

    daily = df.resample("D")[TARGET].agg(
        temp_min="min",
        temp_max="max",
        temp_mean="mean"
    )

    return daily.iloc[-days:]


def forecast_one_target(province: str, target: str, history: pd.Series, steps: int = 5):
    model_path = MODEL_DIR / f"{province}_{target}_daily.pkl"
    if not model_path.exists():
        raise FileNotFoundError(f"No daily model {target} for {province}")

    payload = joblib.load(model_path)

    model = SARIMAX(
        history,
        order=payload["order"],
        seasonal_order=payload["seasonal_order"],
        enforce_stationarity=False,
        enforce_invertibility=False
    )

    results = model.filter(payload["params"])

    fc = results.get_forecast(steps=steps)
    return fc.predicted_mean


def forecast_daily_minmax_5days(province: str) -> pd.DataFrame:
    daily = load_recent_daily(province)

    min_pred = forecast_one_target(province, "min", daily["temp_min"])
    max_pred = forecast_one_target(province, "max", daily["temp_max"])

    start = daily.index[-1] + pd.Timedelta(days=1)
    idx = pd.date_range(start=start, periods=5, freq="D")

    return pd.DataFrame({
        "date": idx.date,
        "temp_min_forecast": min_pred.values,
        "temp_max_forecast": max_pred.values
    })


if __name__ == "__main__":
    df = forecast_daily_minmax_5days("Ca_Mau")
    df.to_csv("result_demo/result_daily_Ca_Mau.csv", index=False)
    print(df)
