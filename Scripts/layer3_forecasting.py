# ============================================================
# layer3_forecasting.py
# Layer 3 — Footfall Forecasting
# Models : Prophet + XGBoost
# Input  : Data/Derived/13_forecasting_features.csv
#          Data/Derived/04_lmpi_scores.csv
# Output : Models/ + Outputs/Results/ + Outputs/Plots/
# ============================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")
import seaborn as sns
import os
import joblib
import warnings
warnings.filterwarnings("ignore")

from sklearn.metrics          import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection  import TimeSeriesSplit
from xgboost                  import XGBRegressor
from prophet                  import Prophet

BASE    = r"C:\Users\parek\Downloads\LY Project"
DER     = os.path.join(BASE, "Data", "Derived")
MODELS  = os.path.join(BASE, "Models")
RESULTS = os.path.join(BASE, "Outputs", "Results")
PLOTS   = os.path.join(BASE, "Outputs", "Plots")
os.makedirs(MODELS,  exist_ok=True)
os.makedirs(RESULTS, exist_ok=True)

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

LINE_COLORS = {"1":"#f7b731","2A":"#20bf6b","7":"#a55eea","3":"#2e8fff"}

print("=" * 55)
print("  LAYER 3 — FOOTFALL FORECASTING")
print("=" * 55)

# ── STEP 1: Load data ─────────────────────────────────────────
print("\n[1/8] Loading forecasting features...")
df = pd.read_csv(os.path.join(DER, "13_forecasting_features.csv"))
df["date"] = pd.to_datetime(df["date"])

# Remove COVID rows for clean training
df = df[df["is_covid"] == 0].copy()
df = df.sort_values(["station_name","date"]).reset_index(drop=True)

print(f"  Total rows   : {len(df):,}")
print(f"  Stations     : {df['station_name'].nunique()}")
print(f"  Lines        : {df['line'].unique().tolist()}")
print(f"  Date range   : {df['date'].min().date()} → {df['date'].max().date()}")

# ── STEP 2: Define features ───────────────────────────────────
print("\n[2/8] Defining feature sets...")

XGB_FEATURES = [
    "year","month","day_of_week","day_of_year","week_of_year","quarter",
    "is_weekday","is_weekend","is_month_start","is_month_end",
    "month_sin","month_cos","dow_sin","dow_cos","doy_sin","doy_cos",
    "lag_1d","lag_7d","lag_30d","rolling_7d_avg","rolling_30d_avg",
    "wow_change","mom_change",
    "is_monsoon","monsoon_intensity_enc","rainfall_mm","rain_ridership_boost",
    "is_festival","festival_boost","is_public_holiday","external_boost",
    "monsoon_elevated","festival_weekend",
    "is_interchange","is_elevated","pop_density","lmpi_score","severity_encoded",
    "line_growth_rate","years_operational",
    "station_line_share",
]

# Keep only available columns
XGB_FEATURES = [f for f in XGB_FEATURES if f in df.columns]
print(f"  XGBoost features : {len(XGB_FEATURES)}")

# ── STEP 3: Train XGBoost (all stations combined) ────────────
print("\n[3/8] Training XGBoost forecaster...")

# Encode station name
df["station_enc"] = df["station_name"].astype("category").cat.codes

XGB_FEATURES_FULL = XGB_FEATURES + ["station_enc"]

X_all = df[XGB_FEATURES_FULL].fillna(0)
y_all = df["footfall"]

# Time-series split — last 20% as test
split_idx = int(len(df) * 0.80)
X_train, X_test = X_all.iloc[:split_idx], X_all.iloc[split_idx:]
y_train, y_test = y_all.iloc[:split_idx], y_all.iloc[split_idx:]

xgb_reg = XGBRegressor(
    n_estimators=300,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    min_child_weight=5,
    random_state=42,
    verbosity=0,
)
xgb_reg.fit(X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False)

y_pred_xgb = xgb_reg.predict(X_test)

