# ============================================================
# feature_engineering.py
# Feature Engineering — Mumbai Metro Optimization
# Input  : Data/Derived/10_classification_ready.csv
#          Data/Derived/11_forecasting_ready.csv
#          Data/Derived/04_lmpi_scores.csv
#          Data/Raw/01_station_master.csv
# Output : Data/Derived/12_classification_features.csv
#          Data/Derived/13_forecasting_features.csv
# ============================================================

import pandas as pd
import numpy as np
import os
from sklearn.preprocessing import MinMaxScaler, LabelEncoder
import warnings
warnings.filterwarnings("ignore")

BASE = r"C:\Users\parek\Downloads\LY Project"
RAW  = os.path.join(BASE, "Data", "Raw")
DER  = os.path.join(BASE, "Data", "Derived")

print("=" * 55)
print("  FEATURE ENGINEERING — Mumbai Metro Optimization")
print("=" * 55)

# ── Load datasets ─────────────────────────────────────────────
print("\n[1/6] Loading datasets...")
df_class   = pd.read_csv(os.path.join(DER, "10_classification_ready.csv"))
df_fore    = pd.read_csv(os.path.join(DER, "11_forecasting_ready.csv"))
df_lmpi    = pd.read_csv(os.path.join(DER, "04_lmpi_scores.csv"))
df_station = pd.read_csv(os.path.join(RAW, "01_station_master.csv"))

df_fore["date"] = pd.to_datetime(df_fore["date"])

print(f"  Classification : {len(df_class)} rows")
print(f"  Forecasting    : {len(df_fore):,} rows")

# ══════════════════════════════════════════════════════════════
# PART A — CLASSIFICATION FEATURE ENGINEERING (Layer 1)
# ══════════════════════════════════════════════════════════════
print("\n[2/6] Classification feature engineering...")

df_c = df_class.copy()

# ── A1: Interaction features ──────────────────────────────────
# Auto × walking combined problem (worst last-mile experience)
df_c["auto_walk_combined"]   = (df_c["auto_problem_score"] * df_c["walking_problem_score"]) / 100

# Bus + auto gap (if both bad → very poor connectivity)
df_c["transit_gap_score"]    = (df_c["bus_problem_score"] + df_c["auto_problem_score"]) / 2

# Crowding × interchange pressure
df_c["interchange_pressure"] = df_c["crowding_score"] * df_c["is_interchange"]

# Survey dissatisfaction index
df_c["dissatisfaction_idx"]  = (
    (5 - df_c["survey_satisfaction"]) * 0.35 +
    (5 - df_c["survey_auto_avail"])   * 0.25 +
    (5 - df_c["survey_bus_freq"])     * 0.20 +
    (5 - df_c["survey_safety"])       * 0.10 +
    (5 - df_c["survey_walkability"])  * 0.10
).round(3)

# ── A2: Composite scores ──────────────────────────────────────
# Infrastructure gap = how far supply is from demand
df_c["infra_gap"] = (
    (1 - df_c["auto_supply_score"])       * 0.40 +
    (1 - df_c["bus_connectivity_score"])  * 0.35 +
    (df_c["walk_dist_m"] / 1000)          * 0.25
).round(3)

# Accessibility score (inverse of problem)
df_c["accessibility_score"] = (100 - df_c["lmpi_score"]).round(1)

# Population pressure = density × crowding
df_c["population_pressure"] = (df_c["pop_density"] * df_c["crowding_score"] / 100).round(3)

# ── A3: Rank features ─────────────────────────────────────────
# Rank stations within each line by LMPI
df_c["lmpi_rank_in_line"] = df_c.groupby("line")["lmpi_score"].rank(
    ascending=False, method="dense").astype(int)

# Percentile of LMPI across all stations
df_c["lmpi_percentile"] = df_c["lmpi_score"].rank(pct=True).round(3)

# ── A4: Binary flags ──────────────────────────────────────────
df_c["is_critical_auto"]    = (df_c["auto_problem_score"]    > 60).astype(int)
df_c["is_critical_walk"]    = (df_c["walking_problem_score"] > 60).astype(int)
df_c["is_critical_bus"]     = (df_c["bus_problem_score"]     > 60).astype(int)
df_c["is_high_population"]  = (df_c["pop_density"]           > 0.70).astype(int)
df_c["is_multi_problem"]    = (
    df_c[["is_critical_auto","is_critical_walk","is_critical_bus"]].sum(axis=1) >= 2
).astype(int)

# ── A5: Frequency features ────────────────────────────────────
# Frequency gap ratio
df_c["freq_gap_ratio"] = (df_c["freq_delta_peak"] / df_c["rec_trains_peak"]).round(3)

