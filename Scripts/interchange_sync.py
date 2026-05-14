# ============================================================
# interchange_sync.py
# Metro ↔ Metro Interchange Synchronization
# Stations : Marol Naka (L1↔L3), DN Nagar (L1↔L2A),
#            Gundavali (L1↔L7)
# Logic    : Walk 10 min + Wait ≤ 2 min = 12 min total
# Input    : Data/Derived/06_frequency_optimization.csv
#            Data/Derived/04_lmpi_scores.csv
# Output   : Outputs/Results/layer4_interchange_sync.csv
#            Outputs/Plots/26_interchange_sync.png
# ============================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")
import os
import warnings
warnings.filterwarnings("ignore")

BASE    = r"C:\Users\parek\Downloads\LY Project"
DER     = os.path.join(BASE, "Data", "Derived")
RESULTS = os.path.join(BASE, "Outputs", "Results")
PLOTS   = os.path.join(BASE, "Outputs", "Plots")
os.makedirs(RESULTS, exist_ok=True)
os.makedirs(PLOTS,   exist_ok=True)

# ── Style ─────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.facecolor": "#f4f6f9",
    "axes.facecolor":   "#ffffff",
    "axes.edgecolor":   "#e2e7ef",
    "axes.labelcolor":  "#0f1923",
    "axes.titlecolor":  "#0f1923",
    "axes.titlesize":   12,
    "xtick.color":      "#4a5568",
    "ytick.color":      "#4a5568",
    "text.color":       "#0f1923",
    "grid.color":       "#e2e7ef",
    "grid.linestyle":   "--",
    "grid.alpha":       0.6,
    "font.family":      "monospace",
    "legend.facecolor": "#ffffff",
    "legend.edgecolor": "#e2e7ef",
})

print("=" * 60)
print("  INTERCHANGE SYNC — Mumbai Metro (Metro ↔ Metro Only)")
print("=" * 60)

# ══════════════════════════════════════════════════════════════
# STEP 1: Define all parameters
# ══════════════════════════════════════════════════════════════
print("\n[1/6] Loading parameters...")

# ── Journey time constants ────────────────────────────────────
WALK_TIME_MIN   = 10    # platform to platform walk (fixed)
MAX_WAIT_MIN    = 2     # maximum acceptable waiting time
TOTAL_MAX_MIN   = 12    # 10 walk + 2 wait = 12 min total

# ── Metro ↔ Metro interchange stations only ───────────────────
INTERCHANGES = [
    {
        "station":   "Marol Naka",
        "line_a":    "1",
        "line_b":    "3",
        "direction": "Line 1 → Line 3 (Aqua)"
    },
    {
        "station":   "DN Nagar",
        "line_a":    "1",
        "line_b":    "2A",
        "direction": "Line 1 → Line 2A"
    },
    {
        "station":   "Gundavali",
        "line_a":    "1",
        "line_b":    "7",
        "direction": "Line 1 → Line 7"
    },
]

# ── Real MMRDA published headways (minutes) ───────────────────
# Source: MMRDA official timetables
HEADWAYS = {
    "1":  {"peak": 3.5,  "offpeak": 6.5},
    "2A": {"peak": 5.5,  "offpeak": 8.5},
    "7":  {"peak": 5.5,  "offpeak": 9.0},
    "3":  {"peak": 6.0,  "offpeak": 9.0},
}

# ── Time windows ──────────────────────────────────────────────
TIME_WINDOWS = {
    "morning_peak":  {"day_type": "weekday", "hours": "8am–11am",  "is_peak": True},
    "evening_peak":  {"day_type": "weekday", "hours": "5pm–9pm",   "is_peak": True},
    "weekday_off":   {"day_type": "weekday", "hours": "rest of day","is_peak": False},
    "weekend_peak":  {"day_type": "weekend", "hours": "12pm–9pm",  "is_peak": True},
    "weekend_off":   {"day_type": "weekend", "hours": "rest of day","is_peak": False},
}

# ── Festival + holiday headway multipliers ────────────────────
# Lower multiplier = shorter headway = more trains = better sync
EVENT_MULTIPLIERS = {
    "Ganesh Chaturthi": 0.80,   # +20% trains
    "Diwali":           0.82,   # +18% trains
    "New Year":         0.83,   # +17% trains
    "Eid":              0.85,   # +15% trains
    "Navratri":         0.85,   # +15% trains
    "Public Holiday":   0.88,   # +12% trains
    "Normal":           1.00,   # standard
}

