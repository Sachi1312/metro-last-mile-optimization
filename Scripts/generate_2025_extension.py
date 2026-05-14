# ============================================================
# generate_2025_extension.py
# Extends historical ridership from Apr 2025 → Dec 2025
# Using established seasonal patterns from 2019–2025 data
# All synthetic rows clearly flagged: is_synthetic = 1
# Input  : Data/Raw/02_historical_ridership_5yr.csv
#          Data/Raw/01_station_master.csv
# Output : Data/Raw/02_historical_ridership_extended.csv
# ============================================================

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import warnings
warnings.filterwarnings("ignore")

np.random.seed(42)

BASE = r"C:\Users\parek\Downloads\LY Project"
RAW  = os.path.join(BASE, "Data", "Raw")
DER  = os.path.join(BASE, "Data", "Derived")

print("=" * 60)
print("  2025 DATA EXTENSION — Apr 2025 → Dec 2025")
print("=" * 60)

# ── STEP 1: Load existing data ────────────────────────────────
print("\n[1/7] Loading existing historical data...")
df_hist    = pd.read_csv(os.path.join(RAW, "02_historical_ridership_5yr.csv"))
df_station = pd.read_csv(os.path.join(RAW, "01_station_master.csv"))

df_hist["date"] = pd.to_datetime(df_hist["date"])

print(f"  Existing rows    : {len(df_hist):,}")
print(f"  Date range       : {df_hist['date'].min().date()} → {df_hist['date'].max().date()}")
print(f"  Stations         : {df_hist['station_name'].nunique()}")
print(f"  Lines            : {df_hist['line'].unique().tolist()}")

# ── STEP 2: Define extension period ──────────────────────────
print("\n[2/7] Defining extension period...")

EXTENSION_START = datetime(2025, 4, 1)
EXTENSION_END   = datetime(2025, 12, 31)

extension_dates = pd.date_range(EXTENSION_START, EXTENSION_END)
print(f"  Extension period : {EXTENSION_START.date()} → {EXTENSION_END.date()}")
print(f"  Days to generate : {len(extension_dates)}")
print(f"  Rows to generate : {len(extension_dates) * df_station['station_name'].nunique():,}")

# ── STEP 3: Real festival dates for Apr–Dec 2025 ─────────────
print("\n[3/7] Loading 2025 festival calendar...")

FESTIVALS_2025 = {
    "Eid al-Adha":       datetime(2025, 6, 7),
    "Independence Day":  datetime(2025, 8, 15),
    "Ganesh Chaturthi":  datetime(2025, 8, 27),
    "Navratri":          datetime(2025, 9, 22),
    "Dussehra":          datetime(2025, 10, 2),
    "Diwali":            datetime(2025, 10, 20),
    "Guru Nanak":        datetime(2025, 11, 5),
    "Christmas":         datetime(2025, 12, 25),
    "New Year Eve":      datetime(2025, 12, 31),
}

PUBLIC_HOLIDAYS_2025 = [
    datetime(2025, 4, 14),   # Ambedkar Jayanti
    datetime(2025, 5, 1),    # Maharashtra Day
    datetime(2025, 6, 7),    # Eid al-Adha
    datetime(2025, 8, 15),   # Independence Day
    datetime(2025, 8, 27),   # Ganesh Chaturthi
    datetime(2025, 10, 2),   # Gandhi Jayanti / Dussehra
    datetime(2025, 10, 20),  # Diwali
    datetime(2025, 11, 5),   # Guru Nanak Jayanti
    datetime(2025, 12, 25),  # Christmas
]

FESTIVAL_BOOST = {
    "Ganesh Chaturthi": 0.37,
    "Diwali":           0.34,
    "Navratri":         0.18,
    "Eid al-Adha":      0.17,
    "Dussehra":         0.15,
    "New Year Eve":     0.28,
    "Independence Day": 0.12,
    "Guru Nanak":       0.10,
    "Christmas":        0.08,
}

def get_festival_info(date):
    min_days = 999
    nearest  = "none"
    for name, fdate in FESTIVALS_2025.items():
        diff = abs((date - fdate).days)
        if diff < min_days:
            min_days = diff
            nearest  = name
    is_fest   = 1 if min_days <= 2 else 0
    fest_name = nearest if min_days <= 2 else "none"
    boost     = FESTIVAL_BOOST.get(fest_name, 0) if is_fest else 0
    return is_fest, fest_name, min_days, round(boost, 3)

