# ============================================================
# eda.py
# Exploratory Data Analysis — Mumbai Metro Optimization
# Input  : Data/Derived/10_classification_ready.csv
#          Data/Derived/11_forecasting_ready.csv
#          Data/Raw/02_historical_ridership_5yr.csv
# Output : Outputs/Plots/ (10 plots)
# ============================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import os
import warnings
warnings.filterwarnings("ignore")

BASE  = r"C:\Users\parek\Downloads\LY Project"
RAW   = os.path.join(BASE, "Data", "Raw")
DER   = os.path.join(BASE, "Data", "Derived")
PLOTS = os.path.join(BASE, "Outputs", "Plots")
os.makedirs(PLOTS, exist_ok=True)

# ── Style ─────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.facecolor":  "#0e1525",
    "axes.facecolor":    "#141e33",
    "axes.edgecolor":    "#2a3f5f",
    "axes.labelcolor":   "#dce8f5",
    "axes.titlecolor":   "#dce8f5",
    "axes.titlesize":    13,
    "axes.labelsize":    11,
    "xtick.color":       "#7a9bbf",
    "ytick.color":       "#7a9bbf",
    "text.color":        "#dce8f5",
    "grid.color":        "#1e3050",
    "grid.linestyle":    "--",
    "grid.alpha":        0.5,
    "font.family":       "monospace",
    "legend.facecolor":  "#141e33",
    "legend.edgecolor":  "#2a3f5f",
})

SEV_COLORS = {
    "Critical": "#ff3b55",
    "High":     "#ff6b35",
    "Medium":   "#ffc832",
    "Low":      "#22d98a",
}
LINE_COLORS = {
    "1":  "#f7b731",
    "2A": "#20bf6b",
    "7":  "#a55eea",
    "3":  "#2e8fff",
}

print("=" * 55)
print("  EDA — Mumbai Metro Resource Optimization")
print("=" * 55)

# ── Load data ─────────────────────────────────────────────────
print("\nLoading datasets...")
df_class = pd.read_csv(os.path.join(DER, "10_classification_ready.csv"))
df_fore  = pd.read_csv(os.path.join(DER, "11_forecasting_ready.csv"))
df_hist  = pd.read_csv(os.path.join(RAW, "02_historical_ridership_5yr.csv"))
df_lmpi  = pd.read_csv(os.path.join(DER, "04_lmpi_scores.csv"))

df_fore["date"]  = pd.to_datetime(df_fore["date"])
df_hist["date"]  = pd.to_datetime(df_hist["date"])

print(f"  Classification rows : {len(df_class)}")
print(f"  Forecasting rows    : {len(df_fore):,}")
print(f"  Historical rows     : {len(df_hist):,}")

# ══════════════════════════════════════════════════════════════
# PLOT 1 — Severity Distribution (Bar)
# ══════════════════════════════════════════════════════════════
print("\n[1/10] Severity distribution...")
fig, ax = plt.subplots(figsize=(8, 5))
sev_counts = df_class["severity_label"].value_counts().reindex(
    ["Critical","High","Medium","Low"])
bars = ax.bar(sev_counts.index,
              sev_counts.values,
              color=[SEV_COLORS[s] for s in sev_counts.index],
              width=0.55, edgecolor="none")
for bar, val in zip(bars, sev_counts.values):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
            f"{val}\n({val/len(df_class)*100:.1f}%)",
            ha="center", va="bottom", fontsize=10, color="#dce8f5")
ax.set_title("Station Severity Distribution (LMPI Classification)")
ax.set_ylabel("Number of Stations")
ax.set_ylim(0, sev_counts.max() + 8)
ax.grid(axis="y")
ax.set_axisbelow(True)
plt.tight_layout()
plt.savefig(os.path.join(PLOTS, "01_severity_distribution.png"), dpi=150)
plt.close()
print("  ✅ 01_severity_distribution.png")

# ══════════════════════════════════════════════════════════════
# PLOT 2 — LMPI Score Distribution (Histogram + KDE)
# ══════════════════════════════════════════════════════════════
print("[2/10] LMPI distribution...")
fig, ax = plt.subplots(figsize=(9, 5))
for sev, color in SEV_COLORS.items():
    subset = df_class[df_class["severity_label"] == sev]["lmpi_score"]
    ax.hist(subset, bins=12, alpha=0.7, color=color,
            label=f"{sev} (n={len(subset)})", edgecolor="none")
