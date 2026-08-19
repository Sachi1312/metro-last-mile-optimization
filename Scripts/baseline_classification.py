# ============================================================
# baseline_classification.py
# Layer 1 baseline — Logistic Regression
# A simple linear baseline for comparison against Random Forest
# and XGBoost, using the exact same feature matrix, train/test
# split logic (StratifiedKFold, random_state=42), and leakage
# exclusions as Scripts/layer1_classification.py.
# Input  : Data/Derived/12_classification_features.csv
# Output : Outputs/Results/baseline_logreg_fold_accuracy.csv
# ============================================================

import pandas as pd
import os
import warnings
warnings.filterwarnings("ignore")

from sklearn.linear_model      import LogisticRegression
from sklearn.preprocessing     import LabelEncoder, StandardScaler
from sklearn.model_selection   import StratifiedKFold, cross_validate

BASE    = r"C:\Users\parek\Downloads\LY Project"
DER     = os.path.join(BASE, "Data", "Derived")
RESULTS = os.path.join(BASE, "Outputs", "Results")
os.makedirs(RESULTS, exist_ok=True)

print("=" * 55)
print("  BASELINE — LOGISTIC REGRESSION (Layer 1)")
print("=" * 55)

df = pd.read_csv(os.path.join(DER, "12_classification_features.csv"))

LEAKAGE_COLS = ["accessibility_score","lmpi_percentile","lmpi_score",
                "freq_impact","best_impact","freq_delta_peak"]
FEATURE_COLS = [c for c in df.columns
                if c not in ["station_name","line","severity_label",
                             "severity_encoded"] + LEAKAGE_COLS]

X = df[FEATURE_COLS].copy()
y = df["severity_label"].copy()
y = y.replace("Low", "Medium")
SEV_ORDER = ["Critical","High","Medium"]

le = LabelEncoder()
le.fit(SEV_ORDER)
y_enc = le.transform(y)

# Logistic Regression needs scaled features (unlike tree models)
X_scaled = StandardScaler().fit_transform(X)

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

logreg = LogisticRegression(
    max_iter=2000,
    class_weight="balanced",
    random_state=42,
)

cv = cross_validate(logreg, X_scaled, y_enc,
                     cv=skf,
                     scoring=["accuracy","f1_weighted"],
                     return_train_score=True)

acc_train = cv["train_accuracy"].mean()
acc_test  = cv["test_accuracy"].mean()
f1        = cv["test_f1_weighted"].mean()

print(f"  Train Accuracy (avg) : {acc_train*100:.1f}%")
print(f"  Test  Accuracy (avg) : {acc_test*100:.1f}%")
print(f"  F1 Score (weighted)  : {f1*100:.1f}%")
print(f"  Fold-wise accuracy   : {[round(a,3) for a in cv['test_accuracy']]}")

fold_rows = [
    {"model": "Logistic Regression", "fold": i + 1, "accuracy": round(float(cv["test_accuracy"][i]) * 100, 1)}
    for i in range(5)
]
pd.DataFrame(fold_rows).to_csv(os.path.join(RESULTS, "baseline_logreg_fold_accuracy.csv"), index=False)

summary = pd.DataFrame([{
    "model": "Logistic Regression",
    "test_accuracy_pct": round(acc_test * 100, 1),
    "f1_weighted_pct": round(f1 * 100, 1),
}])
summary.to_csv(os.path.join(RESULTS, "baseline_logreg_summary.csv"), index=False)

print(f"\n  Saved:")
print(f"  ├── Outputs/Results/baseline_logreg_fold_accuracy.csv")
print(f"  └── Outputs/Results/baseline_logreg_summary.csv")
