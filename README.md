# Resource Optimization of Last-Mile Connectivity in Urban Metro Systems

**K.J. Somaiya School of Engineering | IT Department | 2023–27**

| | |
|---|---|
| **Guide** | Prof. Chirag Desai |
| **Group 7** | Sachi (16014223069) · Aviral (16014223102) · Vedant (16014223095) · Devansh (16014223113) |

---

## Overview

This project builds a 4-layer machine learning pipeline to optimize last-mile connectivity across 69 stations on Mumbai's metro network (Lines 1, 2A, 7, and 3). It combines ridership forecasting, station classification, intervention prioritization, and frequency optimization — all backed by a live MongoDB Atlas database and a FastAPI backend.

---

## Key Results

| Metric | Value |
|---|---|
| Stations covered | 69 across 4 lines |
| Critical stations flagged | 14 (BKC tops at LMPI 81.5) |
| XGBoost classification accuracy | **95.6%** |
| Random Forest accuracy | **94.2%** |
| XGBoost forecasting MAPE | **2.64%** |
| XGBoost forecasting R² | **0.9985** |
| Prophet avg MAPE | 5.41% |
| Additional peak trains recommended | +116 across network |
| MongoDB documents | 552,172 |

---

## Project Structure

```
LY Project/
├── .env                          # MongoDB URI (keep private, not committed)
├── .gitignore
├── requirements.txt
├── README.md
│
├── Data/
│   ├── Raw/                      # 4 source CSVs
│   │   ├── 01_station_master.csv
│   │   ├── 02_historical_ridership_5yr.csv
│   │   ├── 02_historical_ridership_extended.csv
│   │   └── 03_hourly_ridership_12mo.csv
│   └── Derived/                  # 10 feature-engineered CSVs
│       ├── 04_lmpi_scores.csv
│       ├── 05_temporal_features.csv
│       ├── 06_frequency_optimization.csv
│       ├── 07_intervention_scores.csv
│       ├── 08_survey_responses.csv
│       ├── 10_classification_ready.csv
│       └── 12_classification_features.csv
│
├── Scripts/                      # 16 Python scripts (all complete)
│   ├── derive_01_lmpi.py
│   ├── derive_02_temporal.py
│   ├── derive_03_frequency.py
│   ├── derive_04_intervention.py
│   ├── preprocess.py
│   ├── eda.py
│   ├── feature_engineering.py
│   ├── layer1_classification.py
│   ├── layer3_forecasting.py
│   ├── layer4_optimization.py
│   ├── interchange_sync.py
│   ├── generate_2025_extension.py
│   ├── generate_2026_forecast.py
│   ├── load_to_mongodb.py
│   ├── validate_data.py
│   └── update_monthly.py
│
├── Backend/
│   ├── database.py               # MongoDB connection via pymongo + dotenv
│   └── main.py                   # FastAPI — 10 REST endpoints
│
├── Models/                       # 9 trained .pkl files
│   ├── rf_classifier.pkl
│   ├── xgb_classifier.pkl
│   ├── xgb_forecaster.pkl
│   └── prophet_*.pkl             # Per-station Prophet models
│
├── Notebooks/                    # 5 Jupyter notebooks (explanation + walkthroughs)
│
└── Outputs/
    ├── Plots/                    # 27 EDA + model result plots
    └── Results/                  # 12 CSV result files
```

---

## ML Pipeline

### Layer 1 — Station Classification
- **Models:** Random Forest + XGBoost
- **Features:** 32 engineered features, 5-fold cross-validation
- **Output:** Priority class (Critical / High / Medium) per station
- **Accuracy:** RF 94.2% · XGBoost 95.6%

### Layer 2 — Feature Engineering
- 38 classification features + 45 forecasting features
- Zero nulls, fully preprocessed

### Layer 3 — Ridership Forecasting
- **Models:** XGBoost (network-wide) + Prophet (per key station)
- **Output:** 30-day forecast + Jan–Jun 2026 forecast (12,489 rows)
- **XGBoost:** MAPE 2.64%, R² 0.9985
- **Prophet stations:** Andheri, Ghatkopar, Marol Naka, DN Nagar, Chakala, WEH

### Layer 4 — Optimization
- **Intervention scoring:** Ranked queue for 52 flagged stations
- **Frequency optimization:** Trains/hr per time window
- **Interchange sync:** 3 stations × 5 windows × 6 events = 90 sync rows

---

## LMPI — Last-Mile Pressure Index

```
LMPI = Auto×0.28 + Walking×0.22 + Bus×0.20 + Crowding×0.18 + Safety×0.12
```

| Score | Category | Stations |
|---|---|---|
| ≥ 64 | Critical | 14 |
| 52–63 | High | 38 |
| 38–51 | Medium | 16 |
| < 38 | Low | 1 |

---

## Backend API

Run the FastAPI backend:

```bash
cd Backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Available endpoints:

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Health check |
| GET | `/network/summary` | Overall network stats |
| GET | `/stations` | All 69 stations |
| GET | `/station/{name}` | Single station full profile |
| GET | `/forecast/{name}` | 30-day ridership forecast |
| GET | `/forecast/2026/{name}` | Jan–Jun 2026 forecast |
| GET | `/interventions` | Ranked intervention queue |
| GET | `/frequency/{name}` | Trains/hr recommendations |
| GET | `/interchange` | Interchange sync analysis |
| GET | `/lmpi/line/{line}` | All stations on a line |

---

## Database — MongoDB Atlas

- **Database:** `metropt` (M0 Free Tier)
- **Collections:** 17
- **Total documents:** 552,172
- **Storage:** 269.6 MB

Set your connection URI in a `.env` file:

```
MONGO_URI=mongodb+srv://<user>:<password>@cluster.mongodb.net/metropt
```

---

## Setup

### Prerequisites
- Python 3.12+
- MongoDB Atlas account (or local MongoDB)

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run pipeline (in order)

```bash
# 1. Derive features
python Scripts/derive_01_lmpi.py
python Scripts/derive_02_temporal.py
python Scripts/derive_03_frequency.py
python Scripts/derive_04_intervention.py

# 2. Preprocess + EDA
python Scripts/preprocess.py
python Scripts/eda.py

# 3. Feature engineering
python Scripts/feature_engineering.py

# 4. Train models
python Scripts/layer1_classification.py
python Scripts/layer3_forecasting.py
python Scripts/layer4_optimization.py
python Scripts/interchange_sync.py

# 5. Load to MongoDB
python Scripts/load_to_mongodb.py
```

### Monthly update
```bash
python Scripts/update_monthly.py   # ~3.8 min retrain
```

---

## Data Notes

- Historical ridership calibrated to MMRDA totals
- COVID years (2020–21) kept with `is_covid=1` flag
- Apr–Dec 2025 synthetic extension flagged with `is_synthetic=1`
- Festival window = ±2 days to reduce boundary overlap
- Survey data: real Aqua Line responses + mirrored synthetic data

---

## Future Scope

- Reinforcement learning (requires live AFCS feed)
- Automated monthly scheduler
- Live AFCS API integration
- Research paper submission