from pathlib import Path
import pandas as pd
import joblib
from statsmodels.tsa.statespace.sarimax import SARIMAX


# PATH CONFIG

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PARAM_DIR = BASE_DIR / "sarima_params"

TARGET = "temperature_2m"


# LOAD HISTORY

def load_recent_history(province: str, hours: int = 24 * 7) -> pd.Series:
    csv_path = DATA_DIR / f"{province}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"No data for {province}")

    df = pd.read_csv(csv_path)
    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").sort_index()
    df = df.asfreq("h")
    df = df.ffill().bfill()

    return df[TARGET].iloc[-hours:].astype(float)


# FORECAST

def forecast_temperature(province: str, steps: int = 120) -> pd.DataFrame:
    param_path = PARAM_DIR / f"{province}_sarima_params.pkl"
    if not param_path.exists():
        raise FileNotFoundError(f"No SARIMA params for {province}")

    payload = joblib.load(param_path)

    y_hist = load_recent_history(province)

    model = SARIMAX(
        y_hist,
        order=payload["order"],
        seasonal_order=payload["seasonal_order"],
        enforce_stationarity=False,
        enforce_invertibility=False,
    )

    results = model.filter(payload["params"])

    forecast = results.get_forecast(steps=steps)

    mean = forecast.predicted_mean
    ci = forecast.conf_int()

    start_time = y_hist.index[-1] + pd.Timedelta(hours=1)
    future_index = pd.date_range(start=start_time, periods=steps, freq="h")

    df_forecast = pd.DataFrame({
        "time": future_index,
        "temperature_forecast": mean.values,
        "lower_95": ci.iloc[:, 0].values,
        "upper_95": ci.iloc[:, 1].values,
    })

    return df_forecast


# TEST

if __name__ == "__main__":
    df = forecast_temperature("An_Giang", steps=120)
    df.to_csv("data_test/An_Giang_Sarima.csv", index=False)