# ── Rain headway multipliers ──────────────────────────────────
# Rain increases ridership → MMRDA deploys more trains
RAIN_MULTIPLIERS = {
    "heavy":    0.85,   # +15% trains during heavy rain
    "moderate": 0.90,   # +10% trains
    "light":    0.97,   # +3% trains
    "none":     1.00,
}

# ── Sync quality thresholds ───────────────────────────────────
def get_sync_quality(wait_min):
    if wait_min <= 1.0:   return "Excellent", "✅"
    elif wait_min <= 2.0: return "Good",      "✅"
    else:                 return "Poor",      "❌"

print(f"  Interchange stations : {len(INTERCHANGES)}")
print(f"  Time windows         : {len(TIME_WINDOWS)}")
print(f"  Walk time            : {WALK_TIME_MIN} min (fixed)")
print(f"  Max wait target      : {MAX_WAIT_MIN} min")
print(f"  Total journey target : {TOTAL_MAX_MIN} min")

# ══════════════════════════════════════════════════════════════
# STEP 2: Core sync calculation function
# ══════════════════════════════════════════════════════════════
print("\n[2/6] Computing sync calculations...")

def compute_sync(headway_a, headway_b):
    """
    Realistic sync model:
    - Commuters arrive at Line B platform continuously
      staggered by Line A headway (every headway_a minutes)
    - Each commuter arrives at T + 10 + k*headway_a
      for k = 0, 1, 2, 3...
    - Calculate actual wait for each commuter arrival
    - Average = realistic expected wait
    - With optimal offset: shift Line B cycle to minimize
      this average across all staggered arrivals
    """
    commuter_arrives = WALK_TIME_MIN  # 10 min fixed

    # Simulate commuters arriving over one full Line B cycle
    # (after that pattern repeats)
    simulation_window = headway_b * 3  # 3 full Line B cycles
    
    # Commuter arrival times at Line B platform
    # staggered by Line A headway
    commuter_times = []
    t = commuter_arrives
    while t <= commuter_arrives + simulation_window:
        commuter_times.append(t)
        t += headway_a

    # ── WITHOUT SYNC ─────────────────────────────────────────
    # Line B departs at: 0, headway_b, 2*headway_b...
    # (no special timing, just regular schedule)
    def get_wait(arrival_time, offset_min, hw_b):
        # Find next Line B departure after arrival
        # departures at offset_min, offset_min+hw_b, offset_min+2*hw_b...
        if arrival_time < offset_min:
            return offset_min - arrival_time
        cycles = int((arrival_time - offset_min) / hw_b)
        next_dep = offset_min + (cycles + 1) * hw_b
        wait = next_dep - arrival_time
        return round(wait, 3)

    # Without sync — offset = 0 (Line B runs on its own schedule)
    waits_without = [get_wait(ct, 0, headway_b) for ct in commuter_times]
    avg_wait_without = round(np.mean(waits_without), 2)
    max_wait_without = round(np.max(waits_without), 2)

    # ── WITH OPTIMAL SYNC ─────────────────────────────────────
    # Find the best offset (0 to headway_b) that minimizes
    # average wait across all staggered commuter arrivals
    best_offset_min = 0
    best_avg_wait   = 999
    best_max_wait   = 999

    # Test offsets in 0.1 min increments
    for offset_test in np.arange(0, headway_b, 0.1):
        waits_test = [get_wait(ct, offset_test, headway_b)
                      for ct in commuter_times]
        avg_test = np.mean(waits_test)
        if avg_test < best_avg_wait:
            best_avg_wait   = avg_test
            best_max_wait   = np.max(waits_test)
            best_offset_min = offset_test

    avg_wait_with = round(best_avg_wait, 2)
    max_wait_with = round(best_max_wait, 2)
    optimal_offset_sec = round(best_offset_min * 60)

    return (avg_wait_without, max_wait_without,
            optimal_offset_sec, avg_wait_with, max_wait_with)

# ══════════════════════════════════════════════════════════════
# STEP 3: Generate all rows
# ══════════════════════════════════════════════════════════════
print("\n[3/6] Generating sync recommendations...")

rows = []

