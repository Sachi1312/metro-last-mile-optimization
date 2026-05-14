# ============================================================
# update_monthly.py
# Monthly update — validate → append → retrain → forecast
# Usage: python Scripts\update_monthly.py --input <csv_path>
# Run once at end of every month when new AFCS data arrives
# ============================================================

import pandas as pd
import numpy as np
import os
import sys
import argparse
import joblib
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pymongo import MongoClient
import warnings
warnings.filterwarnings("ignore")

BASE    = r"C:\Users\parek\Downloads\LY Project"
RAW     = os.path.join(BASE, "Data", "Raw")
DER     = os.path.join(BASE, "Data", "Derived")
MODELS  = os.path.join(BASE, "Models")
RESULTS = os.path.join(BASE, "Outputs", "Results")

# Load environment
load_dotenv(os.path.join(BASE, ".env"))
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME   = os.getenv("DB_NAME", "metropt")

np.random.seed(42)

print("=" * 60)
print("  MONTHLY UPDATE — Mumbai Metro Optimization")
print("=" * 60)

# ── Parse arguments ───────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True,
                    help="Path to new AFCS CSV (e.g. Data/New/april_2026_afcs.csv)")
args = parser.parse_args()

# ══════════════════════════════════════════════════════════════
# STEP 1: Validate incoming data
# ══════════════════════════════════════════════════════════════
print(f"\n[1/7] Validating incoming data...")
print(f"  File: {args.input}")

from validate_data import validate
if not validate(args.input):
    print("\n  ❌ Validation failed — aborting monthly update")
    print("  Fix the errors in the input file and try again")
    sys.exit(1)

print("  ✅ Validation passed — proceeding with update")

# ══════════════════════════════════════════════════════════════
# STEP 2: Load new data
# ══════════════════════════════════════════════════════════════
print(f"\n[2/7] Loading new AFCS data...")

df_new = pd.read_csv(args.input)
df_new["date"] = pd.to_datetime(df_new["date"])
df_new["is_synthetic"] = 0
df_new["is_covid"]     = 0

# Add missing columns with defaults
for col in ["festival_name","rain_intensity","festival_boost","rain_boost"]:
    if col not in df_new.columns:
        df_new[col] = "none" if "name" in col or "intensity" in col else 0

new_month = df_new["date"].dt.to_period("M").iloc[0]
print(f"  New data month   : {new_month}")
print(f"  New rows         : {len(df_new):,}")
print(f"  Stations covered : {df_new['station_name'].nunique()}")

# ══════════════════════════════════════════════════════════════
# STEP 3: Append to historical CSV + MongoDB
# ══════════════════════════════════════════════════════════════
print(f"\n[3/7] Appending to historical data...")

# Load existing
extended_path = os.path.join(RAW, "02_historical_ridership_extended.csv")
df_existing   = pd.read_csv(extended_path)
df_existing["date"] = pd.to_datetime(df_existing["date"])

rows_before = len(df_existing)

# Align columns
for col in df_existing.columns:
    if col not in df_new.columns:
        df_new[col] = 0
df_new = df_new[df_existing.columns]

# Append
df_combined = pd.concat([df_existing, df_new], ignore_index=True)
df_combined = df_combined.sort_values(["station_name","date"]).reset_index(drop=True)

# Save updated CSV
df_combined.to_csv(extended_path, index=False)
print(f"  Rows before  : {rows_before:,}")
print(f"  Rows added   : {len(df_new):,}")
print(f"  Rows after   : {len(df_combined):,}")
print(f"  Date range   : {df_combined['date'].min().date()} → {df_combined['date'].max().date()}")

# Update MongoDB
print(f"  Updating MongoDB...")
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
    db     = client[DB_NAME]

    # Add new records to historical_ridership collection
    new_records = df_new.copy()
    new_records["date"] = new_records["date"].dt.to_pydatetime()
    new_records = new_records.where(pd.notnull(new_records), None)
    db["historical_ridership"].insert_many(new_records.to_dict("records"))
    print(f"  ✅ MongoDB historical_ridership updated ({len(df_new):,} docs added)")
except Exception as e:
    print(f"  ⚠️  MongoDB update failed: {e} — CSV updated successfully")

# ══════════════════════════════════════════════════════════════
# STEP 4: Retrain XGBoost forecaster
# ══════════════════════════════════════════════════════════════
print(f"\n[4/7] Retraining XGBoost forecaster...")

from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error
import numpy as np

# Load feature engineering output and rebuild with new data
df_train = df_combined[df_combined["is_covid"] == 0].copy()
df_train = df_train.sort_values(["station_name","date"]).reset_index(drop=True)

# Add station encoding
df_train["station_enc"] = df_train["station_name"].astype("category").cat.codes

# Add lag features
print("  Computing lag features...")
df_train["lag_1d"]  = df_train.groupby("station_name")["footfall"].shift(1)
df_train["lag_7d"]  = df_train.groupby("station_name")["footfall"].shift(7)
df_train["lag_30d"] = df_train.groupby("station_name")["footfall"].shift(30)
df_train["rolling_7d_avg"]  = df_train.groupby("station_name")["footfall"].transform(
    lambda x: x.shift(1).rolling(7, min_periods=1).mean())