mae_xgb  = mean_absolute_error(y_test, y_pred_xgb)
rmse_xgb = np.sqrt(mean_squared_error(y_test, y_pred_xgb))
r2_xgb   = r2_score(y_test, y_pred_xgb)
mape_xgb = np.mean(np.abs((y_test - y_pred_xgb) / (y_test + 1))) * 100

print(f"  MAE  : {mae_xgb:,.0f} passengers")
print(f"  RMSE : {rmse_xgb:,.0f} passengers")
print(f"  R²   : {r2_xgb:.4f}")
print(f"  MAPE : {mape_xgb:.2f}%")

joblib.dump(xgb_reg, os.path.join(MODELS, "xgb_forecaster.pkl"))
print(f"  ✅ Saved: Models/xgb_forecaster.pkl")

# ── STEP 4: Prophet (per high-footfall station) ───────────────
print("\n[4/8] Training Prophet models (top 6 stations)...")

# Select top stations by avg footfall
top_stations = (df.groupby("station_name")["footfall"]
                  .mean()
                  .nlargest(6)
                  .index.tolist())
print(f"  Stations: {top_stations}")

prophet_results = {}
prophet_forecasts = {}

for station in top_stations:
    st_df = df[df["station_name"] == station][["date","footfall",
             "is_festival","is_monsoon","is_public_holiday"]].copy()
    st_df = st_df.rename(columns={"date":"ds","footfall":"y"})
    st_df = st_df.sort_values("ds").reset_index(drop=True)

    # Train/test split — last 60 days as test
    train_p = st_df.iloc[:-60]
    test_p  = st_df.iloc[-60:]

    m = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        seasonality_mode="multiplicative",
        changepoint_prior_scale=0.1,
        seasonality_prior_scale=10,
    )
    # Add custom regressors
    m.add_regressor("is_festival")
    m.add_regressor("is_monsoon")
    m.add_regressor("is_public_holiday")

    m.fit(train_p)

    # Predict on test period
    future = test_p[["ds","is_festival","is_monsoon","is_public_holiday"]].copy()
    forecast = m.predict(future)

    y_true = test_p["y"].values
    y_pred = forecast["yhat"].values

    mae_p  = mean_absolute_error(y_true, y_pred)
    mape_p = np.mean(np.abs((y_true - y_pred) / (y_true + 1))) * 100
    r2_p   = r2_score(y_true, y_pred)

    prophet_results[station] = {
        "mae": mae_p, "mape": mape_p, "r2": r2_p
    }
    prophet_forecasts[station] = {
        "model": m, "test_df": test_p,
        "forecast": forecast, "train_df": train_p
    }

    print(f"  {station:<20} MAE: {mae_p:>7,.0f}  MAPE: {mape_p:.1f}%  R²: {r2_p:.3f}")

# Save Prophet models
for station, data in prophet_forecasts.items():
    safe_name = station.replace(" ","_").replace("/","_").replace("(","").replace(")","")
    joblib.dump(data["model"],
                os.path.join(MODELS, f"prophet_{safe_name}.pkl"))
print(f"  ✅ Saved {len(top_stations)} Prophet models")

# ── STEP 5: 30-day forecast ───────────────────────────────────
print("\n[5/8] Generating 30-day forecast...")

# Use XGBoost to forecast next 30 days for all stations
last_date    = df["date"].max()
future_dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=30)

