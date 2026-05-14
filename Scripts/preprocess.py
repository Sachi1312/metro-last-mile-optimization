# ============================================================
# preprocess.py
# Merges all 8 CSVs, cleans, encodes, scales
# Input  : Data/Raw/ + Data/Derived/
# Output : Data/Derived/09_master_features.csv
#          Data/Derived/10_classification_ready.csv
#          Data/Derived/11_forecasting_ready.csv
# ============================================================

import pandas as pd
import numpy as np
import os
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
import warnings
warnings.filterwarnings("ignore")

BASE = r"C:\Users\parek\Downloads\LY Project"
RAW  = os.path.join(BASE, "Data", "Raw")
DER  = os.path.join(BASE, "Data", "Derived")

print("=" * 55)
print("  PREPROCESSING PIPELINE — Mumbai Metro Optimization")
print("=" * 55)

# ── STEP 1: Load all 8 CSVs ──────────────────────────────────
print("\n[1/8] Loading datasets...")

df_station  = pd.read_csv(os.path.join(RAW, "01_station_master.csv"))
df_hist     = pd.read_csv(os.path.join(RAW, "02_historical_ridership_5yr.csv"))
df_hourly   = pd.read_csv(os.path.join(RAW, "03_hourly_ridership_12mo.csv"))
df_lmpi     = pd.read_csv(os.path.join(DER, "04_lmpi_scores.csv"))
df_temporal = pd.read_csv(os.path.join(DER, "05_temporal_features.csv"))
df_freq     = pd.read_csv(os.path.join(DER, "06_frequency_optimization.csv"))
df_interv   = pd.read_csv(os.path.join(DER, "07_intervention_scores.csv"))
df_survey   = pd.read_csv(os.path.join(RAW, "08_survey_responses.csv"))

print(f"  01 Station Master      : {len(df_station):>7,} rows")
print(f"  02 Historical Ridership: {len(df_hist):>7,} rows")
print(f"  03 Hourly Ridership    : {len(df_hourly):>7,} rows")
print(f"  04 LMPI Scores         : {len(df_lmpi):>7,} rows")
print(f"  05 Temporal Features   : {len(df_temporal):>7,} rows")
print(f"  06 Frequency Optim.    : {len(df_freq):>7,} rows")
print(f"  07 Intervention Scores : {len(df_interv):>7,} rows")
print(f"  08 Survey Responses    : {len(df_survey):>7,} rows")

# ── STEP 2: Clean station master ─────────────────────────────
print("\n[2/8] Cleaning station master...")

# Fix interchange_with column
df_station["interchange_with"] = df_station["interchange_with"].fillna("none")
df_station["is_interchange"]   = df_station["is_interchange"].astype(int)
df_station["is_elevated"]      = df_station["is_elevated"].astype(int)

# Normalize line names
df_station["line"] = df_station["line"].astype(str).str.strip()

print(f"  Stations cleaned: {len(df_station)}")
print(f"  Lines: {df_station['line'].unique().tolist()}")
print(f"  Roles: {df_station['role'].nunique()} unique roles")

# ── STEP 3: Clean LMPI scores ────────────────────────────────
print("\n[3/8] Cleaning LMPI scores...")

# Check for nulls
null_count = df_lmpi.isnull().sum().sum()
print(f"  Null values: {null_count}")

# Clamp scores
score_cols = ["auto_problem_score","walking_problem_score",
              "bus_problem_score","crowding_score","safety_score","lmpi_score"]
for col in score_cols:
    df_lmpi[col] = df_lmpi[col].clip(0, 100).round(1)

# Encode severity label
sev_order = {"Critical": 3, "High": 2, "Medium": 1, "Low": 0}
df_lmpi["severity_encoded"] = df_lmpi["severity_label"].map(sev_order)

print(f"  LMPI range: {df_lmpi['lmpi_score'].min()} – {df_lmpi['lmpi_score'].max()}")
print(f"  Severity distribution:")
print(df_lmpi["severity_label"].value_counts().to_string())

# ── STEP 4: Clean temporal features ──────────────────────────
print("\n[4/8] Cleaning temporal features...")

df_temporal["date"] = pd.to_datetime(df_temporal["date"])
df_temporal["rainfall_mm"] = df_temporal["rainfall_mm"].fillna(0)
df_temporal["festival_boost"] = df_temporal["festival_boost"].fillna(0)

# Encode categoricals
df_temporal["day_type_encoded"]       = (df_temporal["day_type"] == "weekday").astype(int)
df_temporal["monsoon_intensity_enc"]  = df_temporal["monsoon_intensity"].map(
    {"none": 0, "light": 1, "moderate": 2, "heavy": 3}
).fillna(0).astype(int)

print(f"  Date range: {df_temporal['date'].min().date()} to {df_temporal['date'].max().date()}")
print(f"  Monsoon days  : {df_temporal['is_monsoon'].sum()}")
print(f"  Festival days : {df_temporal['is_festival'].sum()}")
print(f"  Holiday days  : {df_temporal['is_public_holiday'].sum()}")

# ── STEP 5: Clean historical ridership ───────────────────────
print("\n[5/8] Cleaning historical ridership...")

