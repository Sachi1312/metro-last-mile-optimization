# ============================================================
# derive_02_temporal.py
# Derives temporal features from IMD calendar + festival dates
# Input  : System date (no CSV needed)
# Output : Data/Derived/05_temporal_features.csv
# ============================================================

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

BASE = r"C:\\Users\\parek\\Downloads\\LY Project"
DER  = os.path.join(BASE, "Data", "Derived")
os.makedirs(DER, exist_ok=True)

# ── STEP 1: Define date range ─────────────────────────────────
# 12 months: Apr 2024 – Mar 2025 (matches AFCS/hourly data)
START = datetime(2024, 4, 1)
END   = datetime(2025, 3, 31)
print(f"Generating temporal features: {START.date()} to {END.date()}")

# ── STEP 2: Real festival dates (Government of India calendar)─
# Source: Official Hindu/Islamic calendar + Maharashtra state holidays
FESTIVALS = {
    "Ganesh Chaturthi": [datetime(2024, 9, 7),  datetime(2025, 8, 27)],
    "Diwali":           [datetime(2024, 11, 1),  datetime(2025, 10, 20)],
    "Eid al-Fitr":      [datetime(2024, 4, 10)],
    "Navratri":         [datetime(2024, 10, 3),  datetime(2025, 9, 22)],
    "New Year":         [datetime(2025, 1, 1),   datetime(2026, 1, 1)],
    "Holi":             [datetime(2025, 3, 14),  datetime(2026, 3, 3)],
    
}

# Public holidays (Government of India declared)
PUBLIC_HOLIDAYS = [
    
    datetime(2024, 4, 14),  # Ambedkar Jayanti
    datetime(2024, 5, 1),   # Maharashtra Day
    datetime(2024, 8, 15),  # Independence Day
    datetime(2024, 10, 2),  # Gandhi Jayanti
    datetime(2024, 10, 12), # Dussehra
    datetime(2024, 11, 1),  # Diwali
    datetime(2024, 11, 15), # Guru Nanak Jayanti
    datetime(2025, 1, 1),   # New Year
    datetime(2025, 1, 26),  # Republic Day
    datetime(2025, 3, 14),  # Holi
    
]

# ── STEP 3: IMD Mumbai monsoon parameters ────────────────────
# Source: IMD historical averages for Mumbai
# Monsoon months: June–September
# Rainfall probability distribution (Mumbai historical)
RAIN_PROB = {
    1:  {"none":0.95,"light":0.04,"moderate":0.01,"heavy":0.00},
    2:  {"none":0.95,"light":0.04,"moderate":0.01,"heavy":0.00},
    3:  {"none":0.93,"light":0.05,"moderate":0.02,"heavy":0.00},
    4:  {"none":0.90,"light":0.07,"moderate":0.03,"heavy":0.00},
    5:  {"none":0.82,"light":0.10,"moderate":0.06,"heavy":0.02},
    6:  {"none":0.15,"light":0.30,"moderate":0.35,"heavy":0.20},  # Monsoon
    7:  {"none":0.10,"light":0.25,"moderate":0.38,"heavy":0.27},  # Peak
    8:  {"none":0.12,"light":0.28,"moderate":0.36,"heavy":0.24},  # Peak
    9:  {"none":0.20,"light":0.32,"moderate":0.30,"heavy":0.18},  # Monsoon
    10: {"none":0.75,"light":0.15,"moderate":0.08,"heavy":0.02},
    11: {"none":0.90,"light":0.07,"moderate":0.03,"heavy":0.00},
    12: {"none":0.93,"light":0.05,"moderate":0.02,"heavy":0.00},
}

# Rainfall mm ranges per intensity (IMD Mumbai)
RAIN_MM = {
    "none":     (0, 0),
    "light":    (1, 15),
    "moderate": (15, 35),
    "heavy":    (35, 80),
}

# Ridership boost from rain (your observed data)
RAIN_BOOST = {
    "none":     0.00,
    "light":    0.065,   # +5-8%
    "moderate": 0.135,   # +12-15%
    "heavy":    0.185,   # +17-20%
}

