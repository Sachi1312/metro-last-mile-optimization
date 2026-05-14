# ============================================================
# layer4_optimization.py
# Layer 4 — Intervention Scoring + Frequency Optimization
# Input  : Data/Derived/04_lmpi_scores.csv
#          Data/Derived/06_frequency_optimization.csv
#          Data/Derived/07_intervention_scores.csv
#          Data/Derived/12_classification_features.csv
#          Outputs/Results/layer1_predictions.csv
#          Outputs/Results/layer3_30day_forecast.csv
# Output : Outputs/Results/ + Outputs/Plots/
# ============================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")
import seaborn as sns
import os
import warnings
warnings.filterwarnings("ignore")

BASE    = r"C:\Users\parek\Downloads\LY Project"
DER     = os.path.join(BASE, "Data", "Derived")
RAW     = os.path.join(BASE, "Data", "Raw")
RESULTS = os.path.join(BASE, "Outputs", "Results")
PLOTS   = os.path.join(BASE, "Outputs", "Plots")
os.makedirs(RESULTS, exist_ok=True)
os.makedirs(PLOTS,   exist_ok=True)

# ── Style ─────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.facecolor": "#0e1525","axes.facecolor":  "#141e33",
    "axes.edgecolor":   "#2a3f5f","axes.labelcolor": "#dce8f5",
    "axes.titlecolor":  "#dce8f5","axes.titlesize":  12,
    "xtick.color":      "#7a9bbf","ytick.color":     "#7a9bbf",
    "text.color":       "#dce8f5","grid.color":      "#1e3050",
    "grid.linestyle":   "--","grid.alpha":           0.5,
    "font.family":      "monospace",
    "legend.facecolor": "#141e33","legend.edgecolor": "#2a3f5f",
})

SEV_COLORS = {
    "Critical": "#ff3b55","High": "#ff6b35",
    "Medium":   "#ffc832","Low":  "#22d98a"
}
LINE_COLORS = {"1":"#f7b731","2A":"#20bf6b","7":"#a55eea","3":"#2e8fff"}

print("=" * 55)
print("  LAYER 4 — INTERVENTION + FREQUENCY OPTIMIZATION")
print("=" * 55)

# ── STEP 1: Load all inputs ───────────────────────────────────
print("\n[1/7] Loading inputs...")
df_lmpi     = pd.read_csv(os.path.join(DER,     "04_lmpi_scores.csv"))
df_freq     = pd.read_csv(os.path.join(DER,     "06_frequency_optimization.csv"))
df_interv   = pd.read_csv(os.path.join(DER,     "07_intervention_scores.csv"))
df_class_f  = pd.read_csv(os.path.join(DER,     "12_classification_features.csv"))
df_l1       = pd.read_csv(os.path.join(RESULTS, "layer1_predictions.csv"))
df_forecast = pd.read_csv(os.path.join(RESULTS, "layer3_30day_forecast.csv"))
df_station  = pd.read_csv(os.path.join(RAW,     "01_station_master.csv"))

df_forecast["date"] = pd.to_datetime(df_forecast["date"])

print(f"  LMPI scores       : {len(df_lmpi)} stations")
print(f"  Frequency optim.  : {len(df_freq)} rows")
print(f"  Interventions     : {len(df_interv)} rows")
print(f"  L1 predictions    : {len(df_l1)} stations")
print(f"  30-day forecast   : {len(df_forecast):,} rows")

# ── STEP 2: Build master station profile ─────────────────────
print("\n[2/7] Building master station profile...")

df_master = df_lmpi.merge(
    df_station[["station_name","role","is_interchange",
                "is_elevated","pop_density",
                "auto_supply_score","bus_connectivity_score","walk_dist_m"]],
    on="station_name", how="left"
)

# Add Layer 1 predictions
df_master = df_master.merge(
    df_l1[["station_name","xgb_predicted","rf_predicted"]],
    on="station_name", how="left"
)

# Best intervention per station
best_interv = df_interv.groupby("station_name").agg(
    top_intervention   = ("intervention",          "first"),
    top_impact         = ("impact_score",          "max"),
    total_interventions= ("intervention",          "count"),
    min_cost_lakhs     = ("estimated_cost_lakhs",  "min"),
    max_cost_lakhs     = ("estimated_cost_lakhs",  "max"),
    best_cost_eff      = ("cost_effectiveness",    "max"),
).reset_index()
df_master = df_master.merge(best_interv, on="station_name", how="left")

