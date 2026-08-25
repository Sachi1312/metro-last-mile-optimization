# ============================================================
# baseline_linear_forecast.py
# Layer 3 baseline — Linear Regression, same features as XGBoost
# Trains a plain linear model on the exact same feature set and
# chronological 80/20 split as Scripts/layer3_forecasting.py, so
# the comparison isolates "does the model matter" from "do the
# features matter" — unlike the seasonal-naive baseline (no model)
# or Prophet (different feature set entirely).
# Input  : Data/Derived/13_forecasting_features.csv
# Output : Outputs/Results/baseline_linear_forecast.csv
# ============================================================

import pandas as pd
import numpy as np
import os
import warnings
warnings.filterwarnings("ignore")

from sklearn.linear_model import LinearRegression

BASE    = r"C:\Users\parek\Downloads\LY Project"
DER     = os.path.join(BASE, "Data", "Derived")
RESULTS = os.path.join(BASE, "Outputs", "Results")
os.makedirs(RESULTS, exist_ok=True)

print("=" * 55)
print("  BASELINE — LINEAR REGRESSION (Layer 3)")
print("=" * 55)

df = pd.read_csv(os.path.join(DER, "13_forecasting_features.csv"))
df["date"] = pd.to_datetime(df["date"])

# Match layer3_forecasting.py exactly: drop COVID rows, sort, 80/20 chronological split
df = df[df["is_covid"] == 0].copy()
df = df.sort_values(["station_name", "date"]).reset_index(drop=True)

XGB_FEATURES = [
    "year","month","day_of_week","day_of_year","week_of_year","quarter",
    "is_weekday","is_weekend","is_month_start","is_month_end",
    "month_sin","month_cos","dow_sin","dow_cos","doy_sin","doy_cos",
    "lag_1d","lag_7d","lag_30d","rolling_7d_avg","rolling_30d_avg",
    "wow_change","mom_change",
    "is_monsoon","monsoon_intensity_enc","rainfall_mm","rain_ridership_boost",
    "is_festival","festival_boost","is_public_holiday","external_boost",
    "monsoon_elevated","festival_weekend",
    "is_interchange","is_elevated","pop_density","lmpi_score","severity_encoded",
    "line_growth_rate","years_operational",
    "station_line_share",
]
XGB_FEATURES = [f for f in XGB_FEATURES if f in df.columns]

df["station_enc"] = df["station_name"].astype("category").cat.codes
FEATURES_FULL = XGB_FEATURES + ["station_enc"]

X_all = df[FEATURES_FULL].fillna(0)
y_all = df["footfall"]

split_idx = int(len(df) * 0.80)
X_train, X_test = X_all.iloc[:split_idx], X_all.iloc[split_idx:]
y_train, y_test = y_all.iloc[:split_idx], y_all.iloc[split_idx:]

model = LinearRegression()
model.fit(X_train, y_train)
y_pred = model.predict(X_test)

mae  = np.mean(np.abs(y_test.values - y_pred))
mape = np.mean(np.abs((y_test.values - y_pred) / (y_test.values + 1))) * 100  # same formula as layer3_forecasting.py
ss_res = np.sum((y_test.values - y_pred) ** 2)
ss_tot = np.sum((y_test.values - y_test.values.mean()) ** 2)
r2 = 1 - ss_res / ss_tot

print(f"  Test rows : {len(X_test):,}")
print(f"  MAE       : {mae:.1f}")
print(f"  MAPE      : {mape:.2f}%")
print(f"  R2        : {r2:.4f}")

summary = pd.DataFrame([{
    "model": "Linear Regression",
    "mae": round(float(mae), 1),
    "mape": round(float(mape), 2),
    "r2": round(float(r2), 4),
    "test_rows": len(X_test),
}])
summary.to_csv(os.path.join(RESULTS, "baseline_linear_forecast.csv"), index=False)

print(f"\n  Saved:")
print(f"  └── Outputs/Results/baseline_linear_forecast.csv")