# Threshold lines
for thresh, label in [(64,"Critical"), (52,"High"), (38,"Medium")]:
    ax.axvline(thresh, color="#dce8f5", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.text(thresh+0.5, ax.get_ylim()[1]*0.85, label,
            fontsize=8, color="#dce8f5", alpha=0.7)
ax.set_title("LMPI Score Distribution by Severity")
ax.set_xlabel("LMPI Score (0–100)")
ax.set_ylabel("Number of Stations")
ax.legend(loc="upper left")
ax.grid(axis="y")
plt.tight_layout()
plt.savefig(os.path.join(PLOTS, "02_lmpi_distribution.png"), dpi=150)
plt.close()
print("  ✅ 02_lmpi_distribution.png")

# ══════════════════════════════════════════════════════════════
# PLOT 3 — LMPI by Line (Box Plot)
# ══════════════════════════════════════════════════════════════
print("[3/10] LMPI by line...")
fig, ax = plt.subplots(figsize=(8, 5))
lines = ["1","2A","7","3"]
data  = [df_class[df_class["line"]==l]["lmpi_score"].values for l in lines]
bp = ax.boxplot(data, patch_artist=True, widths=0.5,
                medianprops=dict(color="#dce8f5", linewidth=2))
for patch, line in zip(bp["boxes"], lines):
    patch.set_facecolor(LINE_COLORS[line])
    patch.set_alpha(0.75)
for element in ["whiskers","caps","fliers"]:
    for item in bp[element]:
        item.set_color("#7a9bbf")
ax.set_xticklabels([f"Line {l}" for l in lines])
ax.set_title("LMPI Score Distribution by Metro Line")
ax.set_ylabel("LMPI Score")
ax.grid(axis="y")
plt.tight_layout()
plt.savefig(os.path.join(PLOTS, "03_lmpi_by_line.png"), dpi=150)
plt.close()
print("  ✅ 03_lmpi_by_line.png")

# ══════════════════════════════════════════════════════════════
# PLOT 4 — Top 15 Stations by LMPI Score (Horizontal Bar)
# ══════════════════════════════════════════════════════════════
print("[4/10] Top stations by LMPI...")
fig, ax = plt.subplots(figsize=(10, 7))
top15 = df_class.nlargest(15, "lmpi_score")[["station_name","line","lmpi_score","severity_label"]]
colors = [SEV_COLORS[s] for s in top15["severity_label"]]
bars = ax.barh(top15["station_name"], top15["lmpi_score"],
               color=colors, edgecolor="none", height=0.65)
for bar, (_, row) in zip(bars, top15.iterrows()):
    ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
            f"{row['lmpi_score']:.1f}  Line {row['line']}",
            va="center", fontsize=9, color="#dce8f5")
ax.axvline(64, color="#ff3b55", linestyle="--", linewidth=0.8, alpha=0.7, label="Critical threshold")
ax.set_title("Top 15 Stations by LMPI Score")
ax.set_xlabel("LMPI Score")
ax.set_xlim(0, 100)
ax.invert_yaxis()
ax.grid(axis="x")
ax.legend()
plt.tight_layout()
plt.savefig(os.path.join(PLOTS, "04_top_stations_lmpi.png"), dpi=150)
plt.close()
print("  ✅ 04_top_stations_lmpi.png")

# ══════════════════════════════════════════════════════════════
# PLOT 5 — LMPI Factor Comparison (Radar / Bar)
# ══════════════════════════════════════════════════════════════
print("[5/10] Factor comparison by severity...")
fig, ax = plt.subplots(figsize=(10, 5))
factors = ["auto_problem_score","walking_problem_score",
           "bus_problem_score","crowding_score","safety_score"]
factor_labels = ["Auto","Walking","Bus","Crowding","Safety"]
x = np.arange(len(factors))
width = 0.2
for i, (sev, color) in enumerate(SEV_COLORS.items()):
    means = df_class[df_class["severity_label"]==sev][factors].mean().values
    ax.bar(x + i*width, means, width, label=sev, color=color,
           alpha=0.8, edgecolor="none")
ax.set_xticks(x + width*1.5)
ax.set_xticklabels(factor_labels)
ax.set_title("Average LMPI Factor Scores by Severity")
ax.set_ylabel("Problem Score (0–100)")
ax.legend()
ax.grid(axis="y")
ax.set_axisbelow(True)
plt.tight_layout()
plt.savefig(os.path.join(PLOTS, "05_factor_comparison.png"), dpi=150)
plt.close()
print("  ✅ 05_factor_comparison.png")

# ══════════════════════════════════════════════════════════════
# PLOT 6 — Correlation Heatmap
# ══════════════════════════════════════════════════════════════
print("[6/10] Correlation heatmap...")
corr_cols = [
    "lmpi_score","auto_problem_score","walking_problem_score",
    "bus_problem_score","crowding_score","safety_score",
    "pop_density","auto_supply_score","bus_connectivity_score",
    "is_interchange","survey_satisfaction",
]
corr = df_class[corr_cols].corr()
fig, ax = plt.subplots(figsize=(10, 8))
mask = np.triu(np.ones_like(corr, dtype=bool))
cmap = sns.diverging_palette(220, 10, as_cmap=True)
sns.heatmap(corr, mask=mask, cmap=cmap, center=0,
            annot=True, fmt=".2f", annot_kws={"size":8},
            linewidths=0.5, linecolor="#1e3050",
            ax=ax, cbar_kws={"shrink":0.7})