# ── STEP 4: IMD monsoon parameters for 2025 ──────────────────
print("\n[4/7] Setting monsoon parameters...")

# Mumbai monsoon: June–September
# Rainfall probability by month (IMD historical)
RAIN_PROB_2025 = {
    4:  {"none":0.92,"light":0.06,"moderate":0.02,"heavy":0.00},
    5:  {"none":0.82,"light":0.10,"moderate":0.06,"heavy":0.02},
    6:  {"none":0.15,"light":0.30,"moderate":0.35,"heavy":0.20},
    7:  {"none":0.10,"light":0.25,"moderate":0.38,"heavy":0.27},
    8:  {"none":0.12,"light":0.28,"moderate":0.36,"heavy":0.24},
    9:  {"none":0.20,"light":0.32,"moderate":0.30,"heavy":0.18},
    10: {"none":0.75,"light":0.15,"moderate":0.08,"heavy":0.02},
    11: {"none":0.90,"light":0.07,"moderate":0.03,"heavy":0.00},
    12: {"none":0.93,"light":0.05,"moderate":0.02,"heavy":0.00},
}

RAIN_MM = {
    "none":0,"light":np.random.uniform(2,15),
    "moderate":np.random.uniform(15,35),"heavy":np.random.uniform(35,80)
}

RAIN_BOOST = {"none":0.0,"light":0.065,"moderate":0.135,"heavy":0.185}

def get_rain_info(date):
    month = date.month
    probs = RAIN_PROB_2025.get(month, {"none":1.0,"light":0,"moderate":0,"heavy":0})
    intensity = np.random.choice(list(probs.keys()), p=list(probs.values()))
    lo_hi = {"none":(0,0),"light":(2,15),"moderate":(15,35),"heavy":(35,80)}
    lo, hi = lo_hi[intensity]
    mm = round(np.random.uniform(lo, hi), 1) if hi > 0 else 0.0
    return intensity, mm, round(RAIN_BOOST[intensity], 3)

# ── STEP 5: Line growth rates for 2025 ───────────────────────
print("\n[5/7] Applying 2025 growth rates...")

# Based on published MMRDA data + growth trajectory
# Line 1: saturated, minimal growth
# Lines 2A & 7: still growing but slowing
# Line 3: rapid growth as new line matures

LINE_2025_BASE = {
    "1":  410000,    # ~4.1L/day base (saturated)
    "2A": 310000,    # ~3.1L/day (growing)
    "7":  300000,    # ~3.0L/day (growing)
    "3":  180000,    # ~1.8L/day (new, maturing fast)
}

# Monthly growth factor for Apr–Dec 2025
# Line 3 grows fastest (new line gaining ridership)
MONTHLY_GROWTH = {
    "1":  {4:1.00,5:1.00,6:1.02,7:1.01,8:1.01,9:1.01,10:1.02,11:1.01,12:1.01},
    "2A": {4:1.00,5:1.02,6:1.04,7:1.03,8:1.03,9:1.02,10:1.03,11:1.02,12:1.02},
    "7":  {4:1.00,5:1.02,6:1.04,7:1.03,8:1.03,9:1.02,10:1.03,11:1.02,12:1.02},
    "3":  {4:1.00,5:1.05,6:1.08,7:1.07,8:1.08,9:1.07,10:1.09,11:1.08,12:1.10},
}

# Station role share (same as generator)
ROLE_SHARE = {
    "terminus_interchange":0.08,"remote":0.012,
    "residential_high":0.07,"residential_mid":0.045,
    "office_heavy":0.065,"interchange":0.09,
    "airport":0.04,"office_premium":0.085,
    "interchange_rail":0.11,"religious_tourist":0.055,
    "office_mid":0.060,"commercial":0.070,
    "office_south":0.048,"shopping_hub":0.075,"airport_adj":0.035,
}

# Weekday vs weekend multiplier
WD_MULT = {"weekday": 1.0, "weekend": 0.88}

# ── STEP 6: Generate extension rows ──────────────────────────
print("\n[6/7] Generating extension rows...")

rows = []
total_dates = len(extension_dates)