df_hist["date"] = pd.to_datetime(df_hist["date"])
df_hist["footfall"] = df_hist["footfall"].clip(lower=0)

# Remove COVID outlier year (2020) from training
# or flag it separately
df_hist["is_covid"] = df_hist["date"].dt.year.isin([2020, 2021]).astype(int)

# Check nulls
null_hist = df_hist.isnull().sum().sum()
print(f"  Null values   : {null_hist}")
print(f"  Date range    : {df_hist['date'].min().date()} to {df_hist['date'].max().date()}")
print(f"  Total rows    : {len(df_hist):,}")
print(f"  Stations      : {df_hist['station_name'].nunique()}")
print(f"  COVID rows    : {df_hist['is_covid'].sum():,} (flagged, not removed)")

# ── STEP 6: Clean hourly ridership ───────────────────────────
print("\n[6/8] Cleaning hourly ridership...")

df_hourly["date"] = pd.to_datetime(df_hourly["date"])
df_hourly["hourly_footfall"] = df_hourly["hourly_footfall"].clip(lower=0)

# Encode peak type
peak_map = {"morning_peak": 2, "evening_peak": 2, "broad_peak": 1, "off_peak": 0}
df_hourly["peak_encoded"] = df_hourly["peak_type"].map(peak_map).fillna(0).astype(int)

null_hourly = df_hourly.isnull().sum().sum()
print(f"  Null values   : {null_hourly}")
print(f"  Total rows    : {len(df_hourly):,}")
print(f"  Hours covered : {sorted(df_hourly['hour'].unique())}")

# ── STEP 7: Build classification-ready dataset ───────────────
print("\n[7/8] Building classification dataset (Layer 1)...")

# Base: LMPI scores per station
df_class = df_lmpi.copy()

# Merge station master features
df_class = df_class.merge(
    df_station[[
        "station_name","role","is_interchange","is_elevated",
        "pop_density","auto_supply_score","bus_connectivity_score","walk_dist_m"
    ]],
    on="station_name", how="left"
)

# Merge best intervention impact per station
best_interv = df_interv.groupby("station_name").agg(
    best_impact     = ("impact_score", "max"),
    num_interventions = ("intervention", "count"),
    avg_cost        = ("estimated_cost_lakhs", "mean"),
).reset_index()
df_class = df_class.merge(best_interv, on="station_name", how="left")

# Merge recommended frequency (morning peak)
freq_peak = df_freq[df_freq["time_window"] == "morning_peak"][[
    "station_name","recommended_trains_hr","delta_trains_hr","intervention_impact"
]].rename(columns={
    "recommended_trains_hr": "rec_trains_peak",
    "delta_trains_hr":       "freq_delta_peak",
    "intervention_impact":   "freq_impact",
})
df_class = df_class.merge(freq_peak, on="station_name", how="left")

# Encode categorical columns
le_role = LabelEncoder()
df_class["role_encoded"] = le_role.fit_transform(df_class["role"].fillna("unknown"))

le_lm = LabelEncoder()
df_class["last_mile_encoded"] = le_lm.fit_transform(df_class["recommended_last_mile"].fillna("Auto Rickshaw"))

# Final feature columns for classification
CLASS_FEATURES = [
    "auto_problem_score","walking_problem_score","bus_problem_score",
    "crowding_score","safety_score","lmpi_score",
    "pop_density","auto_supply_score","bus_connectivity_score","walk_dist_m",
    "is_interchange","is_elevated","role_encoded",
    "survey_satisfaction","survey_auto_avail","survey_bus_freq",
    "survey_safety","survey_walkability",
    "best_impact","num_interventions","avg_cost",
    "rec_trains_peak","freq_delta_peak","freq_impact",
]

df_class_out = df_class[["station_name","line","severity_label","severity_encoded"] + CLASS_FEATURES].copy()

# Handle any remaining nulls
df_class_out[CLASS_FEATURES] = df_class_out[CLASS_FEATURES].fillna(df_class_out[CLASS_FEATURES].median())

# Scale features to 0-1
scaler = MinMaxScaler()
df_class_scaled = df_class_out.copy()
df_class_scaled[CLASS_FEATURES] = scaler.fit_transform(df_class_out[CLASS_FEATURES])

# Save both unscaled and scaled
df_class_out.to_csv(os.path.join(DER, "10_classification_ready.csv"), index=False)
df_class_scaled.to_csv(os.path.join(DER, "10_classification_scaled.csv"), index=False)

print(f"  Rows    : {len(df_class_out)}")
print(f"  Features: {len(CLASS_FEATURES)}")
print(f"  Nulls   : {df_class_out[CLASS_FEATURES].isnull().sum().sum()}")
print(f"  Class distribution:")
print(df_class_out["severity_label"].value_counts().to_string())

# ── STEP 8: Build forecasting-ready dataset ──────────────────
print("\n[8/8] Building forecasting dataset (Layer 3)...")

# Use daily historical data + temporal features
df_fore = df_hist.merge(
    df_temporal[[
        "date","day_type_encoded","month","is_monsoon",
        "monsoon_intensity_enc","rain_ridership_boost",
        "is_public_holiday","total_boost_multiplier"
    ]],
    on="date", how="left"
)