ax.set_title("Feature Correlation Matrix")
plt.xticks(rotation=45, ha="right", fontsize=8)
plt.yticks(rotation=0, fontsize=8)
plt.tight_layout()
plt.savefig(os.path.join(PLOTS, "06_correlation_heatmap.png"), dpi=150)
plt.close()
print("  ✅ 06_correlation_heatmap.png")

# ══════════════════════════════════════════════════════════════
# PLOT 7 — 5-Year Ridership Trend by Line
# ══════════════════════════════════════════════════════════════
print("[7/10] 5-year ridership trend...")
fig, ax = plt.subplots(figsize=(12, 5))
df_trend = df_hist.copy()
df_trend["year_month"] = df_trend["date"].dt.to_period("M")
for line, color in LINE_COLORS.items():
    subset = df_trend[df_trend["line"]==line].groupby("year_month")["footfall"].sum().reset_index()
    subset["year_month"] = subset["year_month"].dt.to_timestamp()
    ax.plot(subset["year_month"], subset["footfall"]/1e5,
            color=color, linewidth=1.5, label=f"Line {line}", alpha=0.9)
ax.set_title("Monthly Ridership Trend by Line (2019–2025)")
ax.set_ylabel("Total Footfall (Lakhs)")
ax.set_xlabel("Month")
ax.legend()
ax.grid(True)
ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0fL"))
# Mark COVID period
ax.axvspan(pd.Timestamp("2020-03-01"), pd.Timestamp("2021-06-01"),
           alpha=0.15, color="#ff3b55", label="COVID period")
plt.xticks(rotation=30)
plt.tight_layout()
plt.savefig(os.path.join(PLOTS, "07_ridership_trend.png"), dpi=150)
plt.close()
print("  ✅ 07_ridership_trend.png")

# ══════════════════════════════════════════════════════════════
# PLOT 8 — Festival Impact on Footfall
# ══════════════════════════════════════════════════════════════
print("[8/10] Festival impact...")
fig, ax = plt.subplots(figsize=(9, 5))
df_hist["is_festival"] = df_hist["is_festival"].fillna(0)
fest_impact = df_hist.groupby(["festival_name","is_festival"])["footfall"].mean().reset_index()
fest_days   = df_hist[df_hist["is_festival"]==1].groupby("festival_name")["footfall"].mean()
normal_avg  = df_hist[df_hist["is_festival"]==0]["footfall"].mean()
boost_pct   = ((fest_days - normal_avg) / normal_avg * 100).sort_values(ascending=False)
boost_pct   = boost_pct[boost_pct.index != "none"]
colors_fest = ["#ff3b55" if v > 30 else "#ff6b35" if v > 15 else "#ffc832"
               for v in boost_pct.values]
bars = ax.bar(boost_pct.index, boost_pct.values,
              color=colors_fest, edgecolor="none", width=0.5)
for bar, val in zip(bars, boost_pct.values):
    ax.text(bar.get_x() + bar.get_width()/2,
            bar.get_height() + 0.3,
            f"+{val:.1f}%", ha="center", va="bottom", fontsize=10)
ax.axhline(0, color="#dce8f5", linewidth=0.8)
ax.set_title("Average Ridership Boost During Festivals vs Normal Days")
ax.set_ylabel("Footfall Increase (%)")
ax.grid(axis="y")
ax.set_axisbelow(True)
plt.xticks(rotation=20)
plt.tight_layout()
plt.savefig(os.path.join(PLOTS, "08_festival_impact.png"), dpi=150)
plt.close()
print("  ✅ 08_festival_impact.png")

# ══════════════════════════════════════════════════════════════
# PLOT 9 — Monsoon Impact on Ridership
# ══════════════════════════════════════════════════════════════
print("[9/10] Monsoon impact...")
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

# Left: Monthly avg footfall
monthly = df_hist.groupby(df_hist["date"].dt.month)["footfall"].mean()
month_names = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
colors_mon = ["#2e8fff" if m not in [6,7,8,9] else "#a55eea" for m in range(1,13)]
axes[0].bar(month_names, monthly.values/1000,
            color=colors_mon, edgecolor="none", width=0.65)
axes[0].set_title("Avg Daily Footfall by Month")
axes[0].set_ylabel("Avg Footfall (000s)")
axes[0].grid(axis="y")
# Highlight monsoon
for i, m in enumerate(month_names):
    if m in ["Jun","Jul","Aug","Sep"]:
        axes[0].get_xticklabels()
