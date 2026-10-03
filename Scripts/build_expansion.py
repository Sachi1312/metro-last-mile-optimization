# ============================================================
# build_expansion.py
# Faculty-review extension. Does not modify the original 69-station
# pipeline outputs.
#
# Writes Outputs/Expansion/bundle.json and a few plots.
# Delhi and future-Mumbai rows are synthetic scenario data.
# ============================================================

import hashlib
import json
import os
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    silhouette_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict, learning_curve
from sklearn.preprocessing import LabelEncoder, StandardScaler
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "Data", "Raw")
DER = os.path.join(BASE, "Data", "Derived")
OUT = os.path.join(BASE, "Outputs", "Expansion")
PLOTS = os.path.join(BASE, "Outputs", "Plots")
os.makedirs(OUT, exist_ok=True)
os.makedirs(PLOTS, exist_ok=True)

ROLE_BOOST = {
    "interchange_rail": 28,
    "terminus_interchange": 22,
    "interchange": 20,
    "office_premium": 18,
    "shopping_hub": 15,
    "office_heavy": 14,
    "commercial": 12,
    "residential_high": 8,
    "airport": 6,
    "office_mid": 5,
    "office_south": 5,
    "religious_tourist": 4,
    "residential_mid": 0,
    "remote": 0,
    "airport_adj": 3,
}

# Typical physical profile for a role. Used only when a station has no survey.
ROLE_PROFILE = {
    "terminus_interchange": (0.72, 0.55, 0.68, 400),
    "interchange": (0.82, 0.60, 0.72, 330),
    "interchange_rail": (0.90, 0.70, 0.80, 300),
    "office_premium": (0.80, 0.42, 0.55, 520),
    "office_heavy": (0.62, 0.38, 0.48, 500),
    "office_mid": (0.68, 0.55, 0.60, 440),
    "office_south": (0.60, 0.50, 0.55, 470),
    "residential_high": (0.78, 0.65, 0.70, 370),
    "residential_mid": (0.55, 0.45, 0.50, 490),
    "remote": (0.28, 0.22, 0.28, 720),
    "airport": (0.22, 0.78, 0.55, 310),
    "airport_adj": (0.40, 0.70, 0.50, 380),
    "shopping_hub": (0.80, 0.68, 0.74, 360),
    "commercial": (0.78, 0.60, 0.68, 400),
    "religious_tourist": (0.70, 0.62, 0.60, 410),
}

MUMBAI_FESTIVALS = [
    ("Ganesh Chaturthi", 0.38),
    ("Diwali", 0.34),
    ("Navratri", 0.22),
    ("Eid", 0.18),
    ("Dussehra", 0.16),
    ("Holi", 0.15),
    ("Janmashtami", 0.14),
    ("Gudi Padwa", 0.12),
    ("Christmas", 0.08),
    ("Independence Day", 0.06),
    ("Republic Day", 0.05),
]

DELHI_FESTIVALS = [
    ("Diwali", 0.32),
    ("Holi", 0.28),
    ("Dussehra", 0.18),
    ("Eid", 0.16),
    ("Janmashtami", 0.12),
    ("Raksha Bandhan", 0.10),
    ("Republic Day", 0.08),
    ("Independence Day", 0.08),
]

# Published 2031 daily ridership (MMRDA project pages). Line 6's page did not
# quote a total, so it is scaled from Line 2B riders-per-km.
LINE_RIDERSHIP_2031 = {
    "2B": 1_050_000,
    "4": 1_213_000,
    "5": 302_500,
    "6": int(round(1_050_000 / 23.643 * 15.31)),
    "7A": None,  # combined with line 9 below
    "9": 1_112_000,
}

OPENING_FACTOR = 0.45  # 2031 planning total is not opening-day demand

# name, line, role, interchange, interchange_with, elevated
FUTURE_MUMBAI = [
    # Line 2B — MMRDA list of 20 stations. DN Nagar itself is already in the 69.
    ("ESIC Nagar", "2B", "residential_mid", False, "none", True),
    ("Prem Nagar", "2B", "residential_mid", False, "none", True),
    ("Indira Nagar", "2B", "residential_mid", False, "none", True),
    ("Nanavati Hospital", "2B", "commercial", False, "none", True),
    ("Khira Nagar", "2B", "residential_high", False, "none", True),
    ("Saraswat Nagar", "2B", "residential_mid", False, "none", True),
    ("National College", "2B", "commercial", False, "none", True),
    ("Bandra Metro", "2B", "interchange_rail", True, "railway", True),
    ("Income Tax Office", "2B", "interchange", True, "3", True),
    ("ILFS", "2B", "office_mid", False, "none", True),
    ("MTNL Metro", "2B", "office_mid", False, "none", True),
    ("SG Barve Marg", "2B", "residential_mid", False, "none", True),
    ("Kurla (E)", "2B", "interchange_rail", True, "4", True),
    ("EEH", "2B", "interchange", True, "eastern express", True),
    ("Chembur", "2B", "interchange_rail", True, "monorail", True),
    ("Diamond Garden", "2B", "residential_mid", False, "none", True),
    ("Shivaji Chowk", "2B", "residential_mid", False, "none", True),
    ("BSNL Metro", "2B", "residential_mid", False, "none", True),
    ("Mankhurd", "2B", "interchange_rail", True, "railway", True),
    ("Mandale Metro", "2B", "terminus_interchange", True, "depot", True),
    # Line 4 — MMRDA list of 30 stations
    ("Bhakti Park Metro", "4", "residential_mid", False, "none", True),
    ("Wadala TT", "4", "interchange_rail", True, "monorail", True),
    ("Anik Nagar Bus Depot", "4", "residential_mid", False, "none", True),
    ("Siddharth Colony", "4", "interchange", True, "2B", True),
    ("Garodia Nagar", "4", "residential_mid", False, "none", True),
    ("Pant Nagar", "4", "residential_high", False, "none", True),
    ("Laxmi Nagar", "4", "interchange", True, "1", True),
    ("Shreyes Cinema", "4", "shopping_hub", False, "none", True),
    ("Godrej Company", "4", "office_heavy", False, "none", True),
    ("Vikhroli Metro", "4", "interchange_rail", True, "railway", True),
    ("Surya Nagar", "4", "residential_mid", False, "none", True),
    ("Gandhi Nagar", "4", "interchange", True, "6", True),
    ("Naval Housing", "4", "residential_mid", False, "none", True),
    ("Bhandup Mahapalika", "4", "commercial", False, "none", True),
    ("Bhandup Metro", "4", "residential_high", False, "none", True),
    ("Shangrila", "4", "residential_mid", False, "none", True),
    ("Sonapur", "4", "residential_mid", False, "none", True),
    ("Mulund Fire Station", "4", "residential_mid", False, "none", True),
    ("Mulund Naka", "4", "commercial", False, "none", True),
    ("Thane Teen Haath Naka", "4", "commercial", False, "none", True),
    ("RTO Thane", "4", "office_mid", False, "none", True),
    ("Mahapalika Marg", "4", "office_mid", False, "none", True),
    ("Cadbury Junction", "4", "office_heavy", False, "none", True),
    ("Majiwada", "4", "residential_high", False, "none", True),
    ("Kapurbawdi", "4", "interchange", True, "5", True),
    ("Manpada", "4", "residential_mid", False, "none", True),
    ("Tikuji-Ni-Wadi", "4", "residential_mid", False, "none", True),
    ("Dongari Pada", "4", "residential_mid", False, "none", True),
    ("Vijay Garden", "4", "residential_mid", False, "none", True),
    ("Kasarvadavali", "4", "terminus_interchange", True, "4A", True),
    # Line 5 — MMRDA list. Meets Line 4 at Kapurbawdi, not the original 69.
    ("Balkum Naka", "5", "residential_mid", False, "none", True),
    ("Kasheli", "5", "residential_mid", False, "none", True),
    ("Kalher", "5", "residential_mid", False, "none", True),
    ("Purna", "5", "residential_mid", False, "none", True),
    ("Anjurphata", "5", "commercial", False, "none", True),
    ("Dhamankar Naka", "5", "commercial", False, "none", True),
    ("Bhiwandi", "5", "commercial", False, "none", True),
    ("Gopal Nagar", "5", "residential_mid", False, "none", True),
    ("Temghar", "5", "residential_mid", False, "none", True),
    ("Rajnouli", "5", "remote", False, "none", True),
    ("Gove Gaon", "5", "remote", False, "none", True),
    ("Kon Gaon", "5", "remote", False, "none", True),
    ("Lal Chowki", "5", "residential_mid", False, "none", True),
    ("Kalyan Station", "5", "interchange_rail", True, "railway", True),
    ("Kalyan APMC", "5", "terminus_interchange", True, "railway", True),
    # Line 6 — MMRDA list of 13
    ("Swami Samarth Nagar", "6", "residential_high", False, "none", True),
    ("Adarsh Nagar", "6", "interchange", True, "2A", True),
    ("Jogeshwari (W)", "6", "interchange_rail", True, "railway", True),
    ("JVLR", "6", "interchange", True, "7", True),
    ("Shyam Nagar", "6", "residential_mid", False, "none", True),
    ("Maha Kali Caves", "6", "religious_tourist", False, "none", True),
    ("SEEPZ Village", "6", "interchange", True, "3", True),
    ("Saki Vihar Road", "6", "office_heavy", False, "none", True),
    ("Rambaug", "6", "residential_mid", False, "none", True),
    ("Powai Lake", "6", "residential_high", False, "none", True),
    ("IIT Powai", "6", "office_mid", False, "none", True),
    ("Kanjur Marg (W)", "6", "interchange", True, "4", True),
    ("Vikhroli (EEH)", "6", "interchange_rail", True, "railway", True),
    # Line 9 — Dahisar (E) to Mira-Bhayander. Dahisar itself is already in the 69.
    ("Pandhurang Wadi", "9", "residential_mid", False, "none", True),
    ("Miragaon", "9", "residential_mid", False, "none", True),
    ("Kashigaon", "9", "residential_mid", False, "none", True),
    ("Sai Baba Nagar", "9", "residential_mid", False, "none", True),
    ("Meditiya Nagar", "9", "residential_mid", False, "none", True),
    ("Shahid Bhagat Singh Garden", "9", "residential_mid", False, "none", True),
    ("Subhash Chandra Bose Stadium", "9", "terminus_interchange", True, "none", True),
    # Line 7A — Andheri (E) to CSIA. Andheri itself is already in the 69.
    ("Airport Colony", "7A", "airport_adj", False, "none", True),
    ("CSIA", "7A", "airport", True, "3", False),
]