# Merge station features
df_fore = df_fore.merge(
    df_station[[
        "station_name","role","is_interchange","is_elevated",
        "pop_density","auto_supply_score","bus_connectivity_score"
    ]],
    on="station_name", how="left"
)

# Merge LMPI
df_fore = df_fore.merge(
    df_lmpi[["station_name","lmpi_score","severity_encoded"]],
    on="station_name", how="left"
)

# Add lag features
print("  Computing lag features...")
df_fore = df_fore.sort_values(["station_name","date"]).reset_index(drop=True)

df_fore["lag_1d"]  = df_fore.groupby("station_name")["footfall"].shift(1)
df_fore["lag_7d"]  = df_fore.groupby("station_name")["footfall"].shift(7)
df_fore["lag_30d"] = df_fore.groupby("station_name")["footfall"].shift(30)
df_fore["rolling_7d_avg"]  = df_fore.groupby("station_name")["footfall"].transform(
    lambda x: x.shift(1).rolling(7, min_periods=1).mean()
)
df_fore["rolling_30d_avg"] = df_fore.groupby("station_name")["footfall"].transform(
    lambda x: x.shift(1).rolling(30, min_periods=1).mean()
)

# Encode day type
df_fore["is_weekday"] = df_fore["day_type_encoded"].fillna(
    df_fore["date"].dt.dayofweek.apply(lambda x: 1 if x < 5 else 0)
).astype(int)

# Drop COVID rows for clean training (keep flagged)
print("  Columns after merge:", [c for c in df_fore.columns if c in ["rainfall_mm","is_festival","festival_boost","day_type_encoded"]])
df_fore_clean = df_fore[df_fore["is_covid"] == 0].copy()

# Drop rows with null footfall
df_fore_clean = df_fore_clean.dropna(subset=["footfall"])

# Fill lag nulls with station median
# Fill lag nulls with station median
lag_cols = ["lag_1d","lag_7d","lag_30d","rolling_7d_avg","rolling_30d_avg"]
for col in lag_cols:
    df_fore_clean[col] = df_fore_clean.groupby("station_name")[col].transform(
        lambda x: x.fillna(x.median())
    )

# Fill temporal nulls (pre-2024 dates have no temporal features)
df_fore_clean["is_monsoon"]            = df_fore_clean["is_monsoon"].fillna(
    df_fore_clean["date"].dt.month.isin([6,7,8,9]).astype(int))
df_fore_clean["monsoon_intensity_enc"] = df_fore_clean["monsoon_intensity_enc"].fillna(0).astype(int)
df_fore_clean["rain_ridership_boost"]  = df_fore_clean["rain_ridership_boost"].fillna(0)
df_fore_clean["is_public_holiday"]     = df_fore_clean["is_public_holiday"].fillna(0).astype(int)
df_fore_clean["total_boost_multiplier"]= df_fore_clean["total_boost_multiplier"].fillna(1.0)
df_fore_clean["day_type_encoded"]      = df_fore_clean["day_type_encoded"].fillna(
    df_fore_clean["date"].dt.dayofweek.apply(lambda x: 1 if x < 5 else 0))
df_fore_clean["month"]                 = df_fore_clean["month"].fillna(
    df_fore_clean["date"].dt.month)

# Final forecasting features
FORE_FEATURES = [
    "station_name","line","date","footfall",
    "is_weekday","month","is_monsoon","monsoon_intensity_enc",
    "rainfall_mm","rain_ridership_boost",
    "is_festival","festival_boost","is_public_holiday",
    "total_boost_multiplier","is_interchange","is_elevated",
    "pop_density","lmpi_score","severity_encoded","is_covid",
    "lag_1d","lag_7d","lag_30d","rolling_7d_avg","rolling_30d_avg",
]

df_fore_out = df_fore_clean[FORE_FEATURES].copy()
df_fore_out.to_csv(os.path.join(DER, "11_forecasting_ready.csv"), index=False)

print(f"  Rows    : {len(df_fore_out):,}")
print(f"  Features: {len(FORE_FEATURES)}")
print(f"  Nulls   : {df_fore_out.isnull().sum().sum()}")
print(f"  Date range: {df_fore_out['date'].min()} to {df_fore_out['date'].max()}")

# ── FINAL SUMMARY ─────────────────────────────────────────────
print("\n" + "=" * 55)
print("  PREPROCESSING COMPLETE")
print("=" * 55)
print(f"\n  Output files in Data/Derived/:")
outputs = [
    "10_classification_ready.csv",
    "10_classification_scaled.csv",
    "11_forecasting_ready.csv",
]
for f in outputs:
    path = os.path.join(DER, f)
    size = os.path.getsize(path) / 1024
    rows = len(pd.read_csv(path))
    print(f"  {f:<35} {rows:>7,} rows  {size:>7.0f} KB")

print(f"\n  Ready for:")
print(f"  → Layer 1 : 10_classification_ready.csv")
print(f"  → Layer 3 : 11_forecasting_ready.csv")
print(f"  → EDA     : both files above")