# Frequency peak recommendation
freq_peak = df_freq[df_freq["time_window"]=="morning_peak"][[
    "station_name","current_trains_hr","recommended_trains_hr",
    "delta_trains_hr","recommended_headway_min"
]].rename(columns={
    "current_trains_hr":     "curr_trains_peak",
    "recommended_trains_hr": "rec_trains_peak",
    "delta_trains_hr":       "delta_trains_peak",
    "recommended_headway_min":"rec_headway_peak",
})
df_master = df_master.merge(freq_peak, on="station_name", how="left")

# 30-day avg forecast per station
fore_avg = df_forecast.groupby("station_name")["forecasted_footfall"].agg(
    ["mean","max","min"]).reset_index()
fore_avg.columns = ["station_name","fore_avg_daily",
                    "fore_peak_day","fore_min_day"]
df_master = df_master.merge(fore_avg, on="station_name", how="left")

print(f"  Master profile    : {len(df_master)} stations, {len(df_master.columns)} columns")

# ── STEP 3: Compute composite optimization score ──────────────
print("\n[3/7] Computing optimization scores...")

# Priority score — combines LMPI + forecast growth + intervention impact
# Higher = needs more urgent action

SEV_WEIGHT = {"Critical": 1.0, "High": 0.75, "Medium": 0.45, "Low": 0.15}

df_master["sev_weight"]     = df_master["severity_label"].map(SEV_WEIGHT).fillna(0.45)
df_master["forecast_growth"]= (
    (df_master["fore_peak_day"] - df_master["fore_avg_daily"]) /
    (df_master["fore_avg_daily"] + 1)
).fillna(0).clip(0, 1).round(4)

df_master["optimization_score"] = (
    df_master["lmpi_score"]        / 100   * 0.35 +
    df_master["sev_weight"]                * 0.25 +
    df_master["top_impact"].fillna(0)      * 0.20 +
    df_master["forecast_growth"]           * 0.10 +
    (df_master["delta_trains_peak"] /
     df_master["rec_trains_peak"].replace(0,1)) * 0.10
).round(4)

df_master = df_master.sort_values("optimization_score", ascending=False).reset_index(drop=True)
df_master["priority_rank"] = df_master.index + 1

print(f"  Top 5 priority stations:")
top5 = df_master.head(5)[["station_name","line","lmpi_score",
                           "severity_label","optimization_score"]]
print(top5.to_string(index=False))

# ── STEP 4: Frequency optimization per time window ───────────
print("\n[4/7] Frequency optimization summary...")

# All 4 time windows
freq_summary = df_freq.merge(
    df_lmpi[["station_name","severity_label","lmpi_score"]],
    on="station_name", how="left",
    suffixes=("","_lmpi")
)

print(f"\n  Avg recommended trains/hr by severity and window:")
pivot = freq_summary.groupby(["severity_label","time_window"])[
    "recommended_trains_hr"].mean().unstack()
pivot = pivot.reindex(["Critical","High","Medium","Low"])
print(pivot.round(1).to_string())

print(f"\n  Total frequency increase needed (morning peak):")
for sev in ["Critical","High","Medium","Low"]:
    subset = freq_summary[(freq_summary["severity_label"]==sev) &
                          (freq_summary["time_window"]=="morning_peak")]
    if len(subset):
        total_delta = subset["delta_trains_hr"].sum()
        avg_delta   = subset["delta_trains_hr"].mean()
        print(f"  {sev:10s}: +{avg_delta:.1f} trains/hr avg  "
              f"(+{total_delta:.0f} total across {len(subset)} stations)")

# ── STEP 5: Intervention priority queue ──────────────────────
print("\n[5/7] Building intervention priority queue...")

# Top intervention per station ranked by impact × severity weight
df_interv_ranked = df_interv.merge(
    df_lmpi[["station_name","severity_label","lmpi_score"]],
    on="station_name", how="left",
    suffixes=("","_lmpi")
)
df_interv_ranked["severity_label"] = df_interv_ranked["severity_label_lmpi"].fillna(
    df_interv_ranked["severity_label"])

df_interv_ranked["sev_weight"] = df_interv_ranked["severity_label"].map(SEV_WEIGHT).fillna(0.45)
df_interv_ranked["priority_score"] = (
    df_interv_ranked["impact_score"] * 0.60 +
    df_interv_ranked["sev_weight"]   * 0.25 +
    (df_interv_ranked["lmpi_score"] / 100) * 0.15
).round(4)

# Top intervention per station only
df_top_interv = (df_interv_ranked
                 .sort_values("priority_score", ascending=False)
                 .groupby("station_name")
                 .first()
                 .reset_index()
                 .sort_values("priority_score", ascending=False))

print(f"  Top 10 highest priority interventions:")
print(df_top_interv[["station_name","line","severity_label",
                      "intervention","impact_score",
                      "estimated_cost_lakhs","priority_score"]
                    ].head(10).to_string(index=False))