df_train["rolling_30d_avg"] = df_train.groupby("station_name")["footfall"].transform(
    lambda x: x.shift(1).rolling(30, min_periods=1).mean())

# Time features
df_train["year"]        = df_train["date"].dt.year
df_train["month"]       = df_train["date"].dt.month
df_train["day_of_week"] = df_train["date"].dt.dayofweek
df_train["day_of_year"] = df_train["date"].dt.dayofyear
df_train["is_weekday"]  = (df_train["day_of_week"] < 5).astype(int)
df_train["is_weekend"]  = (df_train["day_of_week"] >= 5).astype(int)
df_train["month_sin"]   = np.sin(2*np.pi*df_train["month"]/12)
df_train["month_cos"]   = np.cos(2*np.pi*df_train["month"]/12)
df_train["dow_sin"]     = np.sin(2*np.pi*df_train["day_of_week"]/7)
df_train["dow_cos"]     = np.cos(2*np.pi*df_train["day_of_week"]/7)
df_train["is_monsoon"]  = df_train["month"].isin([6,7,8,9]).astype(int)

# External features
df_train["festival_boost"]       = pd.to_numeric(df_train.get("festival_boost",0), errors="coerce").fillna(0)
df_train["rain_boost"]           = pd.to_numeric(df_train.get("rain_boost",0), errors="coerce").fillna(0)
df_train["external_boost"]       = df_train["festival_boost"] + df_train["rain_boost"]
df_train["is_festival"]          = pd.to_numeric(df_train.get("is_festival",0), errors="coerce").fillna(0)
df_train["line_growth_rate"]     = df_train["line"].map({"1":0.02,"2A":0.08,"7":0.08,"3":0.15}).fillna(0.02)
df_train["years_operational"]    = df_train["year"] - df_train["line"].map(
    {"1":2014,"2A":2022,"7":2022,"3":2024}).fillna(2022)

# Merge station features
df_station = pd.read_csv(os.path.join(RAW, "01_station_master.csv"))
df_lmpi    = pd.read_csv(os.path.join(DER, "04_lmpi_scores.csv"))

sev_map = {"Critical":3,"High":2,"Medium":1,"Low":0}
df_lmpi["severity_encoded"] = df_lmpi["severity_label"].map(sev_map).fillna(1)

df_train = df_train.merge(
    df_station[["station_name","is_interchange","is_elevated","pop_density"]],
    on="station_name", how="left")
df_train = df_train.merge(
    df_lmpi[["station_name","lmpi_score","severity_encoded"]],
    on="station_name", how="left")

FEATURES = [
    "year","month","day_of_week","day_of_year","is_weekday","is_weekend",
    "month_sin","month_cos","dow_sin","dow_cos","is_monsoon",
    "lag_1d","lag_7d","lag_30d","rolling_7d_avg","rolling_30d_avg",
    "is_festival","festival_boost","external_boost",
    "is_interchange","is_elevated","pop_density",
    "lmpi_score","severity_encoded","line_growth_rate","years_operational",
    "station_enc",
]

df_model = df_train.dropna(subset=["footfall"]+FEATURES).copy()
X = df_model[FEATURES].fillna(0)
y = df_model["footfall"]

# Time-based split — last 10% as test
split_idx = int(len(X) * 0.90)
X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

xgb = XGBRegressor(
    n_estimators=300, max_depth=6, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.8,
    min_child_weight=5, random_state=42, verbosity=0,
)
xgb.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

y_pred = xgb.predict(X_test)
mae    = mean_absolute_error(y_test, y_pred)
mape   = np.mean(np.abs((y_test - y_pred) / (y_test + 1))) * 100

print(f"  Retrained on     : {len(X_train):,} rows")
print(f"  Test MAE         : {mae:,.0f} passengers")
print(f"  Test MAPE        : {mape:.2f}%")

# Save updated model
joblib.dump(xgb, os.path.join(MODELS, "xgb_forecaster.pkl"))
print(f"  ✅ Model saved: Models/xgb_forecaster.pkl")

# ══════════════════════════════════════════════════════════════
# STEP 5: Generate new 30-day forecast
# ══════════════════════════════════════════════════════════════
print(f"\n[5/7] Generating new 30-day forecast...")

last_date    = df_combined["date"].max()
future_dates = pd.date_range(last_date + timedelta(days=1), periods=30)
print(f"  Forecast period  : {future_dates[0].date()} → {future_dates[-1].date()}")

df_station_enc = df_combined[["station_name","station_enc"]].drop_duplicates().set_index("station_name")["station_enc"].to_dict()

