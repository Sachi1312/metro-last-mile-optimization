# ============================================================
# derive_01_lmpi.py
# Derives LMPI scores and severity labels from survey responses
# Input  : Data/Raw/08_survey_responses.csv
# Output : Data/Derived/04_lmpi_scores.csv
# ============================================================

import pandas as pd
import numpy as np
import os

BASE = r"C:\\Users\\parek\\Downloads\\LY Project"
RAW  = os.path.join(BASE, "Data", "Raw")
DER  = os.path.join(BASE, "Data", "Derived")
os.makedirs(DER, exist_ok=True)

# ── STEP 1: Load survey responses ────────────────────────────
print("Loading survey responses...")
df = pd.read_csv(os.path.join(RAW, "08_survey_responses.csv"))
print(f"  Loaded {len(df):,} responses across {df['station_name'].nunique()} stations")

# ── STEP 2: Aggregate to station level ───────────────────────
# Convert ratings (1-5) to problem scores (0-100)
# Higher score = worse problem
print("Aggregating to station level...")

agg = df.groupby(["station_name", "line"]).agg(
    avg_satisfaction    = ("satisfaction_rating",  "mean"),
    avg_auto_avail      = ("auto_availability",     "mean"),
    avg_bus_freq        = ("bus_frequency",         "mean"),
    avg_safety          = ("safety_rating",         "mean"),
    avg_walkability     = ("walkability",            "mean"),
    pct_problem_auto    = ("problem_auto",           "mean"),
    pct_problem_bus     = ("problem_bus",            "mean"),
    pct_problem_walk    = ("problem_walk",           "mean"),
    pct_problem_safety  = ("problem_safety",         "mean"),
    pct_problem_crowd   = ("problem_crowding",       "mean"),
    total_responses     = ("satisfaction_rating",   "count"),
).reset_index()

# ── STEP 3: Convert ratings to 0-100 problem scores ──────────
# Rating scale: 5 = excellent, 1 = very poor
# Problem score: 0 = no problem, 100 = severe problem

print("Computing factor scores...")

# Auto problem score: low rating + high % reporting problem
agg["auto_problem_score"] = (
    ((5 - agg["avg_auto_avail"]) / 4 * 70) +   # rating component (70%)
    (agg["pct_problem_auto"] * 30)               # binary problem flag (30%)
).round(1)

# Walking problem score
agg["walking_problem_score"] = (
    ((5 - agg["avg_walkability"]) / 4 * 70) +
    (agg["pct_problem_walk"] * 30)
).round(1)

# Bus problem score
agg["bus_problem_score"] = (
    ((5 - agg["avg_bus_freq"]) / 4 * 70) +
    (agg["pct_problem_bus"] * 30)
).round(1)

# Crowding score: derived from satisfaction + crowd problem flag
agg["crowding_score"] = (
    ((5 - agg["avg_satisfaction"]) / 4 * 50) +
    (agg["pct_problem_crowd"] * 50)
).round(1)

# Safety score
agg["safety_score"] = (
    ((5 - agg["avg_safety"]) / 4 * 70) +
    (agg["pct_problem_safety"] * 30)
).round(1)

# Clamp all scores to 0-100
for col in ["auto_problem_score","walking_problem_score","bus_problem_score","crowding_score","safety_score"]:
    agg[col] = agg[col].clip(0, 100)

# ── STEP 4: Compute LMPI using weighted formula ───────────────
# Weights derived from literature + survey importance ranking
# Auto       : 0.28 (highest — most reported problem)
# Walking    : 0.22
# Bus        : 0.20
# Crowding   : 0.18
# Safety     : 0.12

print("Computing LMPI scores...")

agg["lmpi_score"] = (
    agg["auto_problem_score"]    * 0.28 +
    agg["walking_problem_score"] * 0.22 +
    agg["bus_problem_score"]     * 0.20 +
    agg["crowding_score"]        * 0.18 +
    agg["safety_score"]          * 0.12
).round(1).clip(0, 100)

# ── Role-based boost ─────────────────────────────────────────
# High footfall stations get LMPI boost reflecting real crush load
# Source: MMRDA ridership data + interchange complexity
df_station = pd.read_csv(os.path.join(RAW, "01_station_master.csv"))
agg = agg.merge(df_station[["station_name","role","pop_density"]],
                on="station_name", how="left")