# ── A6: Final classification feature set ─────────────────────
CLASS_FINAL_FEATURES = [
    # Original LMPI factors
    "auto_problem_score","walking_problem_score","bus_problem_score",
    "crowding_score","safety_score","lmpi_score",
    # Station characteristics
    "pop_density","auto_supply_score","bus_connectivity_score",
    "walk_dist_m","is_interchange","is_elevated","role_encoded",
    # Survey features
    "survey_satisfaction","survey_auto_avail","survey_bus_freq",
    "survey_safety","survey_walkability",
    # Engineered interaction features
    "auto_walk_combined","transit_gap_score","interchange_pressure",
    "dissatisfaction_idx","infra_gap","accessibility_score",
    "population_pressure",
    # Rank features
    "lmpi_rank_in_line","lmpi_percentile",
    # Binary flags
    "is_critical_auto","is_critical_walk","is_critical_bus",
    "is_high_population","is_multi_problem",
    # Frequency features
    "rec_trains_peak","freq_delta_peak","freq_gap_ratio","freq_impact",
    # Intervention
    "best_impact","num_interventions",
]

df_c_out = df_c[["station_name","line","severity_label","severity_encoded"] +
                CLASS_FINAL_FEATURES].copy()

# Handle nulls
df_c_out[CLASS_FINAL_FEATURES] = df_c_out[CLASS_FINAL_FEATURES].fillna(
    df_c_out[CLASS_FINAL_FEATURES].median())

# Scale
scaler_c = MinMaxScaler()
df_c_scaled = df_c_out.copy()
df_c_scaled[CLASS_FINAL_FEATURES] = scaler_c.fit_transform(
    df_c_out[CLASS_FINAL_FEATURES])

# Save
df_c_out.to_csv(os.path.join(DER, "12_classification_features.csv"), index=False)
df_c_scaled.to_csv(os.path.join(DER, "12_classification_features_scaled.csv"), index=False)

print(f"  Original features  : {len(df_class.columns) - 4}")
print(f"  Engineered features: {len(CLASS_FINAL_FEATURES)}")
print(f"  New features added : {len(CLASS_FINAL_FEATURES) - (len(df_class.columns) - 4)}")
print(f"  Nulls              : {df_c_out[CLASS_FINAL_FEATURES].isnull().sum().sum()}")
print(f"  Rows               : {len(df_c_out)}")

# ══════════════════════════════════════════════════════════════
# PART B — FORECASTING FEATURE ENGINEERING (Layer 3)
# ══════════════════════════════════════════════════════════════
print("\n[3/6] Forecasting feature engineering...")

df_f = df_fore.copy()

# ── B1: Time-based features ───────────────────────────────────
df_f["year"]          = df_f["date"].dt.year
df_f["day_of_week"]   = df_f["date"].dt.dayofweek      # 0=Mon, 6=Sun
df_f["day_of_year"]   = df_f["date"].dt.dayofyear
df_f["week_of_year"]  = df_f["date"].dt.isocalendar().week.astype(int)
df_f["quarter"]       = df_f["date"].dt.quarter
df_f["is_weekend"]    = (df_f["day_of_week"] >= 5).astype(int)
df_f["is_month_start"]= df_f["date"].dt.is_month_start.astype(int)
df_f["is_month_end"]  = df_f["date"].dt.is_month_end.astype(int)

# ── B2: Cyclical encoding (sine/cosine) ───────────────────────
# Captures cyclical nature of month, day of week, day of year
df_f["month_sin"]     = np.sin(2 * np.pi * df_f["month"] / 12)
df_f["month_cos"]     = np.cos(2 * np.pi * df_f["month"] / 12)
df_f["dow_sin"]       = np.sin(2 * np.pi * df_f["day_of_week"] / 7)
df_f["dow_cos"]       = np.cos(2 * np.pi * df_f["day_of_week"] / 7)
df_f["doy_sin"]       = np.sin(2 * np.pi * df_f["day_of_year"] / 365)
df_f["doy_cos"]       = np.cos(2 * np.pi * df_f["day_of_year"] / 365)

# ── B3: Growth features ───────────────────────────────────────
# Year-over-year growth proxy (lines 2A and 7 growing fast)
LINE_GROWTH_RATE = {"1": 0.02, "2A": 0.45, "7": 0.42, "3": 0.80}
df_f["line_growth_rate"] = df_f["line"].map(LINE_GROWTH_RATE).fillna(0.02)

# Years since line opened
LINE_OPEN_YEAR = {"1": 2014, "2A": 2022, "7": 2022, "3": 2024}
df_f["years_operational"] = df_f["year"] - df_f["line"].map(LINE_OPEN_YEAR).fillna(2022)
df_f["years_operational"] = df_f["years_operational"].clip(lower=0)

# ── B4: Lag interaction features ─────────────────────────────
# Week-over-week change
df_f["wow_change"] = ((df_f["footfall"] - df_f["lag_7d"]) /
                       df_f["lag_7d"].replace(0, np.nan)).fillna(0).round(4)

# Month-over-month change
df_f["mom_change"] = ((df_f["footfall"] - df_f["lag_30d"]) /
                       df_f["lag_30d"].replace(0, np.nan)).fillna(0).round(4)