forecast_rows = []
for station in df["station_name"].unique():
    st_data = df[df["station_name"] == station].sort_values("date")
    if len(st_data) < 30:
        continue

    last_vals = st_data["footfall"].values
    line      = st_data["line"].iloc[0]

    for i, fdate in enumerate(future_dates):
        row = {
            "station_name":      station,
            "line":              line,
            "date":              fdate,
            "year":              fdate.year,
            "month":             fdate.month,
            "day_of_week":       fdate.dayofweek,
            "day_of_year":       fdate.dayofyear,
            "week_of_year":      fdate.isocalendar()[1],
            "quarter":           (fdate.month-1)//3+1,
            "is_weekday":        int(fdate.dayofweek < 5),
            "is_weekend":        int(fdate.dayofweek >= 5),
            "is_month_start":    int(fdate.day == 1),
            "is_month_end":      int(fdate.day == fdate.days_in_month),
            "month_sin":         np.sin(2*np.pi*fdate.month/12),
            "month_cos":         np.cos(2*np.pi*fdate.month/12),
            "dow_sin":           np.sin(2*np.pi*fdate.dayofweek/7),
            "dow_cos":           np.cos(2*np.pi*fdate.dayofweek/7),
            "doy_sin":           np.sin(2*np.pi*fdate.dayofyear/365),
            "doy_cos":           np.cos(2*np.pi*fdate.dayofyear/365),
            "lag_1d":            last_vals[-1],
            "lag_7d":            last_vals[-7] if len(last_vals)>=7 else last_vals[-1],
            "lag_30d":           last_vals[-30] if len(last_vals)>=30 else last_vals[-1],
            "rolling_7d_avg":    np.mean(last_vals[-7:]),
            "rolling_30d_avg":   np.mean(last_vals[-30:]),
            "wow_change":        0,
            "mom_change":        0,
            "is_monsoon":        int(fdate.month in [6,7,8,9]),
            "monsoon_intensity_enc": 2 if fdate.month in [7,8] else (1 if fdate.month in [6,9] else 0),
            "rainfall_mm":       0,
            "rain_ridership_boost": 0.135 if fdate.month in [7,8] else 0,
            "is_festival":       0,
            "festival_boost":    0,
            "is_public_holiday": 0,
            "external_boost":    0,
            "monsoon_elevated":  int(fdate.month in [6,7,8,9]) * int(st_data["is_elevated"].iloc[0]),
            "festival_weekend":  0,
            "is_interchange":    int(st_data["is_interchange"].iloc[0]),
            "is_elevated":       int(st_data["is_elevated"].iloc[0]),
            "pop_density":       st_data["pop_density"].iloc[0],
            "lmpi_score":        st_data["lmpi_score"].iloc[0],
            "severity_encoded":  st_data["severity_encoded"].iloc[0],
            "line_growth_rate":  st_data["line_growth_rate"].iloc[0],
            "years_operational": st_data["years_operational"].iloc[0],
            "station_line_share":st_data["station_line_share"].iloc[-1],
            "station_enc":       st_data["station_enc"].iloc[0],
        }
        forecast_rows.append(row)

df_future = pd.DataFrame(forecast_rows)
X_future  = df_future[XGB_FEATURES_FULL].fillna(0)
df_future["forecasted_footfall"] = xgb_reg.predict(X_future).astype(int)
df_future["forecasted_footfall"] = df_future["forecasted_footfall"].clip(lower=0)

df_future[["station_name","line","date","forecasted_footfall"]].to_csv(
    os.path.join(RESULTS, "layer3_30day_forecast.csv"), index=False)
print(f"  ✅ 30-day forecast: {len(df_future):,} rows saved")

# ── STEP 6: Plots ─────────────────────────────────────────────
print("\n[6/8] Generating plots...")

# -- Plot 1: XGBoost actual vs predicted
fig, ax = plt.subplots(figsize=(12, 5))
sample  = min(300, len(y_test))
ax.plot(range(sample), y_test.values[:sample]/1000,
        color="#7a9bbf", linewidth=1, label="Actual", alpha=0.8)
ax.plot(range(sample), y_pred_xgb[:sample]/1000,
        color="#2e8fff", linewidth=1.5, label="XGBoost Predicted", alpha=0.9)
ax.set_title(f"XGBoost — Actual vs Predicted Footfall (Sample)\nMAE: {mae_xgb:,.0f}  MAPE: {mape_xgb:.1f}%  R²: {r2_xgb:.3f}")
ax.set_ylabel("Footfall (000s)")
ax.set_xlabel("Test Sample Index")
ax.legend()
ax.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(PLOTS, "16_xgb_actual_vs_predicted.png"), dpi=150)
plt.close()
print("  ✅ 16_xgb_actual_vs_predicted.png")

