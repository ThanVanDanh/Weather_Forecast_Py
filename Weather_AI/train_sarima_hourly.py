from pathlib import Path
import pandas as pd
import numpy as np
import joblib
from statsmodels.tsa.statespace.sarimax import SARIMAX

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SAVE_DIR = BASE_DIR / "models_hourly_sarima"
SAVE_DIR.mkdir(exist_ok=True)

TARGET = "temperature_2m"

ORDER = (1, 1, 1)
SEASONAL_ORDER = (1, 1, 1, 24)   # chu kỳ 24h
VAL_HOURS = 24                  # validate 1 ngày


def load_hourly(csv_path: Path) -> pd.Series:
    df = pd.read_csv(csv_path)
    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").sort_index()
    df = df.asfreq("h").ffill().bfill()
    return df[TARGET].astype(float)


def train_one(province: str, csv_path: Path):
    print(f"\n=== TRAIN HOURLY {province} ===")
    y = load_hourly(csv_path)

    train_y = y.iloc[:-VAL_HOURS]
    val_y = y.iloc[-VAL_HOURS:]

    model = SARIMAX(
        train_y,
        order=ORDER,
        seasonal_order=SEASONAL_ORDER,
        enforce_stationarity=False,
        enforce_invertibility=False
    )
    res = model.fit(disp=False)

    forecast = res.get_forecast(steps=VAL_HOURS)
    y_pred = forecast.predicted_mean.reindex(val_y.index)

    mae = np.mean(np.abs(val_y - y_pred))
    rmse = np.sqrt(np.mean((val_y - y_pred) ** 2))

    print(f"[{province}] MAE={mae:.3f} | RMSE={rmse:.3f}")

    payload = {
        "order": ORDER,
        "seasonal_order": SEASONAL_ORDER,
        "params": res.params
    }
    joblib.dump(payload, SAVE_DIR / f"{province}_hourly.pkl")
    print(f"[{province}] Saved → models_hourly_sarima/{province}_hourly.pkl")


def main():
    for csv in DATA_DIR.glob("*.csv"):
        train_one(csv.stem, csv)


if __name__ == "__main__":
    print("🚀 TRAIN SARIMA HOURLY (24h forecast)")
    main()