for idx, date in enumerate(extension_dates):
    if idx % 30 == 0:
        print(f"  Processing {date.date()} ({idx}/{total_dates})...")

    dow      = date.dayofweek
    day_type = "weekend" if dow >= 5 else "weekday"
    wd_mult  = WD_MULT[day_type]
    month    = date.month

    is_fest, fest_name, d2f, fest_boost = get_festival_info(date.to_pydatetime())
    rain_int, rain_mm, rain_boost       = get_rain_info(date.to_pydatetime())
    is_holiday = int(date.to_pydatetime() in PUBLIC_HOLIDAYS_2025)

    for _, st in df_station.iterrows():
        line = str(st["line"]).strip()
        if line not in LINE_2025_BASE:
            continue

        base       = LINE_2025_BASE[line]
        growth     = MONTHLY_GROWTH[line].get(month, 1.0)
        share      = ROLE_SHARE.get(st["role"], 0.05)

        # Rain boost only meaningful for elevated lines
        eff_rain = rain_boost if st["is_elevated"] else rain_boost * 0.4

        # Total multiplier
        total_mult = 1 + fest_boost + eff_rain

        # Base footfall with noise
        noise    = np.random.normal(1.0, 0.055)
        footfall = max(0, int(base * growth * share * wd_mult * total_mult * noise))

        rows.append({
            "date":              date.strftime("%Y-%m-%d"),
            "station_name":      st["station_name"],
            "line":              st["line"],
            "day_type":          day_type,
            "footfall":          footfall,
            "is_festival":       is_fest,
            "festival_name":     fest_name,
            "days_to_festival":  min(d2f, 999),
            "rain_intensity":    rain_int,
            "rainfall_mm":       rain_mm,
            "rain_boost":        eff_rain,
            "festival_boost":    fest_boost,
            "is_synthetic":      1,           # clearly flagged
            "is_covid":          0,
        })

df_ext = pd.DataFrame(rows)
print(f"\n  Extension rows generated : {len(df_ext):,}")

# ── STEP 7: Merge + save ──────────────────────────────────────
print("\n[7/7] Merging with existing data and saving...")

# Add is_synthetic flag to original data
df_hist["is_synthetic"] = 0

# Ensure same columns
for col in df_ext.columns:
    if col not in df_hist.columns:
        df_hist[col] = 0

df_hist = df_hist[df_ext.columns]

# Merge
df_combined = pd.concat([df_hist, df_ext], ignore_index=True)
df_combined = df_combined.sort_values(["station_name","date"]).reset_index(drop=True)

# Verify no overlap
df_combined["date"] = pd.to_datetime(df_combined["date"])
overlap = df_combined[
    (df_combined["date"] >= pd.Timestamp("2025-04-01")) &
    (df_combined["is_synthetic"] == 0)
]
print(f"  Overlap check (should be 0): {len(overlap)} rows")

# Save
out_path = os.path.join(RAW, "02_historical_ridership_extended.csv")
df_combined.to_csv(out_path, index=False)

# ── Final summary ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("  2025 EXTENSION COMPLETE")
print("=" * 60)
print(f"\n  Original rows    : {len(df_hist):,}")
print(f"  Extension rows   : {len(df_ext):,}")
print(f"  Combined rows    : {len(df_combined):,}")
print(f"  Date range       : {df_combined['date'].min()} → {df_combined['date'].max()}")
print(f"  Stations         : {df_combined['station_name'].nunique()}")
print(f"  Synthetic rows   : {df_combined['is_synthetic'].sum():,} (flagged)")
print(f"  Real rows        : {(df_combined['is_synthetic']==0).sum():,}")

print(f"\n  2025 Extension Footfall Summary:")
ext_only = df_ext.groupby("line")["footfall"].agg(["mean","sum"]).reset_index()
for _, row in ext_only.iterrows():
    print(f"  Line {row['line']:<4} → avg daily/station: {row['mean']:>8,.0f}  "
          f"total: {row['sum']:>12,.0f}")

print(f"\n  Festival days in extension: {df_ext['is_festival'].sum()}")
print(f"  Monsoon days in extension : {df_ext[df_ext['rain_intensity']!='none']['date'].nunique()}")

print(f"\n  Saved:")
print(f"  └── Data/Raw/02_historical_ridership_extended.csv")
print(f"\n  Next step: Run generate_2026_forecast.py")