# -- Plot 2: Prophet forecast for top station
top_st   = top_stations[0]
pdata    = prophet_forecasts[top_st]
fig, ax  = plt.subplots(figsize=(12, 5))
ax.plot(pdata["train_df"]["ds"], pdata["train_df"]["y"]/1000,
        color="#7a9bbf", linewidth=1, label="Train", alpha=0.6)
ax.plot(pdata["test_df"]["ds"],  pdata["test_df"]["y"]/1000,
        color="#22d98a", linewidth=1.5, label="Actual (Test)", alpha=0.9)
ax.plot(pdata["forecast"]["ds"], pdata["forecast"]["yhat"]/1000,
        color="#ff6b35", linewidth=1.5, linestyle="--",
        label="Prophet Forecast", alpha=0.9)
ax.fill_between(pdata["forecast"]["ds"],
                pdata["forecast"]["yhat_lower"]/1000,
                pdata["forecast"]["yhat_upper"]/1000,
                alpha=0.15, color="#ff6b35")
ax.set_title(f"Prophet Forecast — {top_st}\nMAE: {prophet_results[top_st]['mae']:,.0f}  MAPE: {prophet_results[top_st]['mape']:.1f}%")
ax.set_ylabel("Footfall (000s)")
ax.set_xlabel("Date")
ax.legend()
ax.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(PLOTS, "17_prophet_forecast.png"), dpi=150)
plt.close()
print("  ✅ 17_prophet_forecast.png")

# -- Plot 3: 30-day forecast by line
fig, ax = plt.subplots(figsize=(12, 5))
for line, color in LINE_COLORS.items():
    line_fore = df_future[df_future["line"]==line].groupby("date")["forecasted_footfall"].sum()
    if len(line_fore):
        ax.plot(line_fore.index, line_fore.values/1e5,
                color=color, linewidth=2, label=f"Line {line}", alpha=0.9)
ax.set_title("30-Day Footfall Forecast by Line")
ax.set_ylabel("Total Footfall (Lakhs)")
ax.set_xlabel("Date")
ax.legend()
ax.grid(True)
plt.xticks(rotation=30)
plt.tight_layout()
plt.savefig(os.path.join(PLOTS, "18_30day_forecast_by_line.png"), dpi=150)
plt.close()
print("  ✅ 18_30day_forecast_by_line.png")

# -- Plot 4: Feature importance — XGBoost Forecaster
fig, ax = plt.subplots(figsize=(9, 7))
feat_imp = pd.Series(xgb_reg.feature_importances_, index=XGB_FEATURES_FULL)
top15    = feat_imp.nlargest(15)
ax.barh(top15.index[::-1], top15.values[::-1],
        color="#a55eea", alpha=0.8, edgecolor="none", height=0.65)
ax.set_title("Top 15 Feature Importances — XGBoost Forecaster")
ax.set_xlabel("Importance Score")
ax.grid(axis="x")
ax.set_axisbelow(True)
plt.tight_layout()
plt.savefig(os.path.join(PLOTS, "19_xgb_forecaster_importance.png"), dpi=150)
plt.close()
print("  ✅ 19_xgb_forecaster_importance.png")

# -- Plot 5: Prophet vs XGBoost MAPE comparison
fig, ax = plt.subplots(figsize=(10, 5))
stations_p = list(prophet_results.keys())
mapes_p    = [prophet_results[s]["mape"] for s in stations_p]
# XGBoost per station MAPE
mapes_x = []
for st in stations_p:
    st_test = df[df["station_name"]==st].iloc[int(len(df[df["station_name"]==st])*0.8):]
    if len(st_test) == 0:
        mapes_x.append(mape_xgb)
        continue
    X_st   = st_test[XGB_FEATURES_FULL].fillna(0)
    y_st   = st_test["footfall"]
    yp_st  = xgb_reg.predict(X_st)
    m_st   = np.mean(np.abs((y_st.values - yp_st) / (y_st.values + 1))) * 100
    mapes_x.append(m_st)

