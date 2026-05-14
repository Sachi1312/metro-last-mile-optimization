# ============================================================
# validate_data.py
# Validates incoming AFCS CSV before monthly update
# Checks: columns, stations, date range, nulls, negatives
# Usage: python Scripts\validate_data.py --input <csv_path>
# ============================================================

import pandas as pd
import numpy as np
import os
import sys
import argparse
from datetime import datetime

BASE = r"C:\Users\parek\Downloads\LY Project"
RAW  = os.path.join(BASE, "Data", "Raw")

# ── Known stations ────────────────────────────────────────────
KNOWN_STATIONS = [
    # Line 7
    "Dahisar (E)","Ovaripada","Rashtriya Udyan","Devipada",
    "Borivali (E)","Magathane","Poisar","Kandivali (E)",
    "Akurli","Kurar","Dindoshi","Goregaon (E)","Jogeshwari (E)","Gundavali",
    # Line 3
    "Aarey JVLR","SEEPZ","MIDC","Marol Naka","CSMIA T2","Sahar Road",
    "CSMIA T1","Santacruz","BKC","Dharavi","Sitaladevi","Dadar",
    "Siddhivinayak","Worli","Acharya Atre Chowk","Mahalaxmi",
    "Mumbai Central","Grant Road","Girgaon","Kalbadevi","CSMT",
    "Hutatma Chowk","Churchgate","Vidhan Bhavan","Nariman Point","Cuffe Parade",
    # Line 2A
    "Dahisar (E) 2A","Anand Nagar","Kandarpada","Mandapeshwar","Eksar",
    "Borivali (W)","Shimpoli","Kandivali (W)","Dahanukarwadi",
    "Valnai-Meeth Chowky","Malad (W)","Lower Malad","Bangur Nagar",
    "Goregaon (W)","Oshiwara","Lower Oshiwara","DN Nagar",
    # Line 1
    "Versova","D.N. Nagar","Azad Nagar","Andheri","WEH",
    "Chakala (JB Nagar)","Airport Road","Marol Naka L1",
    "Saki Naka","Asalpha","Jagruti Nagar","Ghatkopar",
]

REQUIRED_COLS = ["date","station_name","line","footfall"]
VALID_LINES   = ["1","2A","7","3"]

