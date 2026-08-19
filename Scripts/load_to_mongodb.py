# ============================================================
# load_to_mongodb.py
# One-time script — loads all project data into MongoDB Atlas
# Collections created:
#   01_stations, 02_historical_ridership, 03_hourly_ridership
#   04_lmpi_scores, 05_temporal_features, 06_frequency_optimization
#   07_intervention_scores, 08_survey_responses
#   results_layer1, results_layer3_forecast, results_layer3_2026
#   results_layer4_optimization, results_layer4_interventions
#   results_layer4_frequency, results_interchange_sync
# ============================================================

import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING
from pymongo.errors import BulkWriteError
import warnings
warnings.filterwarnings("ignore")

# ── Load environment variables ────────────────────────────────
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME   = os.getenv("DB_NAME", "metropt")

if not MONGO_URI:
    print("❌ ERROR: MONGO_URI not found in .env file")
    print("   Make sure .env exists with MONGO_URI=your_connection_string")
    sys.exit(1)

BASE    = r"C:\Users\parek\Downloads\LY Project"
RAW     = os.path.join(BASE, "Data", "Raw")
DER     = os.path.join(BASE, "Data", "Derived")
RESULTS = os.path.join(BASE, "Outputs", "Results")

print("=" * 60)
print("  LOAD TO MONGODB — Mumbai Metro Optimization")
print("=" * 60)

# ── Connect to MongoDB ────────────────────────────────────────
print("\n[1] Connecting to MongoDB Atlas...")
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
    client.server_info()
    db = client[DB_NAME]
    print(f"  ✅ Connected to MongoDB Atlas")
    print(f"  Database: {DB_NAME}")
except Exception as e:
    print(f"  ❌ Connection failed: {e}")
    sys.exit(1)

# ── Helper functions ──────────────────────────────────────────
def load_csv_to_mongo(filepath, collection_name, batch_size=1000):
    """Load a CSV file into a MongoDB collection."""
    if not os.path.exists(filepath):
        print(f"  ⚠️  File not found: {filepath} — skipping")
        return 0

    df = pd.read_csv(filepath)

    # Convert date columns to datetime
    for col in df.columns:
        if "date" in col.lower():
            try:
                df[col] = pd.to_datetime(df[col]).dt.to_pydatetime()
            except Exception:
                pass

    # Replace NaN with None for MongoDB
    df = df.where(pd.notnull(df), None)

    # Convert to list of dicts
    records = df.to_dict("records")

    # Drop existing collection
    db[collection_name].drop()

    # Insert in batches
    total_inserted = 0
    for i in range(0, len(records), batch_size):
        batch = records[i:i+batch_size]
        try:
            db[collection_name].insert_many(batch, ordered=False)
            total_inserted += len(batch)
        except BulkWriteError as e:
            total_inserted += e.details["nInserted"]

    return total_inserted

def add_indexes(collection_name, indexes):
    """Add indexes to a collection for faster queries."""
    col = db[collection_name]
    for index_field in indexes:
        try:
            col.create_index([(index_field, ASCENDING)])
        except Exception:
            pass

# ══════════════════════════════════════════════════════════════
# LOAD ALL DATASETS
# ══════════════════════════════════════════════════════════════
print("\n[2] Loading datasets into MongoDB...")
print(f"  {'Collection':<35} {'Rows':>8}  {'Status':>8}")
print(f"  {'─'*55}")

datasets = [
    # (filepath, collection_name, indexes)
    (os.path.join(RAW, "01_station_master.csv"),
     "stations",
     ["station_name","line","role"]),

    (os.path.join(RAW, "02_historical_ridership_extended.csv"),
     "historical_ridership",
     ["station_name","line","date","is_synthetic"]),

    (os.path.join(RAW, "03_hourly_ridership_12mo.csv"),
     "hourly_ridership",
     ["station_name","line","date","hour"]),

    (os.path.join(DER, "04_lmpi_scores.csv"),
     "lmpi_scores",
     ["station_name","line","severity_label"]),

    (os.path.join(DER, "05_temporal_features.csv"),
     "temporal_features",
     ["date","is_festival","is_monsoon"]),

    (os.path.join(DER, "06_frequency_optimization.csv"),
     "frequency_optimization",
     ["station_name","time_window","severity_label"]),

    (os.path.join(DER, "07_intervention_scores.csv"),
     "intervention_scores",
     ["station_name","severity_label","priority"]),

    (os.path.join(RAW, "08_survey_responses.csv"),
     "survey_responses",
     ["station_name","line"]),
]

total_docs = 0
for filepath, collection, indexes in datasets:
    try:
        n = load_csv_to_mongo(filepath, collection)
        add_indexes(collection, indexes)
        print(f"  ✅ {collection:<33} {n:>8,}  inserted")
        total_docs += n
    except Exception as e:
        print(f"  ❌ {collection:<33} {'ERROR':>8}  {str(e)[:30]}")

# ══════════════════════════════════════════════════════════════
# LOAD RESULT FILES
# ══════════════════════════════════════════════════════════════
print(f"\n[3] Loading result files into MongoDB...")
print(f"  {'Collection':<35} {'Rows':>8}  {'Status':>8}")
print(f"  {'─'*55}")