x   = np.arange(len(stations_p))
w   = 0.35
ax.bar(x - w/2, mapes_p, w, label="Prophet",  color="#ff6b35", alpha=0.8)
ax.bar(x + w/2, mapes_x, w, label="XGBoost",  color="#2e8fff", alpha=0.8)
ax.set_xticks(x)
ax.set_xticklabels([s.replace(" ","\\n") for s in stations_p],
                   fontsize=8, rotation=15)
ax.set_ylabel("MAPE (%)")
ax.set_title("Prophet vs XGBoost MAPE — Top Stations")
ax.legend()
ax.grid(axis="y")
ax.set_axisbelow(True)
plt.tight_layout()
plt.savefig(os.path.join(PLOTS, "20_prophet_vs_xgb_mape.png"), dpi=150)
plt.close()
print("  ✅ 20_prophet_vs_xgb_mape.png")

# ── STEP 7: Model performance summary ────────────────────────
print("\n[7/8] Prophet model summary...")
p_maes  = [v["mae"]  for v in prophet_results.values()]
p_mapes = [v["mape"] for v in prophet_results.values()]
print(f"  Avg Prophet MAE  : {np.mean(p_maes):,.0f}")
print(f"  Avg Prophet MAPE : {np.mean(p_mapes):.1f}%")
print(f"  Avg Prophet R²   : {np.mean([v['r2'] for v in prophet_results.values()]):.3f}")

# ── STEP 8: Save results ──────────────────────────────────────
print("\n[8/8] Saving results...")

# XGBoost results
df_xgb_results = pd.DataFrame({
    "actual":    y_test.values,
    "predicted": y_pred_xgb.astype(int),
    "error":     (y_test.values - y_pred_xgb),
    "pct_error": ((y_test.values - y_pred_xgb) / (y_test.values + 1) * 100).round(2),
})
df_xgb_results.to_csv(os.path.join(RESULTS, "layer3_xgb_results.csv"), index=False)

# Prophet results
df_prophet_results = pd.DataFrame(prophet_results).T.reset_index()
df_prophet_results.columns = ["station","mae","mape","r2"]
df_prophet_results.to_csv(os.path.join(RESULTS, "layer3_prophet_results.csv"), index=False)

# ── Final summary ─────────────────────────────────────────────
print("\n" + "=" * 55)
print("  LAYER 3 COMPLETE")
print("=" * 55)
print(f"\n  XGBoost Forecaster")
print(f"  ├── MAE   : {mae_xgb:,.0f} passengers")
print(f"  ├── MAPE  : {mape_xgb:.2f}%")
print(f"  └── R²    : {r2_xgb:.4f}")
print(f"\n  Prophet (avg across {len(top_stations)} stations)")
print(f"  ├── MAE   : {np.mean(p_maes):,.0f} passengers")
print(f"  ├── MAPE  : {np.mean(p_mapes):.2f}%")
print(f"  └── R²    : {np.mean([v['r2'] for v in prophet_results.values()]):.4f}")
print(f"\n  30-Day Forecast : {len(df_future):,} rows")
print(f"\n  Saved:")
print(f"  ├── Models/xgb_forecaster.pkl")
print(f"  ├── Models/prophet_<station>.pkl  (x{len(top_stations)})")
print(f"  ├── Outputs/Results/layer3_xgb_results.csv")
print(f"  ├── Outputs/Results/layer3_prophet_results.csv")
print(f"  └── Outputs/Results/layer3_30day_forecast.csv")
print(f"\n  Plots saved (16–20):")
print(f"  ├── 16_xgb_actual_vs_predicted.png")
print(f"  ├── 17_prophet_forecast.png")
print(f"  ├── 18_30day_forecast_by_line.png")
print(f"  ├── 19_xgb_forecaster_importance.png")
print(f"  └── 20_prophet_vs_xgb_mape.png")