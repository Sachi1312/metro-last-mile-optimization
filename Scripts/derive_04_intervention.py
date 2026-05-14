# ============================================================
# derive_04_intervention.py
# Derives intervention scores from LMPI + station roles
# Input  : Data/Derived/04_lmpi_scores.csv
#          Data/Raw/01_station_master.csv
# Output : Data/Derived/07_intervention_scores.csv
# ============================================================

import pandas as pd
import numpy as np
import os

BASE = r"C:\\Users\\parek\\Downloads\\LY Project"
RAW  = os.path.join(BASE, "Data", "Raw")
DER  = os.path.join(BASE, "Data", "Derived")

np.random.seed(42)

# ── STEP 1: Load inputs ───────────────────────────────────────
print("Loading LMPI scores and station master...")
df_lmpi    = pd.read_csv(os.path.join(DER, "04_lmpi_scores.csv"))
df_station = pd.read_csv(os.path.join(RAW, "01_station_master.csv"))
df = df_lmpi.merge(
    df_station[["station_name","role","is_interchange",
                "is_elevated","auto_supply_score","bus_connectivity_score"]],
    on="station_name", how="left"
)
print(f"  Loaded {len(df)} stations")

# ── STEP 2: Define intervention catalogue ─────────────────────
# Each intervention has:
#   - action     : what to do
#   - base_impact: effectiveness score (0-1)
#   - priority   : High/Medium/Low
#   - cost_range : estimated cost in lakhs (INR)
#   - targets    : which factor score it addresses

INTERVENTIONS = {
    "Critical": [
        {
            "action":      "Deploy pre-positioned auto fleet at peak hours",
            "base_impact": 0.88,
            "priority":    "High",
            "cost_min":    25, "cost_max": 60,
            "addresses":   "auto_problem_score",
        },
        {
            "action":      "Increase trains/hr during peak windows",
            "base_impact": 0.85,
            "priority":    "High",
            "cost_min":    0, "cost_max": 0,   # operational, no capex
            "addresses":   "crowding_score",
        },
        {
            "action":      "Add dedicated BEST bus feeder route",
            "base_impact": 0.80,
            "priority":    "High",
            "cost_min":    30, "cost_max": 80,
            "addresses":   "bus_problem_score",
        },
        {
            "action":      "Real-time auto/cab availability display boards",
            "base_impact": 0.72,
            "priority":    "Medium",
            "cost_min":    8,  "cost_max": 20,
            "addresses":   "auto_problem_score",
        },
    ],
    "High": [
        {
            "action":      "Auto aggregator partnership (Ola/Uber/Rapido)",
            "base_impact": 0.70,
            "priority":    "Medium",
            "cost_min":    5, "cost_max": 15,
            "addresses":   "auto_problem_score",
        },
        {
            "action":      "Covered walkway to nearest bus stop",
            "base_impact": 0.65,
            "priority":    "Medium",
            "cost_min":    10, "cost_max": 30,
            "addresses":   "walking_problem_score",
        },
        {
            "action":      "Cycle docking station at exit",
            "base_impact": 0.60,
            "priority":    "Medium",
            "cost_min":    8, "cost_max": 20,
            "addresses":   "walking_problem_score",
        },
        {
            "action":      "Increase off-peak train frequency",
            "base_impact": 0.62,
            "priority":    "Medium",
            "cost_min":    0, "cost_max": 0,
            "addresses":   "crowding_score",
        },
    ],
    "Medium": [
        {
            "action":      "Digital wayfinding + multilingual signage",
            "base_impact": 0.50,
            "priority":    "Low",
            "cost_min":    3, "cost_max": 10,
            "addresses":   "walking_problem_score",
        },
        {
            "action":      "Shelter + seating at pickup/drop zone",
            "base_impact": 0.48,
            "priority":    "Low",
            "cost_min":    2, "cost_max": 8,
            "addresses":   "safety_score",
        },
        {
            "action":      "Auto stand regularization + price board",
            "base_impact": 0.52,
            "priority":    "Low",
            "cost_min":    1, "cost_max": 5,
            "addresses":   "auto_problem_score",
        },
    ],
    "Low": [
        {
            "action":      "Monitor — no immediate intervention needed",
            "base_impact": 0.15,
            "priority":    "Low",
            "cost_min":    0, "cost_max": 0,
            "addresses":   "none",
        },
        {
            "action":      "Minor infrastructure maintenance",
            "base_impact": 0.20,
            "priority":    "Low",
            "cost_min":    1, "cost_max": 4,
            "addresses":   "safety_score",
        },
    ],
}

