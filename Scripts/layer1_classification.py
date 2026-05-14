# ============================================================
# layer1_classification.py
# Layer 1 — LMPI Severity Classification
# Models : Random Forest + XGBoost
# Input  : Data/Derived/12_classification_features.csv
# Output : Models/ + Outputs/Results/
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

from sklearn.ensemble          import RandomForestClassifier
from sklearn.model_selection   import StratifiedKFold, cross_val_score, cross_validate
from sklearn.metrics           import (classification_report, confusion_matrix,
                                       accuracy_score, f1_score)
from sklearn.preprocessing     import LabelEncoder
from xgboost                   import XGBClassifier
import shap

BASE    = r"C:\Users\parek\Downloads\LY Project"
DER     = os.path.join(BASE, "Data", "Derived")
MODELS  = os.path.join(BASE, "Models")
RESULTS = os.path.join(BASE, "Outputs", "Results")
PLOTS   = os.path.join(BASE, "Outputs", "Plots")
os.makedirs(MODELS,  exist_ok=True)
os.makedirs(RESULTS, exist_ok=True)
os.makedirs(PLOTS,   exist_ok=True)

# ── Style ─────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.facecolor": "#0e1525","axes.facecolor": "#141e33",
    "axes.edgecolor":   "#2a3f5f","axes.labelcolor": "#dce8f5",
    "axes.titlecolor":  "#dce8f5","axes.titlesize":  12,
    "xtick.color":      "#7a9bbf","ytick.color":     "#7a9bbf",
    "text.color":       "#dce8f5","grid.color":      "#1e3050",
    "grid.linestyle":   "--","grid.alpha":           0.5,
    "font.family":      "monospace",
    "legend.facecolor": "#141e33","legend.edgecolor": "#2a3f5f",
})

SEV_ORDER  = ["Critical","High","Medium","Low"]
SEV_COLORS = {"Critical":"#ff3b55","High":"#ff6b35","Medium":"#ffc832","Low":"#22d98a"}

print("=" * 55)
print("  LAYER 1 — LMPI SEVERITY CLASSIFICATION")
print("=" * 55)

# ── STEP 1: Load data ─────────────────────────────────────────
print("\n[1/8] Loading feature matrix...")
df = pd.read_csv(os.path.join(DER, "12_classification_features.csv"))
print(f"  Rows     : {len(df)}")
print(f"  Features : {len(df.columns) - 4}")
print(f"  Classes  : {df['severity_label'].value_counts().to_dict()}")

# ── STEP 2: Prepare X and y ───────────────────────────────────
print("\n[2/8] Preparing features and labels...")

# Drop derived columns that directly encode the target
# accessibility_score = 100 - lmpi_score → perfect correlation, causes leakage
# lmpi_percentile, freq_impact also derived directly from lmpi
LEAKAGE_COLS = ["accessibility_score","lmpi_percentile","lmpi_score",
                "freq_impact","best_impact","freq_delta_peak"]


FEATURE_COLS = [c for c in df.columns
                if c not in ["station_name","line","severity_label",
                             "severity_encoded"] + LEAKAGE_COLS]

X = df[FEATURE_COLS].copy()
y = df["severity_label"].copy()
# Merge Low into Medium — only 1 Low station, causes XGBoost fold issues
y = y.replace("Low", "Medium")
SEV_ORDER = ["Critical","High","Medium"]

# Encode target
le = LabelEncoder()
le.fit(SEV_ORDER)
y_enc = le.transform(y)

print(f"  Feature columns : {len(FEATURE_COLS)}")
print(f"  Feature list    : {FEATURE_COLS}")
print(f"  Class mapping   : {dict(zip(le.classes_, le.transform(le.classes_)))}")

# ── STEP 3: Cross-validation setup ───────────────────────────
print("\n[3/8] Setting up Stratified K-Fold (k=5)...")
# StratifiedKFold ensures each fold has all severity classes
# Critical for small dataset (69 stations)
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
print("  Using StratifiedKFold — ensures class balance in each fold")
print("  Each fold: ~55 train / ~14 test stations")

# ── STEP 4: Random Forest ─────────────────────────────────────
print("\n[4/8] Training Random Forest...")
rf = RandomForestClassifier(
    n_estimators=200,
    max_depth=8,
    min_samples_split=3,
    min_samples_leaf=1,
    class_weight="balanced",   # handles class imbalance
    random_state=42,
    n_jobs=-1,
)

rf_cv = cross_validate(rf, X, y_enc,
                        cv=skf,
                        scoring=["accuracy","f1_weighted"],
                        return_train_score=True)

rf_acc_train = rf_cv["train_accuracy"].mean()
rf_acc_test  = rf_cv["test_accuracy"].mean()
rf_f1        = rf_cv["test_f1_weighted"].mean()

print(f"  Train Accuracy (avg) : {rf_acc_train:.4f} ({rf_acc_train*100:.1f}%)")
print(f"  Test  Accuracy (avg) : {rf_acc_test:.4f}  ({rf_acc_test*100:.1f}%)")
print(f"  F1 Score (weighted)  : {rf_f1:.4f}")
print(f"  Fold-wise accuracy   : {[round(a,3) for a in rf_cv['test_accuracy']]}")

