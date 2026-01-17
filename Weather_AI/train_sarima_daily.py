from pathlib import Path
import pandas as pd
import numpy as np
import joblib
from statsmodels.tsa.statespace.sarimax import SARIMAX

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SAVE_DIR = BASE_DIR / "models_daily_sarima"
SAVE_DIR.mkdir(exist_ok=True)

TARGET = "temperature_2m"

ORDER = (1, 1, 1)
SEASONAL_ORDER = (1, 1, 1, 7)   # chu kỳ tuần
VAL_DAYS = 5                   # validate 5 ngày


def load_daily(csv_path: Path):
    df = pd.read_csv(csv_path)
    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").sort_index()
    df = df.asfreq("h").ffill().bfill()

    daily = df.resample("D")[TARGET].agg(
        temp_min="min",
        temp_max="max",
        temp_mean="mean"
    )
    return daily


def train_target(province: str, series: pd.Series, name: str):
    train_y = series.iloc[:-VAL_DAYS]
    val_y = series.iloc[-VAL_DAYS:]

    model = SARIMAX(
        train_y,
        order=ORDER,
        seasonal_order=SEASONAL_ORDER,
        enforce_stationarity=False,
        enforce_invertibility=False
    )
    res = model.fit(disp=False)

    forecast = res.get_forecast(steps=VAL_DAYS)
    y_pred = forecast.predicted_mean.reindex(val_y.index)

    mae = np.mean(np.abs(val_y - y_pred))
    rmse = np.sqrt(np.mean((val_y - y_pred) ** 2))

    print(f"[{province}-{name}] MAE={mae:.3f} | RMSE={rmse:.3f}")

    payload = {
        "order": ORDER,
        "seasonal_order": SEASONAL_ORDER,
        "params": res.params
    }
    joblib.dump(payload, SAVE_DIR / f"{province}_{name}_daily.pkl")
    print(f"Saved → models_daily_sarima/{province}_{name}_daily.pkl")


def train_one(province: str, csv_path: Path):
    print(f"\n=== TRAIN DAILY {province} ===")
    daily = load_daily(csv_path)

    train_target(province, daily["temp_min"], "min")
    train_target(province, daily["temp_max"], "max")


def main():
    for csv in DATA_DIR.glob("*.csv"):
        train_one(csv.stem, csv)


if __name__ == "__main__":
    print("🚀 TRAIN SARIMA DAILY (5-day min/max forecast)")
    main()