results = [
    (os.path.join(RESULTS, "layer1_predictions.csv"),
     "results_layer1",
     ["station_name","severity_label","xgb_predicted"]),

    (os.path.join(RESULTS, "layer3_30day_forecast.csv"),
     "results_forecast_30day",
     ["station_name","line","date"]),

    (os.path.join(RESULTS, "layer3_2026_forecast.csv"),
     "results_forecast_2026",
     ["station_name","line","date","month_name","reliability"]),

    (os.path.join(RESULTS, "layer4_master_optimization.csv"),
     "results_optimization",
     ["station_name","line","severity_label","priority_rank"]),

    (os.path.join(RESULTS, "layer4_intervention_queue.csv"),
     "results_interventions",
     ["station_name","severity_label","priority_score"]),

    (os.path.join(RESULTS, "layer4_frequency_recommendations.csv"),
     "results_frequency",
     ["station_name","line","time_window"]),

    (os.path.join(RESULTS, "layer4_final_recommendations.csv"),
     "results_final_recommendations",
     ["station_name","line","severity_label","priority_rank"]),

    (os.path.join(RESULTS, "layer4_interchange_sync.csv"),
     "results_interchange_sync",
     ["station","line_a","line_b","time_window","event_type"]),

    (os.path.join(RESULTS, "layer1_fold_accuracy.csv"),
     "results_layer1_fold_accuracy",
     ["model","fold"]),

    (os.path.join(RESULTS, "layer1_feature_importance.csv"),
     "results_layer1_feature_importance",
     ["model","feature"]),

    (os.path.join(RESULTS, "layer1_xgb_class_report_clean.csv"),
     "results_layer1_xgb_class_report",
     ["class_label"]),

    (os.path.join(RESULTS, "layer1_rf_class_report_clean.csv"),
     "results_layer1_rf_class_report",
     ["class_label"]),

    (os.path.join(RESULTS, "model_comparison_classification.csv"),
     "results_model_comparison_classification",
     ["model"]),

    (os.path.join(RESULTS, "model_comparison_classification_folds.csv"),
     "results_model_comparison_classification_folds",
     ["model","fold"]),

    (os.path.join(RESULTS, "model_comparison_forecasting.csv"),
     "results_model_comparison_forecasting",
     ["model"]),
]

for filepath, collection, indexes in results:
    try:
        n = load_csv_to_mongo(filepath, collection)
        add_indexes(collection, indexes)
        print(f"  ✅ {collection:<33} {n:>8,}  inserted")
        total_docs += n
    except Exception as e:
        print(f"  ❌ {collection:<33} {'ERROR':>8}  {str(e)[:30]}")

# ══════════════════════════════════════════════════════════════
# STORE PROJECT METADATA
# ══════════════════════════════════════════════════════════════
print(f"\n[4] Storing project metadata...")

metadata = {
    "project_name":      "Resource Optimization of Last-Mile Connectivity in Urban Metro Systems",
    "group":             "Group 7",
    "members":           ["Sachi", "Vedant", "Aviral", "Devansh"],
    "guide":             "Prof. Chirag Desai",
    "institute":         "K.J. Somaiya School of Engineering",
    "last_updated":      datetime.now(),
    "data_range":        {"start": "2019-02-27", "end": "2025-12-31"},
    "forecast_range":    {"start": "2026-01-01", "end": "2026-06-30"},
    "total_stations":    69,
    "lines":             ["1", "2A", "7", "3"],
    "model_accuracy": {
        "xgb_classifier":  0.956,
        "rf_classifier":   0.942,
        "xgb_forecaster_mape": 2.64,
        "xgb_forecaster_r2":   0.9985,
        "prophet_avg_mape":    5.41,
    },
    "pipeline_layers":   4,
    "total_features":    {"classification": 32, "forecasting": 41},
    "interchange_stations": [
        {"station": "Marol Naka",  "lines": ["1","3"],  "sync_quality": "Poor"},
        {"station": "DN Nagar",    "lines": ["1","2A"], "sync_quality": "Good"},
        {"station": "Gundavali",   "lines": ["1","7"],  "sync_quality": "Good"},
    ],
    "update_frequency":  "monthly",
    "db_version":        1,
}

db["project_metadata"].drop()
db["project_metadata"].insert_one(metadata)
print(f"  ✅ project_metadata stored")

# ══════════════════════════════════════════════════════════════
# VERIFY ALL COLLECTIONS
# ══════════════════════════════════════════════════════════════
print(f"\n[5] Verifying all collections...")
print(f"  {'Collection':<35} {'Documents':>10}")
print(f"  {'─'*48}")

all_collections = db.list_collection_names()
total_in_db = 0
for col in sorted(all_collections):
    count = db[col].count_documents({})
    total_in_db += count
    print(f"  📁 {col:<33} {count:>10,}")

# ── Final summary ─────────────────────────────────────────────
print(f"\n{'=' * 60}")
print(f"  MONGODB LOAD COMPLETE")
print(f"{'=' * 60}")
print(f"\n  Database         : {DB_NAME}")
print(f"  Collections      : {len(all_collections)}")
print(f"  Total documents  : {total_in_db:,}")
print(f"\n  Storage estimate : ~{total_in_db * 0.5 / 1024:.1f} MB")
print(f"  Atlas free limit : 512 MB")
print(f"  Usage            : ~{total_in_db * 0.5 / 1024 / 512 * 100:.1f}% of free tier")
print(f"\n  ✅ All data loaded successfully")
print(f"  ✅ Indexes created for fast queries")
print(f"  ✅ Project metadata stored")
print(f"\n  Next step: main.py (FastAPI backend)")

client.close()