# Survey name → app station name (same physical stop, dual-line rows).
DELHI_NAME_MAP = {
    "Kashmere Gate 2": "Kashmere Gate Yellow",
    "Rajiv Chowk 3": "Rajiv Chowk Blue",
    "Shaheed Sthal (New Bus Adda)": "Shaheed Sthal",
}
# 3 = Blue main, 4 = Blue branch (Vaishali) — both map to Blue in the app.
DELHI_LINE_MAP = {
    1: "Red", 2: "Yellow", 3: "Blue", 4: "Blue",
    "1": "Red", "2": "Yellow", "3": "Blue", "4": "Blue",
}

# Bounded Delhi set: selected Red / Yellow / Blue stations (50).
# name, line, role, interchange, interchange_with, elevated
DELHI = [
    ("Rithala", "Red", "terminus_interchange", True, "none", True),
    ("Rohini West", "Red", "residential_high", False, "none", True),
    ("Rohini East", "Red", "residential_high", False, "none", True),
    ("Pitampura", "Red", "residential_high", False, "none", True),
    ("Netaji Subhash Place", "Red", "interchange", True, "Pink", True),
    ("Inderlok", "Red", "interchange", True, "Green", True),
    ("Kashmere Gate", "Red", "interchange_rail", True, "Yellow", True),
    ("Tis Hazari", "Red", "commercial", False, "none", True),
    ("Shastri Park", "Red", "residential_mid", False, "none", False),
    ("Seelampur", "Red", "residential_high", False, "none", False),
    ("Welcome", "Red", "interchange", True, "Pink", False),
    ("Shahdara", "Red", "interchange_rail", True, "railway", False),
    ("Dilshad Garden", "Red", "residential_mid", False, "none", True),
    ("Shaheed Sthal", "Red", "terminus_interchange", True, "none", True),
    ("Samaypur Badli", "Yellow", "terminus_interchange", True, "none", True),
    ("Azadpur", "Yellow", "interchange", True, "Pink", True),
    ("Model Town", "Yellow", "residential_high", False, "none", True),
    ("Vishwavidyalaya", "Yellow", "office_mid", False, "none", False),
    ("Civil Lines", "Yellow", "residential_mid", False, "none", False),
    ("Kashmere Gate Yellow", "Yellow", "interchange_rail", True, "Red", False),
    ("Chandni Chowk", "Yellow", "commercial", False, "none", False),
    ("New Delhi", "Yellow", "interchange_rail", True, "Airport Express", False),
    ("Rajiv Chowk", "Yellow", "interchange", True, "Blue", False),
    ("Patel Chowk", "Yellow", "office_mid", False, "none", False),
    ("Central Secretariat", "Yellow", "interchange", True, "Violet", False),
    ("INA", "Yellow", "interchange", True, "Pink", False),
    ("AIIMS", "Yellow", "commercial", False, "none", False),
    ("Hauz Khas", "Yellow", "interchange", True, "Magenta", False),
    ("Malviya Nagar", "Yellow", "residential_high", False, "none", False),
    ("Saket", "Yellow", "shopping_hub", False, "none", True),
    ("Qutab Minar", "Yellow", "religious_tourist", False, "none", True),
    ("Sikanderpur", "Yellow", "interchange", True, "Rapid Metro", True),
    ("Millennium City Centre", "Yellow", "terminus_interchange", True, "none", True),
    ("Dwarka Sector 21", "Blue", "interchange", True, "Airport Express", True),
    ("Dwarka", "Blue", "interchange", True, "Grey", True),
    ("Janakpuri West", "Blue", "interchange", True, "Magenta", True),
    ("Rajouri Garden", "Blue", "interchange", True, "Pink", True),
    ("Kirti Nagar", "Blue", "interchange", True, "Green", True),
    ("Karol Bagh", "Blue", "shopping_hub", False, "none", False),
    ("Rajiv Chowk Blue", "Blue", "interchange", True, "Yellow", False),
    ("Mandi House", "Blue", "interchange", True, "Violet", False),
    ("Yamuna Bank", "Blue", "interchange", True, "Blue branch", True),
    ("Akshardham", "Blue", "religious_tourist", False, "none", True),
    ("Mayur Vihar-I", "Blue", "interchange", True, "Pink", True),
    ("Botanical Garden", "Blue", "interchange", True, "Magenta", True),
    ("Noida City Centre", "Blue", "office_heavy", False, "none", True),
    ("Noida Electronic City", "Blue", "terminus_interchange", True, "none", True),
    ("Karkarduma", "Blue", "interchange", True, "Pink", True),
    ("Anand Vihar", "Blue", "interchange_rail", True, "railway", True),
    ("Vaishali", "Blue", "terminus_interchange", True, "none", True),
]

# New-station daily riders that transfer onto an existing station.
# share is the middle case. Low and high are 0.5x and 1.5x this share.
# Sources: MMRDA interchange notes (Line 2B at DN Nagar and ITO/Line 3,
# Line 4 at Ghatkopar, Line 6 at JVLR/Line 7 and Aarey/Line 3 and Line 2A,
# Line 9 at Dahisar, Line 7A at Andheri and CSIA).
TRANSFER_LINKS = [
    ("ESIC Nagar", "D.N. Nagar", 0.20, "Line 2B meets Line 1 at D.N. Nagar"),
    ("Income Tax Office", "BKC", 0.20, "MMRDA lists an ITO junction with Line 3"),
    ("Laxmi Nagar", "Ghatkopar", 0.20, "Line 4 meets Line 1 at Ghatkopar"),
    ("JVLR", "Jogeshwari (E)", 0.20, "MMRDA lists Line 6 interchange with Line 7 at JVLR"),
    ("SEEPZ Village", "Aarey JVLR", 0.15, "MMRDA lists Line 6 interchange with Line 3 at Aarey"),
    ("Adarsh Nagar", "Oshiwara", 0.15, "MMRDA lists Line 6 interchange with Line 2A near Infinity Mall"),
    ("Airport Colony", "Andheri", 0.25, "Line 7A leaves Andheri toward the airport"),
    ("CSIA", "CSMIA T2", 0.30, "Line 7A airport station meets Line 3 at the airport"),
    ("Pandhurang Wadi", "Dahisar (E)", 0.25, "Line 9 is the extension of Line 7 beyond Dahisar"),
]