rows = []
for fdate in future_dates:
    for _, st in df_station.iterrows():
        name = st["station_name"]
        line = str(st["line"])
        st_hist = df_combined[df_combined["station_name"]==name]

        feat = {
            "year":           fdate.year,
            "month":          fdate.month,
            "day_of_week":    fdate.dayofweek,
            "day_of_year":    fdate.dayofyear,
            "is_weekday":     int(fdate.dayofweek < 5),
            "is_weekend":     int(fdate.dayofweek >= 5),
            "month_sin":      np.sin(2*np.pi*fdate.month/12),
            "month_cos":      np.cos(2*np.pi*fdate.month/12),
            "dow_sin":        np.sin(2*np.pi*fdate.dayofweek/7),
            "dow_cos":        np.cos(2*np.pi*fdate.dayofweek/7),
            "is_monsoon":     int(fdate.month in [6,7,8,9]),
            "lag_1d":         st_hist["footfall"].iloc[-1]  if len(st_hist)>=1 else 0,
            "lag_7d":         st_hist["footfall"].iloc[-7]  if len(st_hist)>=7 else 0,
            "lag_30d":        st_hist["footfall"].iloc[-30] if len(st_hist)>=30 else 0,
            "rolling_7d_avg": st_hist["footfall"].iloc[-7:].mean()  if len(st_hist)>=7 else 0,
            "rolling_30d_avg":st_hist["footfall"].iloc[-30:].mean() if len(st_hist)>=30 else 0,
            "is_festival":    0,
            "festival_boost": 0,
            "external_boost": 0,
            "is_interchange": int(st["is_interchange"]),
            "is_elevated":    int(st["is_elevated"]),
            "pop_density":    st["pop_density"],
            "lmpi_score":     df_lmpi[df_lmpi["station_name"]==name]["lmpi_score"].values[0] if name in df_lmpi["station_name"].values else 50,
            "severity_encoded":df_lmpi[df_lmpi["station_name"]==name]["severity_encoded"].values[0] if name in df_lmpi["station_name"].values else 1,
            "line_growth_rate":{"1":0.02,"2A":0.08,"7":0.08,"3":0.15}.get(line, 0.02),
            "years_operational":fdate.year - {"1":2014,"2A":2022,"7":2022,"3":2024}.get(line, 2022),
            "station_enc":    df_station_enc.get(name, 0),
        }
        pred = int(max(0, xgb.predict(pd.DataFrame([feat]))[0]))
        rows.append({
            "date":                fdate.strftime("%Y-%m-%d"),
            "station_name":        name,
            "line":                st["line"],
            "forecasted_footfall": pred,
        })

df_forecast = pd.DataFrame(rows)
forecast_path = os.path.join(RESULTS, "layer3_30day_forecast.csv")
df_forecast.to_csv(forecast_path, index=False)
print(f"  ✅ New forecast saved: {len(df_forecast):,} rows")

# Update MongoDB forecast
try:
    db["results_forecast_30day"].drop()
    records = df_forecast.to_dict("records")
    db["results_forecast_30day"].insert_many(records)
    print(f"  ✅ MongoDB forecast updated")
except Exception as e:
    print(f"  ⚠️  MongoDB forecast update failed: {e}")

# ══════════════════════════════════════════════════════════════
# STEP 6: Update project metadata in MongoDB
# ══════════════════════════════════════════════════════════════
print(f"\n[6/7] Updating project metadata...")
try:
    db["project_metadata"].update_one(
        {},
        {"$set": {
            "last_updated":   datetime.now(),
            "data_range.end": df_combined["date"].max().strftime("%Y-%m-%d"),
            "forecast_range": {
                "start": future_dates[0].strftime("%Y-%m-%d"),
                "end":   future_dates[-1].strftime("%Y-%m-%d"),
            },
            "last_retrain_mape": round(mape, 3),
        }},
    )
    print(f"  ✅ Metadata updated")
except Exception as e:
    print(f"  ⚠️  Metadata update failed: {e}")

# ══════════════════════════════════════════════════════════════
# STEP 7: Summary
# ══════════════════════════════════════════════════════════════
print(f"\n[7/7] Monthly update complete")

print(f"\n{'=' * 60}")
print(f"  MONTHLY UPDATE COMPLETE")
print(f"{'=' * 60}")
print(f"\n  Month updated    : {new_month}")
print(f"  New rows added   : {len(df_new):,}")
print(f"  Total history    : {len(df_combined):,} rows")
print(f"  Data range       : {df_combined['date'].min().date()} → {df_combined['date'].max().date()}")
print(f"  Model MAPE       : {mape:.2f}% (was 2.64% at baseline)")
print(f"  Forecast period  : {future_dates[0].date()} → {future_dates[-1].date()}")
print(f"\n  Files updated:")
print(f"  ├── Data/Raw/02_historical_ridership_extended.csv")
print(f"  ├── Models/xgb_forecaster.pkl")
print(f"  └── Outputs/Results/layer3_30day_forecast.csv")
print(f"\n  MongoDB updated:")
print(f"  ├── historical_ridership (+{len(df_new):,} docs)")
print(f"  ├── results_forecast_30day (refreshed)")
print(f"  └── project_metadata (last_updated)")
print(f"\n  Dashboard will show fresh data automatically.")
print(f"\n  Next update: End of {(df_combined['date'].max() + timedelta(days=32)).strftime('%B %Y')}")

try:
    client.close()
except Exception:
    pass