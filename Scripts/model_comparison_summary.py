# ============================================================
# model_comparison_summary.py
# Consolidates existing per-model evaluation outputs (Layer 1
# classification, Layer 3 forecasting) plus the new baseline
# models into a small set of comparison-ready CSVs for the
# dashboard's Model Comparison page. Reads only already-generated
# results — does not retrain or touch any existing script's output.
# Output : Outputs/Results/model_comparison_classification.csv
#          Outputs/Results/model_comparison_classification_folds.csv
#          Outputs/Results/model_comparison_forecasting.csv
# ============================================================

import pandas as pd
import os

BASE    = r"C:\Users\parek\Downloads\LY Project"
RESULTS = os.path.join(BASE, "Outputs", "Results")

print("=" * 55)
print("  MODEL COMPARISON SUMMARY")
print("=" * 55)

# ── Classification: fold accuracy across all 3 models ─────────
print("\n[1/2] Consolidating classification comparison...")
folds = pd.read_csv(os.path.join(RESULTS, "layer1_fold_accuracy.csv"))          # XGBoost + Random Forest
logreg_folds = pd.read_csv(os.path.join(RESULTS, "baseline_logreg_fold_accuracy.csv"))  # Logistic Regression
all_folds = pd.concat([folds, logreg_folds], ignore_index=True)
all_folds.to_csv(os.path.join(RESULTS, "model_comparison_classification_folds.csv"), index=False)

xgb_report = pd.read_csv(os.path.join(RESULTS, "layer1_xgb_report.csv"), index_col=0)
rf_report  = pd.read_csv(os.path.join(RESULTS, "layer1_rf_report.csv"), index_col=0)
logreg_summary = pd.read_csv(os.path.join(RESULTS, "baseline_logreg_summary.csv"))

# Save cleaned copies of the per-class reports (rename blank index column) for Mongo loading
for name, report in [("xgb", xgb_report), ("rf", rf_report)]:
    cleaned = report.reset_index().rename(columns={"index": "class_label"})
    cleaned.to_csv(os.path.join(RESULTS, f"layer1_{name}_class_report_clean.csv"), index=False)

summary_rows = []
for model, folddf in all_folds.groupby("model"):
    avg_acc = round(folddf["accuracy"].mean(), 1)
    if model == "XGBoost":
        f1 = round(xgb_report.loc["weighted avg", "f1-score"] * 100, 1)
        note = "In-sample F1 (full-fit report); accuracy above is held-out CV"
    elif model == "Random Forest":
        f1 = round(rf_report.loc["weighted avg", "f1-score"] * 100, 1)
        note = "In-sample F1 (full-fit report); accuracy above is held-out CV"
    else:
        f1 = float(logreg_summary["f1_weighted_pct"].iloc[0])
        note = "F1 averaged across CV folds"
    summary_rows.append({
        "model": model,
        "cv_accuracy_pct": avg_acc,
        "f1_weighted_pct": f1,
        "note": note,
    })

pd.DataFrame(summary_rows).to_csv(os.path.join(RESULTS, "model_comparison_classification.csv"), index=False)
print(f"  Saved: model_comparison_classification.csv, model_comparison_classification_folds.csv")

# ── Forecasting: XGBoost vs Prophet vs seasonal-naive ──────────
print("\n[2/2] Consolidating forecasting comparison...")
xgb_rows = pd.read_csv(os.path.join(RESULTS, "layer3_xgb_results.csv"))
xgb_mae  = xgb_rows["error"].abs().mean()
xgb_mape = xgb_rows["pct_error"].abs().mean()
ss_res = ((xgb_rows["actual"] - xgb_rows["predicted"]) ** 2).sum()
ss_tot = ((xgb_rows["actual"] - xgb_rows["actual"].mean()) ** 2).sum()
xgb_r2 = 1 - ss_res / ss_tot

prophet = pd.read_csv(os.path.join(RESULTS, "layer3_prophet_results.csv"))
naive   = pd.read_csv(os.path.join(RESULTS, "baseline_naive_forecast.csv"))

forecast_rows = [
    {"model": "XGBoost", "mae": round(float(xgb_mae), 1), "mape": round(float(xgb_mape), 2),
     "r2": round(float(xgb_r2), 4), "coverage": f"{len(xgb_rows):,} held-out test days, all stations"},
    {"model": "Prophet", "mae": round(float(prophet["mae"].mean()), 1), "mape": round(float(prophet["mape"].mean()), 2),
     "r2": round(float(prophet["r2"].mean()), 4), "coverage": f"{len(prophet)} sample stations"},
    {"model": "Seasonal Naive", "mae": float(naive["mae"].iloc[0]), "mape": float(naive["mape"].iloc[0]),
     "r2": float(naive["r2"].iloc[0]), "coverage": f"{int(naive['test_rows'].iloc[0]):,} held-out test days, all stations"},
]
pd.DataFrame(forecast_rows).to_csv(os.path.join(RESULTS, "model_comparison_forecasting.csv"), index=False)
print(f"  Saved: model_comparison_forecasting.csv")

print("\nDone.")