# A new airport link can pull some Line 1 airport-edge trips off Airport Road.
DIVERSION = [
    ("Airport Road", 0.08, "Some airport trips can use Line 7A instead of Line 1 at Airport Road"),
]


def jitter(name, scale):
    h = int(hashlib.md5(name.encode()).hexdigest()[:8], 16)
    return ((h % 1000) / 999 - 0.5) * 2 * scale


def station_row(name, line, role, interchange, ixwith, elevated, city, network):
    pop, auto, bus, walk = ROLE_PROFILE[role]
    pop = float(np.clip(pop + jitter(name, 0.04), 0.1, 0.98))
    auto = float(np.clip(auto + jitter(name + "a", 0.05), 0.1, 0.95))
    bus = float(np.clip(bus + jitter(name + "b", 0.05), 0.1, 0.95))
    walk = int(np.clip(walk + jitter(name + "w", 40), 250, 900))
    return {
        "station_name": name,
        "line": line,
        "role": role,
        "is_interchange": bool(interchange),
        "interchange_with": ixwith,
        "is_elevated": bool(elevated),
        "pop_density": round(pop, 3),
        "auto_supply_score": round(auto, 3),
        "bus_connectivity_score": round(bus, 3),
        "walk_dist_m": walk,
        "city": city,
        "network": network,
        "is_synthetic": True,
    }


def assign_severity(score):
    if score >= 64:
        return "Critical"
    if score >= 52:
        return "High"
    if score >= 38:
        return "Medium"
    return "Low"


def lmpi_from_facts(row):
    """Display index only. These scores are not model inputs."""
    auto_p = round((1 - row["auto_supply_score"]) * 100, 1)
    bus_p = round((1 - row["bus_connectivity_score"]) * 100, 1)
    walk_p = round(np.clip((row["walk_dist_m"] - 250) / 650 * 100, 0, 100), 1)
    crowd = round(np.clip(row["pop_density"] * 70 + (18 if row["is_interchange"] else 0), 0, 100), 1)
    safety = round(np.clip((1 - row["bus_connectivity_score"]) * 40 + (30 if row["role"] == "remote" else 10), 0, 100), 1)
    score = (
        auto_p * 0.28 + walk_p * 0.22 + bus_p * 0.20 + crowd * 0.18 + safety * 0.12
        + ROLE_BOOST.get(row["role"], 0)
    )
    score = float(np.clip(round(score, 1), 0, 100))
    return {
        "auto_problem_score": auto_p,
        "walking_problem_score": walk_p,
        "bus_problem_score": bus_p,
        "crowding_score": crowd,
        "safety_score": safety,
        "lmpi_score": score,
        "severity_label": assign_severity(score),
        "lmpi_note": "Formula index estimated from station facts. Not a survey and not a model output.",
    }


def load_delhi_survey_lmpi():
    """Same LMPI aggregation as derive_01_lmpi.py, applied to Delhi survey responses."""
    path = os.path.join(RAW, "09_delhi_survey_responses.csv")
    if not os.path.exists(path):
        path = os.path.join(BASE, "Data", "delhi_survey_responses.csv")
    df = pd.read_csv(path)
    df["station_name"] = df["station_name"].replace(DELHI_NAME_MAP)
    df["line"] = df["line"].map(DELHI_LINE_MAP).fillna(df["line"].astype(str))
    df = df[df["line"].isin(["Red", "Yellow", "Blue"])].copy()

    agg = df.groupby(["station_name", "line"]).agg(
        avg_satisfaction=("satisfaction_rating", "mean"),
        avg_auto_avail=("auto_availability", "mean"),
        avg_bus_freq=("bus_frequency", "mean"),
        avg_safety=("safety_rating", "mean"),
        avg_walkability=("walkability", "mean"),
        pct_problem_auto=("problem_auto", "mean"),
        pct_problem_bus=("problem_bus", "mean"),
        pct_problem_walk=("problem_walk", "mean"),
        pct_problem_safety=("problem_safety", "mean"),
        pct_problem_crowd=("problem_crowding", "mean"),
        total_responses=("satisfaction_rating", "count"),
        recommended_last_mile=("last_mile_mode", lambda s: s.mode().iloc[0] if len(s.mode()) else "Auto Rickshaw"),
    ).reset_index()

    agg["auto_problem_score"] = (
        ((5 - agg["avg_auto_avail"]) / 4 * 70) + (agg["pct_problem_auto"] * 30)
    ).round(1).clip(0, 100)
    agg["walking_problem_score"] = (
        ((5 - agg["avg_walkability"]) / 4 * 70) + (agg["pct_problem_walk"] * 30)
    ).round(1).clip(0, 100)
    agg["bus_problem_score"] = (
        ((5 - agg["avg_bus_freq"]) / 4 * 70) + (agg["pct_problem_bus"] * 30)
    ).round(1).clip(0, 100)
    agg["crowding_score"] = (
        ((5 - agg["avg_satisfaction"]) / 4 * 50) + (agg["pct_problem_crowd"] * 50)
    ).round(1).clip(0, 100)
    agg["safety_score"] = (
        ((5 - agg["avg_safety"]) / 4 * 70) + (agg["pct_problem_safety"] * 30)
    ).round(1).clip(0, 100)

    agg["lmpi_base"] = (
        agg["auto_problem_score"] * 0.28
        + agg["walking_problem_score"] * 0.22
        + agg["bus_problem_score"] * 0.20
        + agg["crowding_score"] * 0.18
        + agg["safety_score"] * 0.12
    ).round(1)

    # Clean-model inputs aligned to survey ratings (0–1 supply, metres walk).
    agg["auto_supply_score"] = (agg["avg_auto_avail"] / 5.0).clip(0.05, 0.98).round(3)
    agg["bus_connectivity_score"] = (agg["avg_bus_freq"] / 5.0).clip(0.05, 0.98).round(3)
    agg["walk_dist_m"] = (
        250 + ((5 - agg["avg_walkability"]) / 4.0) * 650
    ).round(0).astype(int).clip(250, 900)

    priors_path = os.path.join(RAW, "10_delhi_station_priors.csv")
    if not os.path.exists(priors_path):
        priors_path = os.path.join(BASE, "Data", "delhi_station_priors.csv")
    priors = pd.read_csv(priors_path)
    priors["station_name"] = priors["station_name"].replace(DELHI_NAME_MAP)
    priors["line"] = priors["line"].map(DELHI_LINE_MAP).fillna(priors["line"].astype(str))
    priors = priors.rename(columns={"basis": "prior_basis", "confidence": "prior_confidence", "n": "prior_n"})
    agg = agg.merge(
        priors[["station_name", "line", "prior_basis", "prior_confidence", "prior_n"]],
        on=["station_name", "line"],
        how="left",
    )
    return agg.set_index("station_name")


def assign_line_ridership(df):
    """Opening-year daily riders. Mumbai future lines use published 2031 totals."""
    daily = {}
    # Lines 9 and 7A share one published total.
    shared = df[df["line"].isin(["9", "7A"])]
    if len(shared):
        weights = shared["pop_density"] * shared["role"].map(
            lambda r: 1.4 if "interchange" in r or r in ("airport", "airport_adj") else 1.0
        )
        weights = weights / weights.sum()
        total = LINE_RIDERSHIP_2031["9"] * OPENING_FACTOR
        for name, w in zip(shared["station_name"], weights):
            daily[name] = int(round(total * w))
    for line, total_2031 in LINE_RIDERSHIP_2031.items():
        if line in ("9", "7A") or total_2031 is None:
            continue
        part = df[df["line"] == line]
        weights = part["pop_density"] * part["role"].map(
            lambda r: 1.5 if "interchange" in r or r == "terminus_interchange" else 1.0
        )
        weights = weights / weights.sum()
        total = total_2031 * OPENING_FACTOR
        for name, w in zip(part["station_name"], weights):
            daily[name] = int(round(total * float(w)))
    return daily