for ic in INTERCHANGES:
    station  = ic["station"]
    line_a   = ic["line_a"]
    line_b   = ic["line_b"]
    direction= ic["direction"]

    for window, winfo in TIME_WINDOWS.items():
        is_peak  = winfo["is_peak"]
        day_type = winfo["day_type"]
        hours    = winfo["hours"]

        # Base headways from MMRDA
        hw_type = "peak" if is_peak else "offpeak"
        base_hw_a = HEADWAYS[line_a][hw_type]
        base_hw_b = HEADWAYS[line_b][hw_type]

        # Generate variants — Normal + Festival + Rain
        variants = [
            ("Normal",           EVENT_MULTIPLIERS["Normal"],           RAIN_MULTIPLIERS["none"]),
            ("Ganesh Chaturthi", EVENT_MULTIPLIERS["Ganesh Chaturthi"], RAIN_MULTIPLIERS["none"]),
            ("Diwali",           EVENT_MULTIPLIERS["Diwali"],           RAIN_MULTIPLIERS["none"]),
            ("Public Holiday",   EVENT_MULTIPLIERS["Public Holiday"],   RAIN_MULTIPLIERS["none"]),
            ("Heavy Rain",       EVENT_MULTIPLIERS["Normal"],           RAIN_MULTIPLIERS["heavy"]),
            ("Moderate Rain",    EVENT_MULTIPLIERS["Normal"],           RAIN_MULTIPLIERS["moderate"]),
        ]

        for event_type, event_mult, rain_mult in variants:
            # Apply multipliers — both lines get more trains
            combined_mult = event_mult * rain_mult
            hw_a = round(base_hw_a * combined_mult, 2)
            hw_b = round(base_hw_b * combined_mult, 2)

            # Trains per hour
            trains_hr_a = round(60 / hw_a, 1)
            trains_hr_b = round(60 / hw_b, 1)

            # Compute sync
            (wait_without, max_without,offset_sec, wait_with, max_with) = compute_sync(hw_a, hw_b)

            # Sync quality
            quality, emoji = get_sync_quality(wait_with)

            # Total journey
            total_journey = round(WALK_TIME_MIN + wait_with, 1)
            within_target = total_journey <= TOTAL_MAX_MIN

            # Recommendation
            if quality == "Poor":
                rec = (f"Increase Line {line_b} frequency to reduce headway below "
                       f"{MAX_WAIT_MIN*2:.0f} min OR hold train {offset_sec}s after "
                       f"Line {line_a} arrival")
            elif offset_sec > 0:
                rec = (f"Hold Line {line_b} train {offset_sec}s after "
                       f"Line {line_a} arrival — commuter wait {wait_with} min ✅")
            else:
                rec = (f"No adjustment needed — Line {line_b} frequency "
                       f"sufficient at {hw_b} min headway ✅")

            rows.append({
                "station":                  station,
                "direction":                direction,
                "line_a":                   line_a,
                "line_b":                   line_b,
                "time_window":              window,
                "day_type":                 day_type,
                "hours":                    hours,
                "event_type":               event_type,
                "is_peak":                  int(is_peak),
                "line_a_headway_min":       hw_a,
                "line_b_headway_min":       hw_b,
                "line_a_trains_per_hr":     trains_hr_a,
                "line_b_trains_per_hr":     trains_hr_b,
                "walk_time_min":            WALK_TIME_MIN,
                "avg_wait_without_sync_min":wait_without,
                "max_wait_without_sync_min": max_without,
                "optimal_offset_sec":       offset_sec,
                "avg_wait_with_sync_min":   wait_with,
                "max_wait_with_sync_min":    max_with,
                "total_journey_min":         round(WALK_TIME_MIN + wait_with, 1),
                "worst_case_journey_min":    round(WALK_TIME_MIN + max_with, 1),
                "within_12min_target":       round(WALK_TIME_MIN + wait_with, 1) <= TOTAL_MAX_MIN,
                "sync_quality":             quality,
                "recommendation":           rec,
            })

df_sync = pd.DataFrame(rows)

# ══════════════════════════════════════════════════════════════
# STEP 4: Print summary
# ══════════════════════════════════════════════════════════════
print("\n[4/6] Results summary...")
print(f"\n  Total rows generated : {len(df_sync)}")

# Normal weekday peak summary
normal_peak = df_sync[
    (df_sync["event_type"] == "Normal") &
    (df_sync["time_window"].isin(["morning_peak","evening_peak"]))
]

print(f"\n  {'─'*58}")
print(f"  NORMAL WEEKDAY PEAK — Sync Analysis")
print(f"  {'─'*58}")
print(f"  {'Station':<15} {'Direction':<22} {'Wait(no sync)':>14} {'Offset':>8} {'Wait(sync)':>11} {'Quality':>10}")
print(f"  {'─'*58}")