# Train final RF on full data for feature importance + saving
rf.fit(X, y_enc)
joblib.dump(rf, os.path.join(MODELS, "rf_classifier.pkl"))
print(f"  ✅ Saved: Models/rf_classifier.pkl")

# ── STEP 5: XGBoost ───────────────────────────────────────────
print("\n[5/8] Training XGBoost...")
xgb = XGBClassifier(
    n_estimators=200,
    max_depth=4,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    use_label_encoder=False,
    eval_metric="mlogloss",
    random_state=42,
    verbosity=0,
)

xgb_cv = cross_validate(xgb, X, y_enc,
                         cv=skf,
                         scoring=["accuracy","f1_weighted"],
                         return_train_score=True)

xgb_acc_train = xgb_cv["train_accuracy"].mean()
xgb_acc_test  = xgb_cv["test_accuracy"].mean()
xgb_f1        = xgb_cv["test_f1_weighted"].mean()

print(f"  Train Accuracy (avg) : {xgb_acc_train:.4f} ({xgb_acc_train*100:.1f}%)")
print(f"  Test  Accuracy (avg) : {xgb_acc_test:.4f}  ({xgb_acc_test*100:.1f}%)")
print(f"  F1 Score (weighted)  : {xgb_f1:.4f}")
print(f"  Fold-wise accuracy   : {[round(a,3) for a in xgb_cv['test_accuracy']]}")

# Train final XGB on full data
xgb.fit(X, y_enc)
joblib.dump(xgb, os.path.join(MODELS, "xgb_classifier.pkl"))
print(f"  ✅ Saved: Models/xgb_classifier.pkl")

# ── STEP 6: Model Comparison ──────────────────────────────────
print("\n[6/8] Model comparison...")
best_model      = "XGBoost" if xgb_acc_test >= rf_acc_test else "Random Forest"
best_accuracy   = max(xgb_acc_test, rf_acc_test)
print(f"  Random Forest accuracy : {rf_acc_test*100:.1f}%")
print(f"  XGBoost accuracy       : {xgb_acc_test*100:.1f}%")
print(f"  Best model             : {best_model} ({best_accuracy*100:.1f}%)")

# ── STEP 7: Plots ─────────────────────────────────────────────
print("\n[7/8] Generating plots...")

# -- Plot 1: Model Accuracy Comparison
fig, ax = plt.subplots(figsize=(8, 5))
models  = ["Random Forest", "XGBoost"]
train_a = [rf_acc_train*100, xgb_acc_train*100]
test_a  = [rf_acc_test*100,  xgb_acc_test*100]
x       = np.arange(len(models))
w       = 0.3
ax.bar(x - w/2, train_a, w, label="Train Accuracy", color="#2e8fff", alpha=0.8)
ax.bar(x + w/2, test_a,  w, label="Test Accuracy",  color="#22d98a", alpha=0.8)
for i, (tr, te) in enumerate(zip(train_a, test_a)):
    ax.text(i - w/2, tr + 0.3, f"{tr:.1f}%", ha="center", fontsize=9)
    ax.text(i + w/2, te + 0.3, f"{te:.1f}%", ha="center", fontsize=9)
ax.set_xticks(x)
ax.set_xticklabels(models)
ax.set_ylim(0, 115)
ax.set_ylabel("Accuracy (%)")
ax.set_title("Layer 1 — Model Accuracy Comparison (5-Fold CV)")
ax.legend()
ax.grid(axis="y")
ax.set_axisbelow(True)
plt.tight_layout()
plt.savefig(os.path.join(PLOTS, "11_model_accuracy.png"), dpi=150)
plt.close()
print("  ✅ 11_model_accuracy.png")

# -- Plot 2: Confusion Matrix (best model on full data)
best_clf = xgb if xgb_acc_test >= rf_acc_test else rf
y_pred   = best_clf.predict(X)
cm       = confusion_matrix(y_enc, y_pred,
                            labels=le.transform(SEV_ORDER))
fig, ax  = plt.subplots(figsize=(7, 6))
sns.heatmap(cm, annot=True, fmt="d",
            xticklabels=SEV_ORDER,
            yticklabels=SEV_ORDER,
            cmap=sns.light_palette("#2e8fff", as_cmap=True),
            linewidths=0.5, linecolor="#1e3050",
            ax=ax, cbar=False)
ax.set_title(f"Confusion Matrix — {best_model}")
ax.set_xlabel("Predicted Label")
ax.set_ylabel("True Label")
plt.tight_layout()
plt.savefig(os.path.join(PLOTS, "12_confusion_matrix.png"), dpi=150)
plt.close()
print("  ✅ 12_confusion_matrix.png")

# -- Plot 3: Feature Importance (RF)
fig, ax = plt.subplots(figsize=(9, 7))
feat_imp = pd.Series(rf.feature_importances_, index=FEATURE_COLS)
top15    = feat_imp.nlargest(15)
colors   = ["#ff3b55" if v > top15.quantile(0.8) else
            "#2e8fff" if v > top15.quantile(0.5) else
            "#7a9bbf" for v in top15.values]