# Footfall vs rolling average ratio
df_f["footfall_vs_avg"] = (df_f["footfall"] /
                            df_f["rolling_7d_avg"].replace(0, np.nan)).fillna(1).round(4)

# ── B5: External effect features ─────────────────────────────
# Combined external boost
df_f["external_boost"] = (
    df_f["festival_boost"].fillna(0) +
    df_f["rain_ridership_boost"].fillna(0)
).round(3)

# Monsoon × elevated interaction
df_f["monsoon_elevated"] = df_f["is_monsoon"] * df_f["is_elevated"]

# Festival × weekend interaction
df_f["festival_weekend"] = df_f["is_festival"] * df_f["is_weekend"]

# ── B6: Station-level normalized features ────────────────────
# Normalize footfall within each station (0-1 relative to that station's history)
df_f["footfall_normalized"] = df_f.groupby("station_name")["footfall"].transform(
    lambda x: (x - x.min()) / (x.max() - x.min() + 1)
).round(4)

# Station footfall share of line total per day
line_daily = df_f.groupby(["line","date"])["footfall"].transform("sum")
df_f["station_line_share"] = (df_f["footfall"] / line_daily.replace(0, np.nan)).fillna(0).round(4)

# ── B7: Final forecasting feature set ─────────────────────────
FORE_FINAL_FEATURES = [
    # Target
    "footfall",
    # Time features
    "year","month","day_of_week","day_of_year","week_of_year","quarter",
    "is_weekday","is_weekend","is_month_start","is_month_end",
    # Cyclical encoding
    "month_sin","month_cos","dow_sin","dow_cos","doy_sin","doy_cos",
    # Lag features
    "lag_1d","lag_7d","lag_30d","rolling_7d_avg","rolling_30d_avg",
    # Lag interactions
    "wow_change","mom_change","footfall_vs_avg",
    # External effects
    "is_monsoon","monsoon_intensity_enc","rainfall_mm","rain_ridership_boost",
    "is_festival","festival_boost","is_public_holiday",
    "external_boost","monsoon_elevated","festival_weekend",
    # Station features
    "is_interchange","is_elevated","pop_density","lmpi_score","severity_encoded",
    # Growth features
    "line_growth_rate","years_operational",
    # Normalized
    "footfall_normalized","station_line_share",
    # COVID flag
    "is_covid",
]

df_f_out = df_f[["station_name","line","date"] + FORE_FINAL_FEATURES].copy()

# Handle nulls
num_cols = df_f_out.select_dtypes(include=[np.number]).columns
df_f_out[num_cols] = df_f_out[num_cols].fillna(df_f_out[num_cols].median())

print(f"  Original features  : {len(df_fore.columns) - 3}")
print(f"  Engineered features: {len(FORE_FINAL_FEATURES)}")
print(f"  New features added : {len(FORE_FINAL_FEATURES) - (len(df_fore.columns) - 3)}")
print(f"  Nulls              : {df_f_out[num_cols].isnull().sum().sum()}")
print(f"  Rows               : {len(df_f_out):,}")

# Save
df_f_out.to_csv(os.path.join(DER, "13_forecasting_features.csv"), index=False)

# ── Feature importance preview ────────────────────────────────
print("\n[4/6] Feature correlation with footfall (top 10)...")
corr_with_target = df_f_out[FORE_FINAL_FEATURES].corr()["footfall"].drop("footfall")
top10 = corr_with_target.abs().nlargest(10)
for feat, val in top10.items():
    direction = "+" if corr_with_target[feat] > 0 else "-"
    print(f"  {feat:<30} {direction}{val:.4f}")

# ── Classification feature summary ───────────────────────────
print("\n[5/6] Classification feature correlation with LMPI (top 10)...")
corr_lmpi = df_c_out[CLASS_FINAL_FEATURES].corr()["lmpi_score"].drop("lmpi_score")
top10_c = corr_lmpi.abs().nlargest(10)
for feat, val in top10_c.items():
    direction = "+" if corr_lmpi[feat] > 0 else "-"
    print(f"  {feat:<30} {direction}{val:.4f}")

# ── Final summary ─────────────────────────────────────────────
print("\n[6/6] Saving outputs...")
outputs = [
    ("12_classification_features.csv",        df_c_out),
    ("12_classification_features_scaled.csv",  df_c_scaled),
    ("13_forecasting_features.csv",            df_f_out),
]
for fname, df in outputs:
    path = os.path.join(DER, fname)
    size = os.path.getsize(path) / 1024
    print(f"  {fname:<45} {len(df):>7,} rows  {size:>7.0f} KB")

print("\n" + "=" * 55)
print("  FEATURE ENGINEERING COMPLETE")
print("=" * 55)
print(f"\n  Classification features : {len(CLASS_FINAL_FEATURES)}")
print(f"  Forecasting features    : {len(FORE_FINAL_FEATURES)}")
print(f"\n  Ready for:")
print(f"  → Layer 1 : 12_classification_features.csv")
print(f"  → Layer 3 : 13_forecasting_features.csv")