def delhi_daily(row):
    """Role-based scenario scale. Not a DMRC ticket count."""
    base = {
        "interchange_rail": 95000,
        "interchange": 72000,
        "terminus_interchange": 48000,
        "office_heavy": 46000,
        "office_premium": 50000,
        "office_mid": 38000,
        "shopping_hub": 52000,
        "commercial": 44000,
        "residential_high": 34000,
        "residential_mid": 22000,
        "religious_tourist": 40000,
        "airport": 60000,
        "airport_adj": 28000,
        "remote": 14000,
    }[row["role"]]
    return int(round(base * (0.92 + jitter(row["station_name"] + "d", 0.08) + 0.08)))


# Peak demand window and area character used to phrase interventions.
ROLE_PEAK = {
    "office_premium": ("Weekday 08:00–11:00 & 17:30–20:30", "office"),
    "office_heavy": ("Weekday 08:00–11:00 & 17:30–20:30", "office"),
    "office_mid": ("Weekday 08:00–11:00 & 17:30–20:30", "office"),
    "office_south": ("Weekday 08:30–11:00 & 17:30–20:00", "office"),
    "residential_high": ("Weekday 07:00–10:00 outbound & 18:00–21:00 return", "residential"),
    "residential_mid": ("Weekday 07:00–10:00 outbound & 18:00–21:00 return", "residential"),
    "interchange": ("Transfer peaks all day; heaviest 08:00–11:00 & 17:00–21:00", "interchange"),
    "interchange_rail": ("Rail–metro transfer peaks 07:30–11:00 & 17:00–21:00", "interchange"),
    "terminus_interchange": ("Terminus surge 07:30–10:30 & 17:30–21:00", "interchange"),
    "airport": ("Flight banks 05:00–09:00 & 18:00–23:00", "airport"),
    "airport_adj": ("Airport spillover 06:00–10:00 & 18:00–22:00", "airport"),
    "shopping_hub": ("Evening & weekend 17:00–22:00", "retail"),
    "commercial": ("Midday + evening 12:00–14:00 & 17:00–21:00", "retail"),
    "religious_tourist": ("Festival & weekend mornings 07:00–13:00", "tourist"),
    "remote": ("Sparse all-day demand; critical 07:30–09:30 & 18:00–20:00", "remote"),
}


def interventions_for(row):
    """Last-mile public transport only, sized to role, peak window, and ridership."""
    role = row["role"]
    peak_window, area = ROLE_PEAK.get(role, ("Weekday peak hours", "general"))
    daily = int(row.get("daily_riders") or 20000)
    peak_share = {
        "office": 0.15,
        "residential": 0.13,
        "interchange": 0.16,
        "airport": 0.14,
        "retail": 0.14,
        "tourist": 0.18,
        "remote": 0.11,
        "general": 0.12,
    }[area]
    peak_riders = max(400, int(round(daily * peak_share)))
    j = 0.92 + jitter(row["station_name"] + "iv", 0.08)

    auto_p = float(row["auto_problem_score"])
    bus_p = float(row["bus_problem_score"])
    walk_p = float(row["walking_problem_score"])
    crowd = float(row["crowding_score"])

    candidates = []

    # --- Autos / e-rickshaws ---
    if auto_p >= 38 or area in ("residential", "remote", "retail"):
        auto_cap = 18 if area in ("residential", "remote") else 28 if area == "retail" else 36
        auto_fleet = int(np.clip(round(peak_riders * (0.035 + auto_p / 3500) * j / 4), 3, auto_cap))
        if area == "office":
            text = f"Stage {auto_fleet} autos/e-rickshaws at the office exit for the evening leave window"
            why = "Office districts empty in a short window; street hail cannot clear the exit."
        elif area == "residential":
            text = f"Mark {auto_fleet} auto/e-rickshaw bays for morning colony last-mile"
            why = "Residential catchments need short hops from the gate before 10:00."
        elif area == "interchange":
            text = f"Pre-position {auto_fleet} transfer-exit autos between arriving trains"
            why = "Transfer pulses create short, sharp auto demand at the exit."
        elif area == "airport":
            text = f"Reserve {auto_fleet} short-hop auto/e-rickshaw bays for terminal spillover"
            why = "Many airport trips are short city hops that do not need a full cab fare."
        elif area == "retail":
            text = f"Evening auto/e-rickshaw bay ({auto_fleet} vehicles, 17:00–22:00)"
            why = "Shopper peaks sit outside regular commute auto supply."
        elif area == "tourist":
            text = f"Festival-day auto pool of {auto_fleet} vehicles near the exit"
            why = "Religious/tourist peaks are short and need staged last-mile."
        else:
            text = f"Guarantee a stand of {auto_fleet} autos/e-rickshaws — local supply is thin"
            why = "Remote stops have almost no standing autos today."
        impact = min(0.95, (auto_p / 100) * 0.65 + (peak_riders / 80000) * 0.25 + 0.08)
        candidates.append({
            "problem": "auto",
            "intervention": text,
            "impact_score": round(impact, 3),
            "severity_label": row["severity_label"],
            "estimated_cost_lakhs": int(round(auto_fleet * 2 * j)),
            "fleet_count": auto_fleet,
            "fleet_type": "auto",
            "peak_window": peak_window,
            "rationale": why,
        })

    # --- Feeder bus ---
    if bus_p >= 40 or walk_p >= 55 or area in ("remote", "residential", "interchange"):
        bus_cap = 4 if area in ("residential", "remote") else 6 if area == "retail" else 10
        bus_fleet = int(np.clip(round(peak_riders * (0.08 + bus_p / 1800) * j / 45), 1, bus_cap))
        if area == "office":
            text = f"Run {bus_fleet} estate/office shuttle bus(es) timed to 09:00 arrival and 18:30 exit"
            why = "Long walks inside office estates are a bus problem, not an auto problem."
        elif area == "residential":
            text = f"Add {bus_fleet} colony feeder bus(es) on a 8–12 min headway in the commute peaks"
            why = "Colony depth is too far for walking; a short feeder beats random autos."
        elif area == "interchange":
            text = f"Time {bus_fleet} feeder bus(es) to the busiest transfer arrivals"
            why = "Interchange riders need a bus that meets the train, not a fixed timetable."
        elif area == "airport":
            text = f"Keep {bus_fleet} airport-link bus(es) on the peak flight banks"
            why = "Airport-adjacent demand is directional and suits a bus loop."
        elif area == "remote":
            text = f"Provide {bus_fleet} sparse-area feeder bus(es) covering the longest walk catchment"
            why = "Remote stations fail on walking distance; bus is the primary fix."
        elif area == "tourist":
            text = f"Deploy {bus_fleet} temporary feeder bus(es) on festival mornings"
            why = "Tourist surges need buses for a few hours, not permanent auto stands only."
        else:
            text = f"Add {bus_fleet} short feeder bus(es) for the evening retail peak"
            why = "Retail peaks need shared capacity, not only single-hire vehicles."
        impact = min(0.95, (bus_p / 100) * 0.55 + (walk_p / 100) * 0.25 + (peak_riders / 90000) * 0.15)
        candidates.append({
            "problem": "bus",
            "intervention": text,
            "impact_score": round(impact, 3),
            "severity_label": row["severity_label"],
            "estimated_cost_lakhs": int(round(bus_fleet * 15 * j)),
            "fleet_count": bus_fleet,
            "fleet_type": "bus",
            "peak_window": peak_window,
            "rationale": why,
        })

    # --- Cabs (only where the area actually needs them) ---
    cab_fit = area in ("office", "airport", "interchange") or (auto_p >= 60 and crowd >= 55)
    if cab_fit:
        cab_cap = 18 if area == "office" else 24 if area == "airport" else 16
        cab_slots = int(np.clip(round(peak_riders * (0.03 + auto_p / 3000) * j / 3), 3, cab_cap))
        if area == "office":
            text = f"Book {cab_slots} guaranteed cab pickup slots for the 18:00–20:30 office exit"
            why = "Premium/office exits oversubscribe street cabs in a 90-minute window."
        elif area == "airport":
            text = f"Hold {cab_slots} aggregator cab slots on the {peak_window.split(',')[0].lower()} banks"
            why = "Airport trips skew to cabs; empty wait time is the failure mode."
        elif area == "interchange":
            text = f"Guarantee {cab_slots} cab slots at the busiest transfer pulse"
            why = "Long onward trips from interchanges prefer cabs over autos."
        else:
            text = f"Partner for {cab_slots} peak cab slots when auto supply collapses"
            why = "High crowding plus weak auto supply needs a cab backup."
        impact = min(0.95, (auto_p / 100) * 0.45 + (crowd / 100) * 0.30 + (peak_riders / 100000) * 0.20)
        candidates.append({
            "problem": "cab",
            "intervention": text,
            "impact_score": round(impact, 3),
            "severity_label": row["severity_label"],
            "estimated_cost_lakhs": int(round(8 + cab_slots * 1.2 * j)),
            "fleet_count": cab_slots,
            "fleet_type": "cab",
            "peak_window": peak_window,
            "rationale": why,
        })

    if not candidates:
        # Fallback for very low-need stations — one light auto stand.
        n = 4
        candidates.append({
            "problem": "auto",
            "intervention": f"Maintain a small stand of {n} autos/e-rickshaws for off-peak gaps",
            "impact_score": 0.25,
            "severity_label": row["severity_label"],
            "estimated_cost_lakhs": 6,
            "fleet_count": n,
            "fleet_type": "auto",
            "peak_window": peak_window,
            "rationale": "Low LMPI — light coverage only.",
        })

    # Keep the strongest 2 actions so the queue stays readable and station-specific.
    candidates.sort(key=lambda x: x["impact_score"], reverse=True)
    return candidates[:2]