for _, row in normal_peak.drop_duplicates("station").iterrows():
    print(f"  {row['station']:<15} "
          f"L{row['line_a']}↔L{row['line_b']:<18} "
          f"{row['avg_wait_without_sync_min']:>12.1f}m "
          f"{row['optimal_offset_sec']:>6}s "
          f"{row['avg_wait_with_sync_min']:>9.1f}m "
          f"{row['sync_quality']:>10}")

print(f"\n  {'─'*58}")
print(f"  FESTIVAL DAY — Ganesh Chaturthi Peak")
print(f"  {'─'*58}")

fest_peak = df_sync[
    (df_sync["event_type"] == "Ganesh Chaturthi") &
    (df_sync["time_window"] == "evening_peak")
]
for _, row in fest_peak.iterrows():
    print(f"  {row['station']:<15} "
          f"Headway L{row['line_a']}: {row['line_a_headway_min']}m  "
          f"L{row['line_b']}: {row['line_b_headway_min']}m  "
          f"Wait: {row['avg_wait_with_sync_min']}m  "
          f"{row['sync_quality']}")

print(f"\n  {'─'*58}")
print(f"  HEAVY RAIN — Morning Peak")
print(f"  {'─'*58}")

rain_peak = df_sync[
    (df_sync["event_type"] == "Heavy Rain") &
    (df_sync["time_window"] == "morning_peak")
]
for _, row in rain_peak.iterrows():
    print(f"  {row['station']:<15} "
          f"Headway L{row['line_a']}: {row['line_a_headway_min']}m  "
          f"L{row['line_b']}: {row['line_b_headway_min']}m  "
          f"Wait: {row['avg_wait_with_sync_min']}m  "
          f"{row['sync_quality']}")

print(f"\n  {'─'*58}")
print(f"  ALL WINDOWS — Within 12 min target?")
print(f"  {'─'*58}")

for station in df_sync["station"].unique():
    st_data = df_sync[df_sync["station"] == station]
    within  = st_data["within_12min_target"].sum()
    total   = len(st_data)
    pct     = within/total*100
    print(f"  {station:<15} {within:>3}/{total} windows within 12 min ({pct:.0f}%)")

# ══════════════════════════════════════════════════════════════
# STEP 5: Save results
# ══════════════════════════════════════════════════════════════
print("\n[5/6] Saving results...")

df_sync.to_csv(
    os.path.join(RESULTS, "layer4_interchange_sync.csv"),
    index=False
)
print(f"  ✅ layer4_interchange_sync.csv — {len(df_sync)} rows")

# ══════════════════════════════════════════════════════════════
# STEP 6: Plot
# ══════════════════════════════════════════════════════════════
print("\n[6/6] Generating plot...")

fig, axes = plt.subplots(1, 3, figsize=(15, 6))
fig.suptitle(
    "Metro ↔ Metro Interchange Sync Analysis\n"
    "Walk: 10 min | Wait target: ≤ 2 min | Total target: ≤ 12 min",
    fontsize=13, fontweight="bold", y=1.01
)

WINDOWS_PLOT  = ["morning_peak","evening_peak","weekday_off","weekend_peak","weekend_off"]
WINDOW_LABELS = ["Morning\nPeak","Evening\nPeak","Weekday\nOff","Weekend\nPeak","Weekend\nOff"]
EVENTS_PLOT   = ["Normal","Ganesh Chaturthi","Diwali","Public Holiday","Heavy Rain","Moderate Rain"]
EVENT_COLORS  = ["#1565c0","#d63031","#e17055","#8e44ad","#27ae60","#00897b"]