# ── STEP 6: Save all outputs ──────────────────────────────────
print("\n[6/7] Saving results...")

# Master optimization report
df_master.to_csv(os.path.join(RESULTS, "layer4_master_optimization.csv"), index=False)

# Frequency recommendations (all windows)
df_freq.merge(
    df_lmpi[["station_name","severity_label"]],
    on="station_name", how="left"
).to_csv(os.path.join(RESULTS, "layer4_frequency_recommendations.csv"), index=False)

# Intervention priority queue
df_top_interv.to_csv(os.path.join(RESULTS, "layer4_intervention_queue.csv"), index=False)

# Final recommendations per station (one row per station)
df_final = df_master[[
    "station_name","line","role","lmpi_score","severity_label",
    "xgb_predicted","priority_rank","optimization_score",
    "top_intervention","top_impact","min_cost_lakhs","max_cost_lakhs",
    "curr_trains_peak","rec_trains_peak","delta_trains_peak","rec_headway_peak",
    "recommended_last_mile","fore_avg_daily","fore_peak_day",
    "is_interchange","is_elevated","pop_density",
]].copy()
df_final.to_csv(os.path.join(RESULTS, "layer4_final_recommendations.csv"), index=False)

print(f"  ✅ layer4_master_optimization.csv")
print(f"  ✅ layer4_frequency_recommendations.csv")
print(f"  ✅ layer4_intervention_queue.csv")
print(f"  ✅ layer4_final_recommendations.csv")

# ── STEP 7: Plots ─────────────────────────────────────────────
print("\n[7/7] Generating plots...")

# -- Plot 1: Optimization score ranked
fig, ax = plt.subplots(figsize=(12, 8))
top20   = df_master.head(20)
colors  = [SEV_COLORS[s] for s in top20["severity_label"]]
bars    = ax.barh(top20["station_name"][::-1],
                  top20["optimization_score"][::-1],
                  color=colors[::-1], edgecolor="none", height=0.65)
for bar, (_, row) in zip(bars, top20[::-1].iterrows()):
    ax.text(bar.get_width() + 0.003,
            bar.get_y() + bar.get_height()/2,
            f"Line {row['line']}  LMPI:{row['lmpi_score']:.0f}",
            va="center", fontsize=8, color="#dce8f5")
ax.set_title("Top 20 Stations — Optimization Priority Score")
ax.set_xlabel("Optimization Score (0–1)")
ax.set_xlim(0, 1.1)
ax.grid(axis="x")
ax.set_axisbelow(True)
# Legend
from matplotlib.patches import Patch
legend_elements = [Patch(facecolor=c, label=s)
                   for s,c in SEV_COLORS.items()]
ax.legend(handles=legend_elements, loc="lower right")
plt.tight_layout()
plt.savefig(os.path.join(PLOTS, "21_optimization_priority.png"), dpi=150)
plt.close()
print("  ✅ 21_optimization_priority.png")

# -- Plot 2: Frequency delta by line (morning peak)
fig, ax = plt.subplots(figsize=(10, 5))
freq_mp = df_freq[df_freq["time_window"]=="morning_peak"].merge(
    df_lmpi[["station_name","severity_label"]], on="station_name", how="left"
)
for i, (line, color) in enumerate(LINE_COLORS.items()):
    ldata = freq_mp[freq_mp["line"]==line]["delta_trains_hr"]
    if len(ldata):
        ax.bar(i, ldata.mean(), color=color, alpha=0.85,
               edgecolor="none", width=0.5,
               label=f"Line {line} (+{ldata.mean():.1f} avg)")
        ax.text(i, ldata.mean()+0.05,
                f"+{ldata.mean():.1f}", ha="center", fontsize=10)
ax.set_xticks(range(len(LINE_COLORS)))
ax.set_xticklabels([f"Line {l}" for l in LINE_COLORS])
ax.set_title("Average Frequency Increase Needed — Morning Peak")
ax.set_ylabel("Additional Trains per Hour")
ax.legend(fontsize=9)
ax.grid(axis="y")
ax.set_axisbelow(True)
plt.tight_layout()
plt.savefig(os.path.join(PLOTS, "22_frequency_delta_by_line.png"), dpi=150)
plt.close()
print("  ✅ 22_frequency_delta_by_line.png")

# -- Plot 3: Intervention cost vs impact scatter
fig, ax = plt.subplots(figsize=(10, 7))
for sev, color in SEV_COLORS.items():
    subset = df_top_interv[df_top_interv["severity_label"]==sev]
    if len(subset):
        ax.scatter(subset["estimated_cost_lakhs"],
                   subset["impact_score"],
                   c=color, label=sev, s=80, alpha=0.85,
                   edgecolors="#0e1525", linewidth=0.5)