def trains_for(daily, severity):
    # A 6-coach train carries about 1,500 people. Morning peak is about 12% of the day.
    peak_load = daily * 0.12
    current = int(np.clip(round(peak_load / 1500), 6, 18))
    extra = 2 if severity == "Critical" else 1 if severity == "High" else 0
    return current, current + extra


def forecast_30(daily):
    """Weekday profile around the station's own daily level. Scenario, not the 2.64% model."""
    start = pd.Timestamp("2026-01-01")
    rows = []
    for i in range(30):
        day = start + pd.Timedelta(days=i)
        weekend = day.dayofweek >= 5
        factor = 0.86 if weekend else 1.05
        value = int(round(daily * factor))
        rows.append({"date": str(day.date()), "footfall": value})
    return rows


def festival_block(stations, festivals):
    result = {}
    for name, mult in festivals:
        rows = []
        for s in stations:
            extra = int(round(s["daily_riders"] * mult))
            rows.append({
                "station_name": s["station_name"],
                "line": s["line"],
                "severity_label": s["severity_label"],
                "normal_daily": s["daily_riders"],
                "extra_riders": extra,
                "avg_festival_boost": mult,
            })
        rows.sort(key=lambda r: r["extra_riders"], reverse=True)
        result[name] = {
            "festival": name,
            "station_count": len(rows),
            "network_avg_extra_riders": int(round(np.mean([r["extra_riders"] for r in rows]))),
            "stations": rows,
            "surge_stations": rows[:5],
            "quiet_stations": list(reversed(rows[-5:])),
            "caveat": (
                "The festival percentage is applied across this network, so stations differ by how busy "
                "they already are. This matches the original Mumbai festival page. Synthetic stations use "
                "scenario ridership, not ticket data."
            ),
        }
    return result


def cv_report(model, X, y, n_splits=5):
    min_class = int(pd.Series(y).value_counts().min())
    splits = min(n_splits, min_class)
    skf = StratifiedKFold(n_splits=splits, shuffle=True, random_state=42)
    pred = cross_val_predict(model, X, y, cv=skf)
    labels = sorted(set(y))
    cm = confusion_matrix(y, pred, labels=labels)
    return {
        "accuracy": round(float(accuracy_score(y, pred)), 4),
        "precision_weighted": round(float(precision_score(y, pred, average="weighted", zero_division=0)), 4),
        "recall_weighted": round(float(recall_score(y, pred, average="weighted", zero_division=0)), 4),
        "f1_weighted": round(float(f1_score(y, pred, average="weighted", zero_division=0)), 4),
        "f1_macro": round(float(f1_score(y, pred, average="macro", zero_division=0)), 4),
        "confusion_matrix": cm.tolist(),
        "labels": [str(x) for x in labels],
        "folds": splits,
    }


def xgb():
    # Same settings as Scripts/layer1_classification.py so the comparison is fair.
    return XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="mlogloss",
        random_state=42,
        verbosity=0,
    )