# ── STEP 4: Helper functions ──────────────────────────────────
def get_festival_info(date):
    min_days = 999
    nearest_fest = "none"
    for name, dates in FESTIVALS.items():
        for fd in dates:
            diff = abs((date - fd).days)
            if diff < min_days:
                min_days = diff
                nearest_fest = name
    is_fest  = 1 if min_days <= 2 else 0
    fest_name = nearest_fest if min_days <= 2 else "none"
    # Boost based on festival importance
    if is_fest:
        if fest_name in ["Ganesh Chaturthi", "Diwali"]:
            boost = np.random.uniform(0.30, 0.40)
        elif fest_name == "New Year":
            boost = np.random.uniform(0.22, 0.30)
        else:
            boost = np.random.uniform(0.12, 0.22)
    else:
        boost = 0.0
    return is_fest, fest_name, min(min_days, 999), round(boost, 3)

def get_rain_info(date):
    month = date.month
    probs = RAIN_PROB[month]
    intensity = np.random.choice(
        list(probs.keys()),
        p=list(probs.values())
    )
    lo, hi = RAIN_MM[intensity]
    mm = round(np.random.uniform(lo, hi), 1) if hi > 0 else 0.0
    boost = RAIN_BOOST[intensity]
    return intensity, mm, round(boost, 3)

def get_peak_type(day_type):
    if day_type == "weekday":
        return "sharp_double"   # 8-11am + 5-9pm
    else:
        return "broad_single"   # 12-9pm

# ── STEP 5: Generate row per day ─────────────────────────────
np.random.seed(42)
rows = []
current = START

while current <= END:
    dow      = current.weekday()           # 0=Mon, 6=Sun
    day_type = "weekend" if dow >= 5 else "weekday"

    is_fest, fest_name, d2f, fest_boost = get_festival_info(current)
    rain_int, rain_mm, rain_boost        = get_rain_info(current)
    is_holiday = int(current in PUBLIC_HOLIDAYS)
    is_monsoon = int(current.month in [6, 7, 8, 9])

    rows.append({
        "date":                  current.strftime("%Y-%m-%d"),
        "day_of_week":           current.strftime("%A"),
        "day_number":            dow,
        "day_type":              day_type,
        "month":                 current.month,
        "month_name":            current.strftime("%B"),
        "quarter":               (current.month - 1) // 3 + 1,
        "is_monsoon":            is_monsoon,
        "monsoon_intensity":     rain_int,
        "rainfall_mm":           rain_mm,
        "rain_ridership_boost":  rain_boost,
        "is_festival":           is_fest,
        "festival_name":         fest_name,
        "days_to_festival":      d2f,
        "festival_boost":        fest_boost,
        "is_public_holiday":     is_holiday,
        "peak_type":             get_peak_type(day_type),
        "morning_peak_start":    8  if day_type == "weekday" else None,
        "morning_peak_end":      11 if day_type == "weekday" else None,
        "evening_peak_start":    17 if day_type == "weekday" else 12,
        "evening_peak_end":      21,
        "total_boost_multiplier": round(1 + fest_boost + rain_boost, 3),
    })

    current += timedelta(days=1)

# ── STEP 6: Save ──────────────────────────────────────────────
df_out = pd.DataFrame(rows)
out_path = os.path.join(DER, "05_temporal_features.csv")
df_out.to_csv(out_path, index=False)

# ── STEP 7: Summary ───────────────────────────────────────────
print(f"\n✅ Saved: Data/Derived/05_temporal_features.csv")
print(f"   Total days     : {len(df_out)}")
print(f"   Weekdays       : {(df_out['day_type']=='weekday').sum()}")
print(f"   Weekends       : {(df_out['day_type']=='weekend').sum()}")
print(f"   Monsoon days   : {df_out['is_monsoon'].sum()}")
print(f"   Festival days  : {df_out['is_festival'].sum()}")
print(f"   Public holidays: {df_out['is_public_holiday'].sum()}")
print(f"\n   Rain Distribution:")
for i in ["none","light","moderate","heavy"]:
    c = (df_out["monsoon_intensity"]==i).sum()
    print(f"   {i:10s}: {c} days")
print(f"\n   Festival Breakdown:")
for f in df_out[df_out["is_festival"]==1]["festival_name"].unique():
    c = (df_out["festival_name"]==f).sum()
    print(f"   {f}: {c} days")