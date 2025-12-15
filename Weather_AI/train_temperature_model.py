"""
TRAIN SARIMAX – SAVE PARAMS ONLY (FINAL)
=======================================

✔ KHÔNG save SARIMAXResults
✔ KHÔNG file GB
✔ Chỉ save params + metadata
✔ Chuẩn để deploy Django / Web

"""

from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from statsmodels.tsa.statespace.sarimax import SARIMAX


# ==============================
# PATH CONFIG
# ==============================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PARAM_DIR = BASE_DIR / "model_params"
PARAM_DIR.mkdir(exist_ok=True)


# ==============================
# MODEL CONFIG
# ==============================

ORDER = (1, 1, 1)
SEASONAL_ORDER = (1, 1, 1, 24)

VAL_HOURS = 24 * 7

TARGET_COL = "temperature_2m"

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
# LOAD DATA
# ==============================

def load_dataset(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    if "time" not in df.columns:
        raise ValueError(f"{csv_path.name} missing 'time'")

    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").sort_index()
    df = df.asfreq("h")

    df = df.ffill().bfill()

    # chỉ dùng 18 tháng gần nhất
    cutoff = df.index.max() - pd.DateOffset(months=18)
    df = df[df.index >= cutoff]

    return df


# ==============================
# TRAIN ONE PROVINCE
# ==============================

def train_province(province: str, csv_path: Path):
    print(f"\n=== TRAINING {province} ===")

    df = load_dataset(csv_path)

    y = df[TARGET_COL].astype(float)
    exog = df[EXOG_COLS].astype(float)

    if len(df) > VAL_HOURS * 2:
        y_train = y.iloc[:-VAL_HOURS]
        y_val = y.iloc[-VAL_HOURS:]

        exog_train = exog.iloc[:-VAL_HOURS]
        exog_val = exog.iloc[-VAL_HOURS:]
    else:
        y_train = y
        exog_train = exog
        y_val = None
        exog_val = None

    model = SARIMAX(
        y_train,
        exog=exog_train,
        order=ORDER,
        seasonal_order=SEASONAL_ORDER,
        enforce_stationarity=False,
        enforce_invertibility=False,
    )

    results = model.fit(disp=False)
    print(f"[{province}] Fit done | AIC={results.aic:.2f}")

    # validation
    if y_val is not None:
        forecast = results.get_forecast(steps=VAL_HOURS, exog=exog_val)
        y_pred = forecast.predicted_mean.reindex(y_val.index)

        mae = float(np.mean(np.abs(y_val - y_pred)))
        rmse = float(np.sqrt(np.mean((y_val - y_pred) ** 2)))

        print(f"[{province}] MAE={mae:.3f} | RMSE={rmse:.3f}")

    # ==============================
    # SAVE PARAMS ONLY (KEY STEP)
    # ==============================

    payload = {
        "params": results.params,              # vector tham số
        "order": ORDER,
        "seasonal_order": SEASONAL_ORDER,
        "exog_cols": EXOG_COLS,
        "last_timestamp": y_train.index[-1],   # mốc thời gian cuối
    }

    save_path = PARAM_DIR / f"{province}_temp_params.pkl"
    joblib.dump(payload, save_path)

    print(f"[{province}] Params saved → {save_path} ({save_path.stat().st_size / 1024:.1f} KB)")


# ==============================
# TRAIN ALL
# ==============================

def train_all():
    csv_files = sorted(DATA_DIR.glob("*.csv"))
    if not csv_files:
        print("❌ No CSV files found")
        return

    for csv_path in csv_files:
        try:
            train_province(csv_path.stem, csv_path)
        except Exception as e:
            print(f"⚠️ ERROR {csv_path.stem}: {e}")

    print("\n🎉 TRAINING COMPLETED – PARAMS SAVED ONLY")


# ==============================
# MAIN
# ==============================

if __name__ == "__main__":
    print("🚀 TRAIN SARIMAX – SAVE PARAMS ONLY")
    print(f"📁 DATA  : {DATA_DIR}")
    print(f"📁 PARAM : {PARAM_DIR}")

    train_all()