# ── STEP 3: Role-based impact modifier ───────────────────────
# Interchange stations get higher impact from frequency interventions
# Remote stations get higher impact from last-mile additions
ROLE_MODIFIER = {
    "interchange_rail":    1.15,
    "terminus_interchange":1.12,
    "interchange":         1.10,
    "office_premium":      1.08,
    "office_heavy":        1.06,
    "shopping_hub":        1.05,
    "residential_high":    1.00,
    "residential_mid":     0.95,
    "remote":              0.90,
    "airport":             1.02,
    "office_south":        1.03,
}

# ── STEP 4: Generate intervention rows ────────────────────────
print("Scoring interventions per station...")

rows = []
for _, st in df.iterrows():
    sev          = st["severity_label"]
    role_mod     = ROLE_MODIFIER.get(st["role"], 1.0)
    lmpi         = st["lmpi_score"]
    interventions = INTERVENTIONS.get(sev, INTERVENTIONS["Low"])

    for inv in interventions:
        # Adjust impact by role + LMPI intensity + small noise
        noise  = np.random.normal(0, 0.025)
        impact = round(min(1.0, max(0.05,
            inv["base_impact"] * role_mod + noise
        )), 3)

        # Factor-specific boost
        # If the station's specific problem score is very high,
        # the intervention addressing it has higher impact
        factor = inv["addresses"]
        if factor != "none" and factor in st.index:
            factor_score = st[factor]
            # High factor score → higher impact for that intervention
            factor_boost = (factor_score / 100) * 0.05
            impact = round(min(1.0, impact + factor_boost), 3)

        cost = round(np.random.uniform(inv["cost_min"], max(inv["cost_min"], inv["cost_max"])), 1)

        rows.append({
            "station_name":          st["station_name"],
            "line":                  st["line"],
            "role":                  st["role"],
            "is_interchange":        int(st["is_interchange"]),
            "lmpi_score":            lmpi,
            "severity_label":        sev,
            "intervention":          inv["action"],
            "impact_score":          impact,
            "priority":              inv["priority"],
            "factor_addressed":      factor,
            "recommended_last_mile": st["recommended_last_mile"],
            "estimated_cost_lakhs":  cost,
            "cost_effectiveness":    round(impact / max(0.1, cost / 100), 3) if cost > 0 else 9.99,
        })

df_out = pd.DataFrame(rows)
df_out.sort_values(["lmpi_score","impact_score"],
                   ascending=[False, False], inplace=True)
df_out.reset_index(drop=True, inplace=True)

# ── STEP 5: Save ──────────────────────────────────────────────
out_path = os.path.join(DER, "07_intervention_scores.csv")
df_out.to_csv(out_path, index=False)

# ── STEP 6: Summary ───────────────────────────────────────────
print(f"\n✅ Saved: Data/Derived/07_intervention_scores.csv")
print(f"   Total rows : {len(df_out)}")
print(f"\n   Interventions by severity:")
for sev in ["Critical","High","Medium","Low"]:
    c = (df_out["severity_label"]==sev).sum()
    print(f"   {sev:10s}: {c} rows")

print(f"\n   Top 5 highest impact interventions:")
top = df_out.nlargest(5, "impact_score")
print(top[["station_name","line","intervention",
           "impact_score","priority","estimated_cost_lakhs"]].to_string(index=False))

print(f"\n   Top 5 most cost-effective interventions:")
top_ce = df_out[df_out["estimated_cost_lakhs"]>0].nlargest(5,"cost_effectiveness")
print(top_ce[["station_name","intervention",
              "impact_score","estimated_cost_lakhs",
              "cost_effectiveness"]].to_string(index=False))