# Label top 8
for _, row in df_top_interv.head(8).iterrows():
    ax.annotate(row["station_name"],
                (row["estimated_cost_lakhs"], row["impact_score"]),
                fontsize=7, color="#dce8f5",
                xytext=(4, 4), textcoords="offset points")
ax.set_title("Intervention Impact vs Cost — All Stations")
ax.set_xlabel("Estimated Cost (Lakhs ₹)")
ax.set_ylabel("Impact Score (0–1)")
ax.legend()
ax.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(PLOTS, "23_impact_vs_cost.png"), dpi=150)
plt.close()
print("  ✅ 23_impact_vs_cost.png")

# -- Plot 4: Last-mile mode by line
fig, ax = plt.subplots(figsize=(10, 5))
lm_line = df_master.groupby(["line","recommended_last_mile"]).size().unstack(fill_value=0)
lm_line = lm_line.reindex(["1","2A","7","3"])
lm_colors = ["#2e8fff","#22d98a","#ffc832","#ff6b35","#a55eea"]
lm_line.plot(kind="bar", ax=ax,
             color=lm_colors[:len(lm_line.columns)],
             edgecolor="none", width=0.65)
ax.set_title("Recommended Last-Mile Mode by Line")
ax.set_ylabel("Number of Stations")
ax.set_xlabel("Metro Line")
ax.legend(title="Mode", fontsize=9, title_fontsize=9)
ax.tick_params(axis="x", rotation=0)
ax.grid(axis="y")
ax.set_axisbelow(True)
plt.tight_layout()
plt.savefig(os.path.join(PLOTS, "24_lastmile_by_line.png"), dpi=150)
plt.close()
print("  ✅ 24_lastmile_by_line.png")

# -- Plot 5: 30-day forecast peak days
fig, ax = plt.subplots(figsize=(12, 5))
daily_total = df_forecast.groupby("date")["forecasted_footfall"].sum()
ax.plot(daily_total.index, daily_total.values/1e5,
        color="#2e8fff", linewidth=1.5, alpha=0.9)
ax.fill_between(daily_total.index, daily_total.values/1e5,
                alpha=0.15, color="#2e8fff")
# Mark weekends
for date in daily_total.index:
    if date.dayofweek >= 5:
        ax.axvline(date, color="#ffc832", alpha=0.08, linewidth=3)
ax.set_title("30-Day Network Footfall Forecast (All Lines Combined)")
ax.set_ylabel("Total Forecasted Footfall (Lakhs)")
ax.set_xlabel("Date")
ax.grid(True)
plt.xticks(rotation=30)
plt.tight_layout()
plt.savefig(os.path.join(PLOTS, "25_30day_network_forecast.png"), dpi=150)
plt.close()
print("  ✅ 25_30day_network_forecast.png")

# ── Final summary ─────────────────────────────────────────────
print("\n" + "=" * 55)
print("  LAYER 4 COMPLETE")
print("=" * 55)
print(f"\n  Stations analyzed    : {len(df_master)}")
print(f"  Critical priority    : {(df_master['severity_label']=='Critical').sum()}")
print(f"  High priority        : {(df_master['severity_label']=='High').sum()}")
print(f"\n  Top 3 priority stations:")
for _, row in df_master.head(3).iterrows():
    print(f"  #{row['priority_rank']} {row['station_name']} "
          f"(Line {row['line']}) — {row['severity_label']} — "
          f"Score: {row['optimization_score']:.3f}")

print(f"\n  Frequency Optimization:")
total_delta = df_freq[df_freq["time_window"]=="morning_peak"]["delta_trains_hr"].sum()
print(f"  Total additional trains needed (peak): +{total_delta:.0f} across network")
print(f"  Avg headway reduction: "
      f"{df_freq[df_freq['time_window']=='morning_peak']['recommended_headway_min'].mean():.1f} min")

print(f"\n  Saved:")
print(f"  ├── Outputs/Results/layer4_master_optimization.csv")
print(f"  ├── Outputs/Results/layer4_frequency_recommendations.csv")
print(f"  ├── Outputs/Results/layer4_intervention_queue.csv")
print(f"  └── Outputs/Results/layer4_final_recommendations.csv")
print(f"\n  Plots saved (21–25):")
print(f"  ├── 21_optimization_priority.png")
print(f"  ├── 22_frequency_delta_by_line.png")
print(f"  ├── 23_impact_vs_cost.png")
print(f"  ├── 24_lastmile_by_line.png")
print(f"  └── 25_30day_network_forecast.png")