def validate(filepath):
    print("=" * 55)
    print("  AFCS DATA VALIDATION")
    print("=" * 55)
    print(f"\n  File: {os.path.basename(filepath)}")

    errors   = []
    warnings = []
    passed   = []

    # ── Check file exists ─────────────────────────────────────
    if not os.path.exists(filepath):
        print(f"\n  ❌ File not found: {filepath}")
        return False

    # ── Load file ─────────────────────────────────────────────
    try:
        df = pd.read_csv(filepath)
        passed.append(f"File loaded — {len(df):,} rows")
    except Exception as e:
        print(f"\n  ❌ Cannot read file: {e}")
        return False

    # ── Check required columns ────────────────────────────────
    missing_cols = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing_cols:
        errors.append(f"Missing columns: {missing_cols}")
    else:
        passed.append(f"All required columns present: {REQUIRED_COLS}")

    if missing_cols:
        print_results(passed, warnings, errors)
        return False

    # ── Parse dates ───────────────────────────────────────────
    try:
        df["date"] = pd.to_datetime(df["date"])
        passed.append(f"Date range: {df['date'].min().date()} → {df['date'].max().date()}")
    except Exception as e:
        errors.append(f"Cannot parse date column: {e}")

    # ── Check single month ────────────────────────────────────
    if "date" in df.columns and df["date"].dtype != object:
        months = df["date"].dt.to_period("M").nunique()
        if months > 1:
            warnings.append(f"Data spans {months} months — expected 1 month per update")
        else:
            passed.append(f"Single month confirmed: {df['date'].dt.to_period('M').iloc[0]}")

    # ── Check stations ────────────────────────────────────────
    unique_stations = df["station_name"].unique().tolist()
    missing_stations = [s for s in KNOWN_STATIONS if s not in unique_stations]
    extra_stations   = [s for s in unique_stations if s not in KNOWN_STATIONS]

    if missing_stations:
        warnings.append(f"{len(missing_stations)} stations missing from data: {missing_stations[:5]}...")
    else:
        passed.append(f"All {len(KNOWN_STATIONS)} known stations present")

    if extra_stations:
        warnings.append(f"{len(extra_stations)} unknown stations found: {extra_stations}")

    # ── Check lines ───────────────────────────────────────────
    invalid_lines = [l for l in df["line"].astype(str).unique() if l not in VALID_LINES]
    if invalid_lines:
        errors.append(f"Invalid line values: {invalid_lines}")
    else:
        passed.append(f"All line values valid: {df['line'].astype(str).unique().tolist()}")

    # ── Check nulls ───────────────────────────────────────────
    null_counts = df[REQUIRED_COLS].isnull().sum()
    total_nulls = null_counts.sum()
    if total_nulls > 0:
        errors.append(f"Null values found: {null_counts[null_counts>0].to_dict()}")
    else:
        passed.append("No null values in required columns")

    # ── Check negative footfall ───────────────────────────────
    neg_count = (df["footfall"] < 0).sum()
    if neg_count > 0:
        errors.append(f"{neg_count} rows have negative footfall")
    else:
        passed.append("No negative footfall values")

    # ── Check footfall range ──────────────────────────────────
    max_footfall = df["footfall"].max()
    min_footfall = df["footfall"].min()
    avg_footfall = df["footfall"].mean()

    if max_footfall > 500000:
        warnings.append(f"Very high footfall detected: {max_footfall:,} — verify data")
    if avg_footfall < 100:
        warnings.append(f"Very low avg footfall: {avg_footfall:.0f} — verify data")

    passed.append(f"Footfall stats — min: {min_footfall:,}  max: {max_footfall:,}  avg: {avg_footfall:,.0f}")

    # ── Check duplicate rows ──────────────────────────────────
    dupes = df.duplicated(subset=["date","station_name"]).sum()
    if dupes > 0:
        errors.append(f"{dupes} duplicate (date, station) pairs found")
    else:
        passed.append("No duplicate (date, station) pairs")

    # ── Check overlap with existing data ─────────────────────
    existing_path = os.path.join(RAW, "02_historical_ridership_extended.csv")
    if os.path.exists(existing_path):
        df_existing = pd.read_csv(existing_path, usecols=["date"])
        df_existing["date"] = pd.to_datetime(df_existing["date"])
        existing_dates = set(df_existing["date"].dt.date.unique())
        new_dates      = set(df["date"].dt.date.unique())
        overlap        = existing_dates & new_dates
        if overlap:
            errors.append(f"Date overlap with existing data: {sorted(overlap)[:3]}...")
        else:
            passed.append("No date overlap with existing historical data")

    # ── Print results ─────────────────────────────────────────
    print_results(passed, warnings, errors)

    is_valid = len(errors) == 0
    print(f"\n  {'✅ VALIDATION PASSED — safe to run update_monthly.py' if is_valid else '❌ VALIDATION FAILED — fix errors before updating'}")
    return is_valid


def print_results(passed, warnings, errors):
    print(f"\n  {'─'*50}")
    print(f"  CHECKS PASSED ({len(passed)}):")
    for p in passed:
        print(f"  ✅ {p}")

    if warnings:
        print(f"\n  WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  ⚠️  {w}")

    if errors:
        print(f"\n  ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  ❌ {e}")
    print(f"  {'─'*50}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate AFCS data before monthly update")
    parser.add_argument("--input", required=True, help="Path to new AFCS CSV file")
    args = parser.parse_args()
    result = validate(args.input)
    sys.exit(0 if result else 1)