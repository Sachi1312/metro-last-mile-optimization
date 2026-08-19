# ============================================================
# baseline_forecast.py
# Layer 3 baseline — Seasonal-naive forecast ("same day last week")
# Uses the pre-engineered lag_7d column as the prediction, evaluated
# on the exact same chronological 80/20 test split as
# Scripts/layer3_forecasting.py, so its MAPE is directly comparable
# to the XGBoost (2.64%) and Prophet (~5.41%) results.
# Input  : Data/Derived/13_forecasting_features.csv
# Output : Outputs/Results/baseline_naive_forecast.csv
# ============================================================

import pandas as pd
import numpy as np
import os
import warnings
warnings.filterwarnings("ignore")

BASE    = r"C:\Users\parek\Downloads\LY Project"
DER     = os.path.join(BASE, "Data", "Derived")
RESULTS = os.path.join(BASE, "Outputs", "Results")
os.makedirs(RESULTS, exist_ok=True)

print("=" * 55)
print("  BASELINE — SEASONAL-NAIVE FORECAST (Layer 3)")
print("=" * 55)

df = pd.read_csv(os.path.join(DER, "13_forecasting_features.csv"))
df["date"] = pd.to_datetime(df["date"])

# Match layer3_forecasting.py exactly: drop COVID rows, sort, 80/20 chronological split
df = df[df["is_covid"] == 0].copy()
df = df.sort_values(["station_name", "date"]).reset_index(drop=True)

split_idx = int(len(df) * 0.80)
test = df.iloc[split_idx:].copy()

# Naive prediction: footfall on the same weekday, 7 days earlier (already engineered as lag_7d)
test = test.dropna(subset=["lag_7d"])
actual    = test["footfall"].values
predicted = test["lag_7d"].values

mae  = np.mean(np.abs(actual - predicted))
mape = np.mean(np.abs((actual - predicted) / (actual + 1))) * 100  # same formula as layer3_forecasting.py
ss_res = np.sum((actual - predicted) ** 2)
ss_tot = np.sum((actual - actual.mean()) ** 2)
r2 = 1 - ss_res / ss_tot

print(f"  Test rows : {len(test):,}")
print(f"  MAE       : {mae:.1f}")
print(f"  MAPE      : {mape:.2f}%")
print(f"  R2        : {r2:.4f}")

summary = pd.DataFrame([{
    "model": "Seasonal Naive (same day last week)",
    "mae": round(float(mae), 1),
    "mape": round(float(mape), 2),
    "r2": round(float(r2), 4),
    "test_rows": len(test),
}])
summary.to_csv(os.path.join(RESULTS, "baseline_naive_forecast.csv"), index=False)

print(f"\n  Saved:")
print(f"  └── Outputs/Results/baseline_naive_forecast.csv")