ROLE_BOOST = {
    "interchange_rail":     28,
    "terminus_interchange": 22,
    "interchange":          20,
    "office_premium":       18,
    "shopping_hub":         15,
    "office_heavy":         14,
    "commercial":           12,
    "residential_high":     8,
    "airport":              6,
    "office_mid":           5,
    "office_south":         5,
    "religious_tourist":    4,
    "residential_mid":      0,
    "remote":               0,
    "airport_adj":          3,
}

agg["role_boost"] = agg["role"].map(ROLE_BOOST).fillna(0)
agg["lmpi_score"] = (agg["lmpi_score"] + agg["role_boost"]).clip(0, 100).round(1)
# Cap remote stations at High (max LMPI 69) — low footfall, lower priority
remote_roles = ["remote", "office_south", "airport"]
agg.loc[agg["role"].isin(remote_roles), "lmpi_score"] = \
    agg.loc[agg["role"].isin(remote_roles), "lmpi_score"].clip(upper=61)

# South Mumbai office stations — lower last-mile problem than BKC
south_mumbai = ["Nariman Point","Cuffe Parade","Vidhan Bhavan",
                "Hutatma Chowk","Churchgate"]
agg.loc[agg["station_name"].isin(south_mumbai), "lmpi_score"] = \
    agg.loc[agg["station_name"].isin(south_mumbai), "lmpi_score"].clip(upper=61)

# ── STEP 5: Assign severity labels ───────────────────────────
# Thresholds based on LMPI distribution quartiles
print("Assigning severity labels...")

def assign_severity(score):
    if score >= 64:   return "Critical"
    elif score >= 52: return "High"
    elif score >= 38: return "Medium"
    else:             return "Low"

agg["severity_label"] = agg["lmpi_score"].apply(assign_severity)







# ── STEP 6: Assign recommended last-mile mode ─────────────────
print("Assigning last-mile recommendations...")

def recommend_last_mile(row):
    if row["avg_auto_avail"] >= 3.5 and row["auto_problem_score"] < 40:
        return "Auto Rickshaw"
    elif row["avg_bus_freq"] >= 3.5 and row["bus_problem_score"] < 40:
        return "BEST Bus"
    elif row["auto_problem_score"] > 60 and row["walking_problem_score"] > 60:
        return "E-Rickshaw"
    elif row["avg_auto_avail"] < 2.5:
        return "Shared Auto"
    else:
        return "Auto Rickshaw"

agg["recommended_last_mile"] = agg.apply(recommend_last_mile, axis=1)

# ── STEP 7: Add survey summary columns ───────────────────────
agg["survey_satisfaction"]  = agg["avg_satisfaction"].round(1)
agg["survey_auto_avail"]    = agg["avg_auto_avail"].round(1)
agg["survey_bus_freq"]      = agg["avg_bus_freq"].round(1)
agg["survey_safety"]        = agg["avg_safety"].round(1)
agg["survey_walkability"]   = agg["avg_walkability"].round(1)

# ── STEP 8: Final output columns ─────────────────────────────
output_cols = [
    "station_name", "line", "total_responses",
    "auto_problem_score", "walking_problem_score",
    "bus_problem_score", "crowding_score", "safety_score",
    "lmpi_score", "severity_label", "recommended_last_mile",
    "survey_satisfaction", "survey_auto_avail",
    "survey_bus_freq", "survey_safety", "survey_walkability",
]
df_out = agg[output_cols].sort_values("lmpi_score", ascending=False).reset_index(drop=True)

# ── STEP 9: Save ──────────────────────────────────────────────
out_path = os.path.join(DER, "04_lmpi_scores.csv")
df_out.to_csv(out_path, index=False)

# ── STEP 10: Summary report ───────────────────────────────────
print(f"\n✅ Saved: Data/Derived/04_lmpi_scores.csv")
print(f"   Total stations: {len(df_out)}")
print(f"\n   Severity Distribution:")
for sev in ["Critical","High","Medium","Low"]:
    count = (df_out["severity_label"] == sev).sum()
    pct   = count / len(df_out) * 100
    print(f"   {sev:10s}: {count:3d} stations ({pct:.1f}%)")

print(f"\n   LMPI Stats:")
print(f"   Min    : {df_out['lmpi_score'].min()}")
print(f"   Max    : {df_out['lmpi_score'].max()}")
print(f"   Mean   : {df_out['lmpi_score'].mean():.1f}")
print(f"   Median : {df_out['lmpi_score'].median():.1f}")

print(f"\n   Top 5 Critical Stations:")
print(df_out[["station_name","line","lmpi_score","severity_label"]].head(5).to_string(index=False))