for ax, ic in zip(axes, INTERCHANGES):
    station = ic["station"]
    st_data = df_sync[df_sync["station"] == station]

    x      = np.arange(len(WINDOWS_PLOT))
    width  = 0.13
    offset = -(len(EVENTS_PLOT)-1)/2 * width

    for j, (event, color) in enumerate(zip(EVENTS_PLOT, EVENT_COLORS)):
        ev_data = st_data[st_data["event_type"] == event]
        waits   = []
        for w in WINDOWS_PLOT:
            row = ev_data[ev_data["time_window"] == w]
            waits.append(row["avg_wait_with_sync_min"].values[0] if len(row) else 0)
        ax.bar(x + offset + j*width, waits, width,
               label=event, color=color, alpha=0.85, edgecolor="none")

    # Target line
    ax.axhline(MAX_WAIT_MIN, color="#d63031", linewidth=1.5,
               linestyle="--", label=f"{MAX_WAIT_MIN} min target")
    ax.axhline(1.0, color="#27ae60", linewidth=1,
               linestyle=":", alpha=0.7, label="Excellent threshold")

    ax.set_title(
        f"{station}\nLine {ic['line_a']} ↔ Line {ic['line_b']}",
        fontsize=11, fontweight="bold"
    )
    ax.set_ylabel("Wait Time (minutes)" if ax == axes[0] else "")
    ax.set_xticks(x)
    ax.set_xticklabels(WINDOW_LABELS, fontsize=8)
    ax.set_ylim(0, 4)
    ax.grid(axis="y", alpha=0.5)
    ax.set_axisbelow(True)

    # Color background by quality zone
    ax.axhspan(0,   1.0, alpha=0.04, color="#27ae60")  # Excellent
    ax.axhspan(1.0, 2.0, alpha=0.04, color="#1565c0")  # Good
    ax.axhspan(2.0, 4.0, alpha=0.04, color="#d63031")  # Poor

    # Zone labels
    ax.text(0.01, 0.5,  "Excellent", transform=ax.transAxes,
            fontsize=7, color="#27ae60", alpha=0.7)
    ax.text(0.01, 0.62, "Good",      transform=ax.transAxes,
            fontsize=7, color="#1565c0", alpha=0.7)
    ax.text(0.01, 0.80, "Poor",      transform=ax.transAxes,
            fontsize=7, color="#d63031", alpha=0.7)

handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels,
           loc="lower center", ncol=4,
           fontsize=8, framealpha=0.9,
           bbox_to_anchor=(0.5, -0.08))

plt.tight_layout()
plt.savefig(
    os.path.join(PLOTS, "26_interchange_sync.png"),
    dpi=150, bbox_inches="tight"
)
plt.close()
print("  ✅ 26_interchange_sync.png")

# ══════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  INTERCHANGE SYNC COMPLETE")
print("=" * 60)

normal_peak_only = df_sync[
    (df_sync["event_type"] == "Normal") &
    (df_sync["time_window"] == "morning_peak")
]

print(f"\n  Stations analyzed    : {df_sync['station'].nunique()}")
print(f"  Total rows           : {len(df_sync)}")
print(f"  Walk time            : {WALK_TIME_MIN} min (fixed)")
print(f"  Max wait target      : {MAX_WAIT_MIN} min")
print(f"  Total journey target : {TOTAL_MAX_MIN} min")

print(f"\n  Normal Morning Peak Results:")
print(f"  {'Station':<15} {'Avg(no sync)':>13} {'Worst(no sync)':>15} {'Avg(sync)':>10} {'Worst(sync)':>12} {'Quality':>10} {'Total avg':>10}")
print(f"  {'─'*90}")
for _, row in normal_peak_only.iterrows():
    emoji = "✅" if row["within_12min_target"] else "❌"
    print(f"  {emoji} {row['station']:<13} "
          f"{row['avg_wait_without_sync_min']:>10.2f}m "
          f"{row['max_wait_without_sync_min']:>14.2f}m "
          f"{row['avg_wait_with_sync_min']:>9.2f}m "
          f"{row['max_wait_with_sync_min']:>11.2f}m "
          f"{row['sync_quality']:>10}  "
          f"{row['total_journey_min']:>7.1f} min")

print(f"\n  Worst Case Journey (Walk 10 + Max Wait):")
for _, row in normal_peak_only.iterrows():
    emoji = "✅" if row["worst_case_journey_min"] <= TOTAL_MAX_MIN else "❌"
    print(f"  {emoji} {row['station']:<15} "
          f"Worst case: {row['worst_case_journey_min']} min "
          f"({'within' if row['worst_case_journey_min'] <= TOTAL_MAX_MIN else 'EXCEEDS'} "
          f"{TOTAL_MAX_MIN} min target)")

print(f"\n  Key Recommendations:")
for _, row in normal_peak_only.iterrows():
    print(f"\n  {row['station']} (L{row['line_a']} ↔ L{row['line_b']}):")
    print(f"  → Avg wait without sync : {row['avg_wait_without_sync_min']} min")
    print(f"  → Worst wait without    : {row['max_wait_without_sync_min']} min")
    print(f"  → After sync offset     : avg {row['avg_wait_with_sync_min']} min, worst {row['max_wait_with_sync_min']} min")
    print(f"  → {row['recommendation']}")

print(f"\n  Saved:")
print(f"  ├── Outputs/Results/layer4_interchange_sync.csv")
print(f"  └── Outputs/Plots/26_interchange_sync.png")