axes[0].set_axisbelow(True)

# Right: Elevated vs non-elevated during monsoon
df_hist_ext = df_hist.merge(
    pd.read_csv(os.path.join(RAW,"01_station_master.csv"))[["station_name","is_elevated"]],
    on="station_name", how="left"
)
df_hist_ext["month"] = df_hist_ext["date"].dt.month
df_hist_ext["is_monsoon"] = df_hist_ext["month"].isin([6,7,8,9]).astype(int)
elev_comp = df_hist_ext.groupby(["is_elevated","is_monsoon"])["footfall"].mean().reset_index()
elev_comp["label"] = elev_comp.apply(
    lambda r: f"{'Elevated' if r['is_elevated'] else 'Underground'}\n{'Monsoon' if r['is_monsoon'] else 'Dry'}",
    axis=1
)
bar_colors = ["#2e8fff","#a55eea","#2e8fff","#a55eea"]
axes[1].bar(elev_comp["label"], elev_comp["footfall"]/1000,
            color=bar_colors, alpha=0.8, edgecolor="none", width=0.55)
axes[1].set_title("Elevated vs Underground: Monsoon Effect")
axes[1].set_ylabel("Avg Footfall (000s)")
axes[1].grid(axis="y")
axes[1].set_axisbelow(True)

plt.suptitle("Monsoon Impact on Mumbai Metro Ridership", fontsize=13, y=1.01)
plt.tight_layout()
plt.savefig(os.path.join(PLOTS, "09_monsoon_impact.png"), dpi=150, bbox_inches="tight")
plt.close()
print("  ✅ 09_monsoon_impact.png")

# ══════════════════════════════════════════════════════════════
# PLOT 10 — Last-Mile Mode Recommendation Distribution
# ══════════════════════════════════════════════════════════════
print("[10/10] Last-mile recommendations...")
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

# Left: Overall pie
# Load last mile from lmpi scores
df_lmpi_lm = pd.read_csv(os.path.join(DER, "04_lmpi_scores.csv"))
df_class_lm = df_class.merge(df_lmpi_lm[["station_name","recommended_last_mile"]], on="station_name", how="left")
lm_counts = df_class_lm["recommended_last_mile"].value_counts()
lm_colors = ["#2e8fff","#22d98a","#ffc832","#ff6b35","#a55eea"]
axes[0].pie(lm_counts.values, labels=lm_counts.index,
            colors=lm_colors[:len(lm_counts)],
            autopct="%1.1f%%", startangle=140,
            wedgeprops={"edgecolor":"#0e1525","linewidth":1.5},
            textprops={"color":"#dce8f5","fontsize":9})
axes[0].set_title("Last-Mile Mode Recommendations\n(All Stations)")

# Right: By severity
lm_sev = df_class_lm.groupby(["severity_label","recommended_last_mile"]).size().unstack(fill_value=0)
lm_sev = lm_sev.reindex(["Critical","High","Medium","Low"])
lm_sev.plot(kind="bar", ax=axes[1], color=lm_colors[:len(lm_sev.columns)],
            edgecolor="none", width=0.6)
axes[1].set_title("Last-Mile Mode by Severity Level")
axes[1].set_ylabel("Number of Stations")
axes[1].set_xlabel("")
axes[1].legend(title="Mode", fontsize=8, title_fontsize=8)
axes[1].tick_params(axis="x", rotation=0)
axes[1].grid(axis="y")
axes[1].set_axisbelow(True)

plt.suptitle("Last-Mile Connectivity Recommendations", fontsize=13, y=1.01)
plt.tight_layout()
plt.savefig(os.path.join(PLOTS, "10_lastmile_recommendations.png"), dpi=150, bbox_inches="tight")
plt.close()
print("  ✅ 10_lastmile_recommendations.png")

# ── FINAL SUMMARY ─────────────────────────────────────────────
print("\n" + "=" * 55)
print("  EDA COMPLETE — 10 plots saved")
print("=" * 55)
print(f"\n  Location: Outputs/Plots/")
for i, f in enumerate(sorted(os.listdir(PLOTS)), 1):
    print(f"  {f}")

print(f"\n  Key Findings:")
print(f"  • Critical stations : {(df_class['severity_label']=='Critical').sum()} ({(df_class['severity_label']=='Critical').sum()/len(df_class)*100:.1f}%)")
print(f"  • High stations     : {(df_class['severity_label']=='High').sum()} ({(df_class['severity_label']=='High').sum()/len(df_class)*100:.1f}%)")
print(f"  • Avg LMPI score    : {df_class['lmpi_score'].mean():.1f}")
print(f"  • Most common mode  : {df_class_lm['recommended_last_mile'].mode()[0]}")
print(f"  • Top critical stn  : {df_class.nlargest(1,'lmpi_score')['station_name'].values[0]}")