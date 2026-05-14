# ============================================================
# derive_03_frequency.py
# Derives frequency recommendations from LMPI + MMRDA headway
# Input  : Data/Derived/04_lmpi_scores.csv
#          Data/Raw/01_station_master.csv
# Output : Data/Derived/06_frequency_optimization.csv
# ============================================================

import pandas as pd
import numpy as np
import os

BASE = r"C:\\Users\\parek\\Downloads\\LY Project"
RAW  = os.path.join(BASE, "Data", "Raw")
DER  = os.path.join(BASE, "Data", "Derived")

# ── STEP 1: Load inputs ───────────────────────────────────────
print("Loading LMPI scores and station master...")
df_lmpi    = pd.read_csv(os.path.join(DER, "04_lmpi_scores.csv"))
df_station = pd.read_csv(os.path.join(RAW, "01_station_master.csv"))
df = df_lmpi.merge(df_station[["station_name","is_interchange","is_elevated","role"]],
                   on="station_name", how="left")
print(f"  Loaded {len(df)} stations")

# ── STEP 2: Real MMRDA published headway data ─────────────────
# Source: MMRDA official timetables
# Trains per hour = 60 / headway_minutes
MMRDA_HEADWAY = {
    "1":  {"peak_min": 3,  "peak_max": 4,  "offpeak_min": 5,  "offpeak_max": 8},
    "2A": {"peak_min": 5,  "peak_max": 6,  "offpeak_min": 7,  "offpeak_max": 10},
    "2B": {"peak_min": 5,  "peak_max": 6,  "offpeak_min": 7,  "offpeak_max": 10},
    "7":  {"peak_min": 5,  "peak_max": 6,  "offpeak_min": 8,  "offpeak_max": 10},
    "3":  {"peak_min": 5,  "peak_max": 7,  "offpeak_min": 8,  "offpeak_max": 10},
}

def headway_to_trains(headway_min):
    return round(60 / headway_min, 1)

# Current trains/hr from published headways (midpoint)
CURRENT_FREQ = {
    "1":  {
        "morning_peak":  headway_to_trains(3.5),   # 17.1
        "evening_peak":  headway_to_trains(3.5),   # 17.1
        "midday":        headway_to_trains(6.0),   # 10.0
        "late_night":    headway_to_trains(10.0),  # 6.0
    },
    "2A": {
        "morning_peak":  headway_to_trains(5.5),   # 10.9
        "evening_peak":  headway_to_trains(5.5),   # 10.9
        "midday":        headway_to_trains(8.0),   # 7.5
        "late_night":    headway_to_trains(12.0),  # 5.0
    },
    "7": {
        "morning_peak":  headway_to_trains(5.5),
        "evening_peak":  headway_to_trains(5.5),
        "midday":        headway_to_trains(9.0),
        "late_night":    headway_to_trains(12.0),
    },
    "3": {
        "morning_peak":  headway_to_trains(6.0),
        "evening_peak":  headway_to_trains(6.0),
        "midday":        headway_to_trains(9.0),
        "late_night":    headway_to_trains(12.0),
    },
}

# ── STEP 3: Adjustment logic based on LMPI + interchange ─────
# Rule: Higher LMPI → more trains needed to handle crush load
# Interchange stations get additional buffer trains

def compute_adjustment(lmpi, severity, is_interchange, time_window):
    adj = 0
    # Severity-based adjustment
    if severity == "Critical":    adj += 2.5
    elif severity == "High":      adj += 1.5
    elif severity == "Medium":    adj += 0.5
    # Interchange bonus (transfer passengers add to load)
    if is_interchange:            adj += 1.5
    # Off-peak adjustments are smaller
    if time_window in ["midday", "late_night"]:
        adj *= 0.5
    return round(adj, 1)

# ── STEP 4: Generate recommendations per station per window ───
print("Computing frequency recommendations...")

TIME_WINDOWS = ["morning_peak", "evening_peak", "midday", "late_night"]
MAX_TRAINS   = {"1": 20, "2A": 15, "7": 15, "3": 15}  # operational cap

rows = []
for _, st in df.iterrows():
    line = str(st["line"]).strip()
    if line not in CURRENT_FREQ:
        line = "3"

    for window in TIME_WINDOWS:
        current   = CURRENT_FREQ[line][window]
        adj       = compute_adjustment(
            st["lmpi_score"], st["severity_label"],
            bool(st["is_interchange"]), window
        )
        rec       = min(MAX_TRAINS.get(line, 15), round(current + adj, 1))
        delta     = round(rec - current, 1)
        # Headway from recommended frequency
        rec_headway = round(60 / rec, 1) if rec > 0 else 60

        # Impact score — higher delta + higher LMPI = higher impact
        impact = round(
            (delta / MAX_TRAINS.get(line, 15)) * 0.5 +
            (st["lmpi_score"] / 100) * 0.5, 3
        )

        rows.append({
            "station_name":           st["station_name"],
            "line":                   st["line"],
            "role":                   st["role"],
            "is_interchange":         int(st["is_interchange"]),
            "time_window":            window,
            "current_trains_hr":      current,
            "recommended_trains_hr":  rec,
            "delta_trains_hr":        delta,
            "recommended_headway_min":rec_headway,
            "lmpi_score":             st["lmpi_score"],
            "severity_label":         st["severity_label"],
            "intervention_impact":    impact,
        })

df_out = pd.DataFrame(rows)
df_out.sort_values(["lmpi_score","intervention_impact"],
                   ascending=[False, False], inplace=True)

# ── STEP 5: Save ──────────────────────────────────────────────
out_path = os.path.join(DER, "06_frequency_optimization.csv")
df_out.to_csv(out_path, index=False)

# ── STEP 6: Summary ───────────────────────────────────────────
print(f"\n✅ Saved: Data/Derived/06_frequency_optimization.csv")
print(f"   Total rows : {len(df_out)}")
print(f"\n   Average frequency increase by severity (morning peak):")
mp = df_out[df_out["time_window"] == "morning_peak"]
for sev in ["Critical","High","Medium","Low"]:
    subset = mp[mp["severity_label"] == sev]
    if len(subset):
        print(f"   {sev:10s}: +{subset['delta_trains_hr'].mean():.1f} trains/hr avg")

print(f"\n   Top 5 stations needing most frequency increase:")
top = df_out[df_out["time_window"]=="morning_peak"].nlargest(5,"delta_trains_hr")
print(top[["station_name","line","current_trains_hr",
           "recommended_trains_hr","delta_trains_hr",
           "severity_label"]].to_string(index=False))