ax.barh(top15.index[::-1], top15.values[::-1],
        color=colors[::-1], edgecolor="none", height=0.65)
ax.set_title("Top 15 Feature Importances — Random Forest")
ax.set_xlabel("Importance Score")
ax.grid(axis="x")
ax.set_axisbelow(True)
plt.tight_layout()
plt.savefig(os.path.join(PLOTS, "13_feature_importance_rf.png"), dpi=150)
plt.close()
print("  ✅ 13_feature_importance_rf.png")

# -- Plot 4: XGBoost Feature Importance
fig, ax = plt.subplots(figsize=(9, 7))
xgb_imp = pd.Series(xgb.feature_importances_, index=FEATURE_COLS)
top15x  = xgb_imp.nlargest(15)
ax.barh(top15x.index[::-1], top15x.values[::-1],
        color="#a55eea", alpha=0.8, edgecolor="none", height=0.65)
ax.set_title("Top 15 Feature Importances — XGBoost")
ax.set_xlabel("Importance Score")
ax.grid(axis="x")
ax.set_axisbelow(True)
plt.tight_layout()
plt.savefig(os.path.join(PLOTS, "14_feature_importance_xgb.png"), dpi=150)
plt.close()
print("  ✅ 14_feature_importance_xgb.png")

# -- Plot 5: SHAP values (XGBoost explainability)
print("  Computing SHAP values (this may take 30 seconds)...")
try:
    explainer  = shap.TreeExplainer(xgb)
    shap_vals  = explainer.shap_values(X, check_additivity=False)
    fig, ax    = plt.subplots(figsize=(10, 7))
    shap.summary_plot(shap_vals, X,
                      plot_type="bar",
                      class_names=SEV_ORDER,
                      show=False,
                      max_display=12)
    plt.title("SHAP Feature Importance — XGBoost (All Classes)")
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS, "15_shap_summary.png"),
                dpi=150, bbox_inches="tight")
    plt.close()
    print("  ✅ 15_shap_summary.png")
except Exception as e:
    print(f"  ⚠️  SHAP skipped: {e}")

# ── STEP 8: Save results ──────────────────────────────────────
print("\n[8/8] Saving results...")

# Predictions on full dataset
df["rf_predicted"]  = le.inverse_transform(rf.predict(X))
df["xgb_predicted"] = le.inverse_transform(xgb.predict(X))
df["rf_correct"]    = (df["rf_predicted"]  == df["severity_label"]).astype(int)
df["xgb_correct"]   = (df["xgb_predicted"] == df["severity_label"]).astype(int)

results_cols = ["station_name","line","severity_label",
                "lmpi_score","rf_predicted","xgb_predicted",
                "rf_correct","xgb_correct"]
df_results = df[results_cols].copy()
df_results.to_csv(os.path.join(RESULTS, "layer1_predictions.csv"), index=False)

# Save classification report
report_rf  = classification_report(y_enc, rf.predict(X),
                                   target_names=SEV_ORDER, output_dict=True)
report_xgb = classification_report(y_enc, xgb.predict(X),
                                   target_names=SEV_ORDER, output_dict=True)
pd.DataFrame(report_rf).T.to_csv(os.path.join(RESULTS, "layer1_rf_report.csv"))
pd.DataFrame(report_xgb).T.to_csv(os.path.join(RESULTS, "layer1_xgb_report.csv"))

# ── Final summary ─────────────────────────────────────────────
print("\n" + "=" * 55)
print("  LAYER 1 COMPLETE")
print("=" * 55)
print(f"\n  Random Forest")
print(f"  ├── Train Accuracy : {rf_acc_train*100:.1f}%")
print(f"  ├── Test  Accuracy : {rf_acc_test*100:.1f}%")
print(f"  └── F1 Score       : {rf_f1*100:.1f}%")
print(f"\n  XGBoost")
print(f"  ├── Train Accuracy : {xgb_acc_train*100:.1f}%")
print(f"  ├── Test  Accuracy : {xgb_acc_test*100:.1f}%")
print(f"  └── F1 Score       : {xgb_f1*100:.1f}%")
print(f"\n  Best Model        : {best_model} ({best_accuracy*100:.1f}%)")
print(f"\n  Saved:")
print(f"  ├── Models/rf_classifier.pkl")
print(f"  ├── Models/xgb_classifier.pkl")
print(f"  ├── Outputs/Results/layer1_predictions.csv")
print(f"  ├── Outputs/Results/layer1_rf_report.csv")
print(f"  └── Outputs/Results/layer1_xgb_report.csv")
print(f"\n  Plots saved (11–15):")
print(f"  ├── 11_model_accuracy.png")
print(f"  ├── 12_confusion_matrix.png")
print(f"  ├── 13_feature_importance_rf.png")
print(f"  ├── 14_feature_importance_xgb.png")
print(f"  └── 15_shap_summary.png")