def main():
    print("Loading original Mumbai tables...")
    master = pd.read_csv(os.path.join(RAW, "01_station_master.csv"))
    features = pd.read_csv(os.path.join(DER, "12_classification_features.csv"))
    survey = pd.read_csv(os.path.join(RAW, "08_survey_responses.csv"))
    master["is_interchange"] = master["is_interchange"].astype(str).str.lower().isin(["true", "1"])
    master["is_elevated"] = master["is_elevated"].astype(str).str.lower().isin(["true", "1"])

    feat = features.merge(
        master[["station_name", "auto_supply_score", "bus_connectivity_score", "walk_dist_m", "is_interchange", "is_elevated", "role"]],
        on="station_name",
        how="left",
        suffixes=("", "_m"),
    )
    # classification file already has some of these columns
    for col in ["auto_supply_score", "bus_connectivity_score", "walk_dist_m", "is_interchange", "is_elevated"]:
        if f"{col}_m" in feat.columns:
            feat[col] = feat[col].fillna(feat[f"{col}_m"])

    feat["severity_model"] = feat["severity_label"].replace({"Low": "Medium"})

    clean_cols = ["pop_density", "auto_supply_score", "bus_connectivity_score", "walk_dist_m", "is_interchange", "is_elevated"]
    # The published model keeps the survey scores and the flags built from them.
    # It only drops columns that are a direct rename of lmpi_score.
    drop_for_published = {
        "station_name", "line", "severity_label", "severity_encoded",
        "accessibility_score", "lmpi_percentile", "lmpi_score",
        "freq_impact", "best_impact", "freq_delta_peak",
    }
    leaky_cols = [c for c in features.columns if c not in drop_for_published]
    for frame in (feat,):
        for c in clean_cols:
            if frame[c].dtype == bool:
                frame[c] = frame[c].astype(int)
            frame[c] = pd.to_numeric(frame[c], errors="coerce")
    feat[clean_cols] = feat[clean_cols].fillna(feat[clean_cols].median())
    for c in leaky_cols:
        feat[c] = pd.to_numeric(feat[c], errors="coerce")
    feat[leaky_cols] = feat[leaky_cols].fillna(0)

    le = LabelEncoder()
    y = le.fit_transform(feat["severity_model"])
    label_names = list(le.classes_)

    print("Severity models: leaky formula inputs vs station facts only...")
    leaky = cv_report(xgb(), feat[leaky_cols].to_numpy(), y)
    clean = cv_report(xgb(), feat[clean_cols].to_numpy(), y)
    leaky["class_names"] = label_names
    clean["class_names"] = label_names

    print("Learning curve on the real 69...")
    train_sizes, train_scores, test_scores = learning_curve(
        xgb(),
        feat[clean_cols].to_numpy(),
        y,
        train_sizes=np.linspace(0.4, 1.0, 5),
        cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
        scoring="accuracy",
        shuffle=True,
        random_state=42,
    )
    learning = []
    for n, tr, te in zip(train_sizes, train_scores, test_scores):
        learning.append({
            "stations": int(n),
            "train_accuracy": round(float(tr.mean()), 4),
            "validation_accuracy": round(float(te.mean()), 4),
        })

    print("Leave-one-line-out...")
    line_holdout = []
    X_clean = feat[clean_cols].to_numpy()
    for line in ["1", "2A", "7", "3"]:
        test_mask = feat["line"].astype(str) == line
        if test_mask.sum() < 3 or (~test_mask).sum() < 10:
            continue
        model = xgb()
        model.fit(X_clean[~test_mask], y[~test_mask.to_numpy()])
        pred = model.predict(X_clean[test_mask])
        line_holdout.append({
            "held_out_line": line,
            "test_stations": int(test_mask.sum()),
            "accuracy": round(float(accuracy_score(y[test_mask.to_numpy()], pred)), 4),
            "f1_weighted": round(float(f1_score(y[test_mask.to_numpy()], pred, average="weighted", zero_division=0)), 4),
        })

    print("Choice model...")
    survey_m = survey.merge(
        master[["station_name", "pop_density", "auto_supply_score", "bus_connectivity_score", "walk_dist_m", "is_interchange", "is_elevated"]],
        on="station_name",
        how="inner",
    )
    problem_sum = survey_m[["problem_auto", "problem_bus", "problem_walk", "problem_safety", "problem_crowding"]].sum(axis=1)
    survey_m["would_opt"] = ((survey_m["satisfaction_rating"] >= 3) & (problem_sum <= 2)).astype(int)
    choice_cols = clean_cols[:]
    Xc = survey_m[choice_cols].astype(float).to_numpy()
    yc = survey_m["would_opt"].to_numpy()
    choice_pipe_report = cv_report(
        LogisticRegression(max_iter=500, class_weight="balanced"),
        StandardScaler().fit_transform(Xc),
        yc,
    )
    scaler = StandardScaler()
    Xs = scaler.fit_transform(Xc)
    logit = LogisticRegression(max_iter=500, class_weight="balanced")
    logit.fit(Xs, yc)
    coefs = []
    pretty = {
        "pop_density": "Denser surroundings",
        "auto_supply_score": "Better auto availability",
        "bus_connectivity_score": "Better bus connection",
        "walk_dist_m": "Longer walk to the station",
        "is_interchange": "Station is an interchange",
        "is_elevated": "Station is elevated",
    }
    for name, coef in sorted(zip(choice_cols, logit.coef_[0]), key=lambda t: abs(t[1]), reverse=True):
        coefs.append({
            "feature": name,
            "label": pretty[name],
            "coefficient": round(float(coef), 3),
            "direction": "opt in" if coef > 0 else "opt out",
        })

    print("Building expansion stations...")
    delhi_lmpi = load_delhi_survey_lmpi()
    print(f"  Delhi survey LMPI for {len(delhi_lmpi)} stations")
    rows = []
    for item in FUTURE_MUMBAI:
        rows.append(station_row(*item, city="Mumbai", network="mumbai_future"))
    for item in DELHI:
        rows.append(station_row(*item, city="Delhi", network="delhi"))
    exp = pd.DataFrame(rows)
    mumbai_daily = assign_line_ridership(exp[exp["network"] == "mumbai_future"])
    stations = []
    for rec in exp.to_dict(orient="records"):
        rec.update(lmpi_from_facts(rec))
        if rec["network"] == "mumbai_future":
            rec["daily_riders"] = mumbai_daily[rec["station_name"]]
            rec["is_synthetic"] = True
            rec["data_source"] = "synthetic_mmrda"
        else:
            rec["daily_riders"] = delhi_daily(rec)
            name = rec["station_name"]
            if name in delhi_lmpi.index:
                drow = delhi_lmpi.loc[name]
                if isinstance(drow, pd.DataFrame):
                    drow = drow[drow["line"] == rec["line"]]
                    drow = drow.iloc[0] if len(drow) else delhi_lmpi.loc[name].iloc[0]
                boost = ROLE_BOOST.get(rec["role"], 0)
                score = float(np.clip(round(float(drow["lmpi_base"]) + boost, 1), 0, 100))
                rec.update({
                    "auto_problem_score": float(drow["auto_problem_score"]),
                    "walking_problem_score": float(drow["walking_problem_score"]),
                    "bus_problem_score": float(drow["bus_problem_score"]),
                    "crowding_score": float(drow["crowding_score"]),
                    "safety_score": float(drow["safety_score"]),
                    "lmpi_score": score,
                    "severity_label": assign_severity(score),
                    "recommended_last_mile": str(drow["recommended_last_mile"]),
                    "auto_supply_score": float(drow["auto_supply_score"]),
                    "bus_connectivity_score": float(drow["bus_connectivity_score"]),
                    "walk_dist_m": int(drow["walk_dist_m"]),
                    "survey_responses": int(drow["total_responses"]),
                    "prior_basis": None if pd.isna(drow.get("prior_basis")) else str(drow.get("prior_basis")),
                    "prior_confidence": None if pd.isna(drow.get("prior_confidence")) else str(drow.get("prior_confidence")),
                    "lmpi_note": "Survey-backed LMPI from Delhi passenger responses (same formula as Mumbai).",
                    "is_synthetic": False,
                    "data_source": "delhi_survey",
                })
            else:
                rec["is_synthetic"] = True
                rec["data_source"] = "synthetic_delhi_missing_survey"
        rec["current_trains_hr"], rec["recommended_trains_hr"] = trains_for(rec["daily_riders"], rec["severity_label"])
        rec["interventions"] = interventions_for(rec)
        rec["forecast_30"] = forecast_30(rec["daily_riders"])
        stations.append(rec)

    # Choice probabilities from station facts only.
    station_X = pd.DataFrame(stations)[choice_cols].astype(float)
    # Mumbai 69 probabilities too
    mumbai_X = feat[choice_cols].astype(float)
    opt_exp = logit.predict_proba(scaler.transform(station_X.to_numpy()))[:, 1]
    opt_mum = logit.predict_proba(scaler.transform(mumbai_X.to_numpy()))[:, 1]
    for s, p in zip(stations, opt_exp):
        s["opt_in_probability"] = round(float(p), 3)
        if s["network"] == "delhi" and s.get("data_source") == "delhi_survey":
            s["opt_in_source"] = "Predicted from station facts; Delhi LMPI severity is survey-backed."
        else:
            s["opt_in_source"] = "Transfer prediction from the Mumbai survey model. Not an observed future-line survey."

    observed = survey_m.groupby("station_name")["would_opt"].mean()
    mumbai_choice = []
    for name, p in zip(feat["station_name"], opt_mum):
        mumbai_choice.append({
            "station_name": name,
            "line": str(feat.loc[feat["station_name"] == name, "line"].iloc[0]),
            "opt_in_probability": round(float(p), 3),
            "survey_opt_in_rate": round(float(observed.get(name, np.nan)), 3),
            "opt_in_source": "Predicted from station facts. The survey rate is the share of real responses that met the written rule.",
        })

    print("Clustering...")
    cluster_frame = pd.concat([
        feat[clean_cols].assign(station_name=feat["station_name"], network="mumbai69", severity=feat["severity_label"]),
        pd.DataFrame(stations)[clean_cols + ["station_name", "network", "severity_label"]].rename(columns={"severity_label": "severity"}),
    ], ignore_index=True)
    Z = StandardScaler().fit_transform(cluster_frame[clean_cols].astype(float))
    best_k, best_score, best_labels = None, -1, None
    for k in (3, 4):
        km = KMeans(n_clusters=k, n_init=20, random_state=42)
        labels_k = km.fit_predict(Z)
        score = float(silhouette_score(Z, labels_k))
        if score > best_score:
            best_k, best_score, best_labels = k, score, labels_k
            best_km = km
    cluster_frame["cluster"] = best_labels
    # Name each cluster from the centroid that stands out.
    centroids = pd.DataFrame(best_km.cluster_centers_, columns=clean_cols)
    cluster_names = {}
    for i, row in centroids.iterrows():
        if row["walk_dist_m"] > 0.4 and row["bus_connectivity_score"] < 0:
            cluster_names[i] = "Long walk, weak bus"
        elif row["is_interchange"] > 0.4:
            cluster_names[i] = "Interchange stations"
        elif row["pop_density"] > 0.3:
            cluster_names[i] = "Dense, busy surroundings"
        else:
            cluster_names[i] = "Quieter residential stops"
    # Keep names unique
    seen = {}
    for i, name in list(cluster_names.items()):
        if name in seen:
            cluster_names[i] = name + f" ({i})"
        seen[name] = True
    cluster_frame["cluster_name"] = cluster_frame["cluster"].map(cluster_names)

    mum = cluster_frame[cluster_frame["network"] == "mumbai69"]
    crosstab = pd.crosstab(mum["cluster_name"], mum["severity"]).to_dict()
    # disagreement: station severity mode of its cluster differs
    disagreements = []
    mode_by_cluster = mum.groupby("cluster_name")["severity"].agg(lambda s: s.value_counts().index[0])
    for _, r in mum.iterrows():
        if r["severity"] != mode_by_cluster[r["cluster_name"]]:
            disagreements.append({
                "station_name": r["station_name"],
                "lmpi_severity": r["severity"],
                "cluster": r["cluster_name"],
                "cluster_usual_severity": mode_by_cluster[r["cluster_name"]],
            })

    name_to_cluster = dict(zip(cluster_frame["station_name"] + "|" + cluster_frame["network"], cluster_frame["cluster_name"]))
    for s in stations:
        s["discovered_cluster"] = name_to_cluster[s["station_name"] + "|" + s["network"]]
    for row in mumbai_choice:
        row["discovered_cluster"] = name_to_cluster.get(row["station_name"] + "|mumbai69")

    print("Future-line effect on the original 69...")
    by_name = {s["station_name"]: s for s in stations}
    # Approximate current daily level for the 69 from classification frequency fields if present,
    # otherwise a role-based stand-in used only for the percent change.
    base_daily = {}
    if "rec_trains_peak" in feat.columns:
        for _, r in feat.iterrows():
            # Invert the same peak rule loosely: trains * 1500 / 0.12
            trains = float(r.get("rec_trains_peak") or 10)
            base_daily[r["station_name"]] = int(round(trains * 1500 / 0.12))
    impact_rows = []
    extras = {name: {"low": 0, "mid": 0, "high": 0, "notes": []} for name in feat["station_name"]}
    for src, dest, share, note in TRANSFER_LINKS:
        src_daily = by_name[src]["daily_riders"]
        extras[dest]["low"] += int(round(src_daily * share * 0.5))
        extras[dest]["mid"] += int(round(src_daily * share))
        extras[dest]["high"] += int(round(src_daily * share * 1.5))
        extras[dest]["notes"].append(note)
    for dest, loss_share, note in DIVERSION:
        base = base_daily.get(dest, 40000)
        lost = int(round(base * loss_share))
        extras[dest]["low"] -= int(round(lost * 0.5))
        extras[dest]["mid"] -= lost
        extras[dest]["high"] -= int(round(lost * 1.5))
        extras[dest]["notes"].append(note)
    for name, bucket in extras.items():
        if bucket["mid"] == 0 and not bucket["notes"]:
            continue
        base = base_daily.get(name, 0)
        extra_peak = abs(bucket["mid"]) * 0.12
        extra_trains = int(np.ceil(extra_peak / 1500)) if bucket["mid"] > 0 else 0
        impact_rows.append({
            "station_name": name,
            "line": str(feat.loc[feat["station_name"] == name, "line"].iloc[0]),
            "base_daily_estimate": base,
            "extra_low": bucket["low"],
            "extra_mid": bucket["mid"],
            "extra_high": bucket["high"],
            "extra_trains_mid": extra_trains,
            "notes": bucket["notes"],
        })
    impact_rows.sort(key=lambda r: r["extra_mid"], reverse=True)

    print("Festivals and interchange...")
    festivals = {
        "mumbai_future": festival_block([s for s in stations if s["network"] == "mumbai_future"], MUMBAI_FESTIVALS),
        "delhi": festival_block([s for s in stations if s["network"] == "delhi"], DELHI_FESTIVALS),
    }
    # Future-open festival on the 69 is served by scaling on the API from impact, not stored here.

    # Metro-to-metro only — same idea as Mumbai 69 (no railway / monorail / depot).
    METRO_CONNECTS = {
        "1", "2A", "2B", "3", "4", "4A", "5", "6", "7", "7A", "9",
        "Red", "Yellow", "Blue", "Pink", "Green", "Violet", "Magenta", "Grey",
        "Airport Express", "Rapid Metro", "Blue branch",
    }
    NON_METRO_CONNECTS = {"railway", "monorail", "eastern express", "depot", "none"}

    def is_metro_connect(target):
        if not target:
            return False
        t = str(target).strip()
        if t.lower() in NON_METRO_CONNECTS:
            return False
        return t in METRO_CONNECTS

    interchange = []
    for s in stations:
        if not s["is_interchange"]:
            continue
        connects = s["interchange_with"]
        if not is_metro_connect(connects):
            continue
        headway_min = round(60 / s["recommended_trains_hr"], 1)
        wait = round(headway_min / 2, 1)
        quality = "excellent" if wait <= 3 else "good" if wait <= 5 else "poor"
        interchange.append({
            "station_name": s["station_name"],
            "line": s["line"],
            "line_a": s["line"],
            "line_b": connects,
            "connects_to": connects,
            "network": s["network"],
            "trains_per_hour": s["recommended_trains_hr"],
            "expected_wait_min": wait,
            "sync_quality": quality,
            "note": (
                "Metro-to-metro planning check only. Railway / monorail links are excluded. "
                "Wait is half the headway, not a live timetable."
            ),
        })

    # Drop bulky duplicates from station list stored for the map. Keep forecast.
    public_stations = []
    for s in stations:
        public_stations.append({k: s[k] for k in s if k != "forecast_30"})
        public_stations[-1]["forecast_30"] = s["forecast_30"]

    evaluation = {
        "leaky_severity_model": leaky,
        "clean_severity_model": clean,
        "learning_curve": learning,
        "leave_one_line_out": line_holdout,
        "delhi_holdout": {
            "accuracy": None,
            "note": "Mumbai-trained clean model tested on Delhi survey severity labels.",
            "predicted_severity_counts": {},
            "survey_severity_counts": {},
            "n_stations": 0,
            "confusion_matrix": None,
            "labels": [],
        },
        "choice_model": {
            **choice_pipe_report,
            "coefficients": coefs,
            "rule": "A real Mumbai response counts as opt-in when satisfaction is 3 or more out of 5 and at most two of the five problem flags are set. Those answers are the target. They are not model inputs.",
            "respondents": int(len(survey_m)),
            "opt_in_rate": round(float(yc.mean()), 4),
            "majority_baseline": round(float(max(yc.mean(), 1 - yc.mean())), 4),
        },
        "clusters": {
            "k": int(best_k),
            "silhouette": round(float(best_score), 3),
            "names": {str(k): v for k, v in cluster_names.items()},
            "crosstab_mumbai69": {str(k): {str(kk): int(vv) for kk, vv in inner.items()} for k, inner in crosstab.items()},
            "disagreements": disagreements[:25],
            "disagreement_count": len(disagreements),
        },
        "notes": [
            "95.6% remains the published result of the original severity model that can see LMPI ingredients.",
            "The clean model uses only population, walk distance, bus access, auto access, interchange, and elevated. That is the honest comparison.",
            "Learning-curve validation accuracy below the training accuracy, on only 69 stations, is the underfitting and small-sample check.",
            "Delhi LMPI is survey-backed (4,560 responses). Future Mumbai lines remain synthetic.",
        ],
    }

    # Mumbai-trained clean model → Delhi survey holdout + future-Mumbai formula transfer.
    model = xgb()
    model.fit(X_clean, y)
    class_labels = list(le.classes_)

    delhi_rows = [s for s in stations if s["network"] == "delhi" and s.get("data_source") == "delhi_survey"]
    if delhi_rows:
        delhi_X = pd.DataFrame(delhi_rows)[clean_cols].astype(float).to_numpy()
        delhi_true = np.array([
            "Medium" if s["severity_label"] == "Low" else s["severity_label"] for s in delhi_rows
        ])
        delhi_pred = le.inverse_transform(model.predict(delhi_X))
        # Map any unseen labels
        delhi_pred = np.array([str(p) for p in delhi_pred])
        cm = confusion_matrix(delhi_true, delhi_pred, labels=class_labels)
        evaluation["delhi_holdout"] = {
            "accuracy": round(float(accuracy_score(delhi_true, delhi_pred)), 4),
            "precision_weighted": round(float(precision_score(delhi_true, delhi_pred, average="weighted", zero_division=0)), 4),
            "recall_weighted": round(float(recall_score(delhi_true, delhi_pred, average="weighted", zero_division=0)), 4),
            "f1_weighted": round(float(f1_score(delhi_true, delhi_pred, average="weighted", zero_division=0)), 4),
            "n_stations": int(len(delhi_rows)),
            "survey_responses": int(sum(s.get("survey_responses", 0) for s in delhi_rows)),
            "confusion_matrix": cm.tolist(),
            "labels": [str(x) for x in class_labels],
            "predicted_severity_counts": {str(k): int(v) for k, v in pd.Series(delhi_pred).value_counts().items()},
            "survey_severity_counts": {str(k): int(v) for k, v in pd.Series(delhi_true).value_counts().items()},
            "note": (
                "Real Delhi holdout: clean model trained only on Mumbai 69, tested against "
                "Delhi survey-derived severity labels (not formula agreement)."
            ),
        }
        for s, pred_label in zip(
            [s for s in public_stations if s["network"] == "delhi"],
            delhi_pred,
        ):
            s["transferred_severity"] = str(pred_label)

    # Combined clean CV on Mumbai + Delhi survey stations.
    delhi_feat = pd.DataFrame(delhi_rows)[clean_cols + ["severity_label"]].copy() if delhi_rows else pd.DataFrame()
    if len(delhi_feat):
        delhi_feat["severity_model"] = delhi_feat["severity_label"].replace({"Low": "Medium"})
        mum_feat = feat[clean_cols].copy()
        mum_feat["severity_model"] = feat["severity_model"]
        combined = pd.concat([mum_feat, delhi_feat[clean_cols + ["severity_model"]]], ignore_index=True)
        for c in clean_cols:
            combined[c] = pd.to_numeric(combined[c], errors="coerce")
            if combined[c].dtype == bool:
                combined[c] = combined[c].astype(int)
        combined[clean_cols] = combined[clean_cols].fillna(combined[clean_cols].median())
        # Reuse Mumbai label encoder classes; drop rows with unknown labels.
        combined = combined[combined["severity_model"].isin(class_labels)].copy()
        y_comb = le.transform(combined["severity_model"])
        X_comb = combined[clean_cols].to_numpy()
        evaluation["clean_severity_model_combined"] = cv_report(xgb(), X_comb, y_comb)
        evaluation["clean_severity_model_combined"]["class_names"] = class_labels
        evaluation["clean_severity_model_combined"]["n_stations"] = int(len(combined))
        evaluation["clean_severity_model_combined"]["note"] = (
            "Clean XGBoost cross-validated on Mumbai 69 + Delhi survey stations "
            f"({len(combined)} labeled stations)."
        )

    def transfer_report(network_id):
        rows = [s for s in stations if s["network"] == network_id]
        if not rows:
            return None
        X = pd.DataFrame(rows)[clean_cols].astype(float).to_numpy()
        pred = le.inverse_transform(model.predict(X))
        formula = np.array([
            "Medium" if s["severity_label"] == "Low" else s["severity_label"]
            for s in rows
        ])
        cm = confusion_matrix(formula, pred, labels=class_labels)
        agree = float((pred == formula).mean()) if len(pred) else 0.0
        return {
            "agreement": round(agree, 4),
            "n_stations": int(len(rows)),
            "confusion_matrix": cm.tolist(),
            "labels": [str(x) for x in class_labels],
            "predicted_counts": {str(k): int(v) for k, v in pd.Series(pred).value_counts().items()},
            "formula_counts": {str(k): int(v) for k, v in pd.Series(formula).value_counts().items()},
            "predictions": [
                {
                    "station_name": s["station_name"],
                    "line": s["line"],
                    "formula_severity": str(f),
                    "predicted_severity": str(p),
                    "agree": bool(p == f),
                }
                for s, p, f in zip(rows, pred, formula)
            ],
        }

    future_transfer = transfer_report("mumbai_future")

    def public_transfer(block):
        if not block:
            return None
        return {k: v for k, v in block.items() if k != "predictions"}

    evaluation["transfer_check"] = {
        "note": (
            "Future Mumbai only: agreement with formula labels — not survey accuracy. "
            "Delhi now has a real survey holdout above."
        ),
        "delhi": None,
        "mumbai_future": public_transfer(future_transfer),
    }
    if future_transfer:
        for s, row in zip(
            [s for s in public_stations if s["network"] == "mumbai_future"],
            future_transfer["predictions"],
        ):
            s["transferred_severity"] = row["predicted_severity"]

    bundle = {
        "assumptions": [
            "Future Mumbai station names are the MMRDA published lists for Lines 2B, 4, 5, 6, 7A, and 9. Stations already in the original 69 (D.N. Nagar, Dahisar, Andheri) are not duplicated.",
            "Future Mumbai daily riders are the MMRDA 2031 line totals multiplied by 0.45, then split across stations by density and interchange role. 2031 is a planning year, not opening day.",
            "Line 6 has no 2031 total on the MMRDA overview used here. Its total is Line 2B's published riders-per-km times Line 6's published length of 15.31 km.",
            "Lines 9 and 7A share the single published 2031 total of 11.12 lakh.",
            "Delhi LMPI and severity are survey-backed (4,560 responses across 50 stations). Daily ridership remains a role-based scenario scale, not DMRC ticket counts.",
            "LMPI on new stations is the same weighted formula, estimated from station facts, and is shown as an index. It is not an input to the choice model or the clean severity model.",
            "Transfer shares onto the original 69 are assumptions at published meeting points. The page shows a low, middle, and high case.",
            "Line 5 meets Line 4 at Kapurbawdi and does not directly add riders to the original 69.",
        ],
        "networks": [
            {"id": "mumbai69", "label": "Mumbai — 69 stations", "synthetic": False, "lines": ["1", "2A", "7", "3"]},
            {"id": "mumbai_future", "label": "Mumbai — future lines", "synthetic": True, "lines": ["2B", "4", "5", "6", "7A", "9"]},
            {"id": "delhi", "label": "Delhi — 50 stations (survey)", "synthetic": False, "survey_backed": True, "lines": ["Red", "Yellow", "Blue"]},
        ],
        "stations": public_stations,
        "mumbai_choice": mumbai_choice,
        "festivals": festivals,
        "future_impact": {
            "rows": impact_rows,
            "unaffected_note": "Stations that do not meet a future line are unchanged. Line 5 does not touch the original 69.",
            "share_note": "Middle case uses the stated transfer share. Low is half of that share. High is one and a half times that share.",
        },
        "interchange": interchange,
        "evaluation": evaluation,
        "choice_coefficients": coefs,
    }

    path = os.path.join(OUT, "bundle.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(bundle, f)
    backend_copy = os.path.join(BASE, "Backend", "expansion_bundle.json")
    with open(backend_copy, "w", encoding="utf-8") as f:
        json.dump(bundle, f)
    print(f"Wrote {path} ({os.path.getsize(path) / 1e6:.1f} MB)")
    print(f"Clean accuracy {clean['accuracy']:.3f}  Leaky accuracy {leaky['accuracy']:.3f}")
    print(f"Choice accuracy {choice_pipe_report['accuracy']:.3f}  Clusters k={best_k} silhouette={best_score:.3f}")
    print(f"Expansion stations {len(public_stations)}  Impact rows {len(impact_rows)}")

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot([r["stations"] for r in learning], [r["train_accuracy"] for r in learning], marker="o", label="Train")
    ax.plot([r["stations"] for r in learning], [r["validation_accuracy"] for r in learning], marker="o", label="Validation")
    ax.set_xlabel("Training stations (real Mumbai only)")
    ax.set_ylabel("Accuracy")
    ax.set_title("Clean severity model — learning curve")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS, "16_learning_curve_clean.png"), dpi=140)
    plt.close()


if __name__ == "__main__":
    main()
