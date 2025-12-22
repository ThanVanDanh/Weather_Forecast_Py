from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from statsmodels.tsa.statespace.sarimax import SARIMAX


# PATH CONFIG

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PARAM_DIR = BASE_DIR / "sarima_params"
PARAM_DIR.mkdir(exist_ok=True)


# MODEL CONFIG

ORDER = (1, 1, 1)
SEASONAL_ORDER = (1, 1, 1, 24)

VAL_HOURS = 24 * 7
TARGET = "temperature_2m"


# LOAD DATA

def load_dataset(csv_path: Path) -> pd.Series:
    df = pd.read_csv(csv_path)

    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").sort_index()
    df = df.asfreq("h")

    df = df.ffill().bfill()

    # dùng 18 tháng gần nhất
    cutoff = df.index.max() - pd.DateOffset(months=18)
    df = df[df.index >= cutoff]

    return df[TARGET].astype(float)


# TRAIN ONE PROVINCE

def train_province(province: str, csv_path: Path):
    print(f"\n=== TRAIN {province} ===")

    y = load_dataset(csv_path)

    if len(y) > VAL_HOURS * 2:
        y_train = y.iloc[:-VAL_HOURS]
        y_val = y.iloc[-VAL_HOURS:]
    else:
        y_train = y
        y_val = None

    model = SARIMAX(
        y_train,
        order=ORDER,
        seasonal_order=SEASONAL_ORDER,
        enforce_stationarity=False,
        enforce_invertibility=False,
    )

    results = model.fit(disp=False)
    print(f"[{province}] Fit done | AIC={results.aic:.2f}")

    if y_val is not None:
        forecast = results.get_forecast(steps=VAL_HOURS)
        y_pred = forecast.predicted_mean.reindex(y_val.index)

        mae = float(np.mean(np.abs(y_val - y_pred)))
        rmse = float(np.sqrt(np.mean((y_val - y_pred) ** 2)))

        print(f"[{province}] MAE={mae:.3f} | RMSE={rmse:.3f}")

    # SAVE PARAMS ONLY
    payload = {
        "params": results.params,
        "order": ORDER,
        "seasonal_order": SEASONAL_ORDER,
        "last_timestamp": y_train.index[-1],
    }

    save_path = PARAM_DIR / f"{province}_sarima_params.pkl"
    joblib.dump(payload, save_path)

    print(f"[{province}] Params saved → {save_path}")


# TRAIN ALL

def train_all():
    for csv_path in sorted(DATA_DIR.glob("*.csv")):
        try:
            train_province(csv_path.stem, csv_path)
        except Exception as e:
            print(f"⚠️ ERROR {csv_path.stem}: {e}")

    print("\n🎉 SARIMA TRAINING COMPLETED")


# MAIN

if __name__ == "__main__":
    print("🚀 TRAIN SARIMA – TEMPERATURE ONLY")
    train_all()
