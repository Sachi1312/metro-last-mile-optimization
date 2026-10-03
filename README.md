# Resource Optimization of Last-Mile Connectivity in Urban Metro Systems

**K.J. Somaiya School of Engineering | IT Department | 2023–27**

| | |
|---|---|
| **Guide** | Prof. Chirag Desai |
| **Group 7** | Sachi (16014223069) · Aviral (16014223102) · Vedant (16014223095) · Devansh (16014223113) |

---

## Overview

This project builds a multi-layer machine learning pipeline for last-mile connectivity on Mumbai metro (69 stations on Lines 1, 2A, 7, and 3), with a faculty extension to:

- **Delhi** — 50 Red / Yellow / Blue stations with **survey-backed LMPI** (4,560 passenger responses)
- **Future Mumbai lines** — MMRDA Lines 2B, 4, 5, 6, 7A, and 9 as a planning scenario (synthetic LMPI)

The stack combines ridership forecasting, station classification, intervention prioritization, frequency optimization, and a React dashboard with a network switcher. Results are served from MongoDB Atlas (Mumbai 69) and a file-backed expansion bundle (Delhi + future lines).

---

## Key Results

| Metric | Value |
|---|---|
| Mumbai stations | 69 across 4 lines |
| Delhi stations (survey) | 50 · 4,560 responses |
| Critical Mumbai stations | 14 (BKC tops at LMPI 81.5) |
| Published severity accuracy (sees LMPI ingredients) | **95.6%** |
| Clean severity CV — Mumbai only (station facts) | **~75.4%** |
| Clean severity CV — Mumbai + Delhi | **~76.5%** |
| Delhi holdout (Mumbai-trained clean → Delhi survey) | **54%** |
| Future Mumbai formula agreement (no survey) | **~19.5%** |
| XGBoost forecasting MAPE | **2.64%** |
| XGBoost forecasting R² | **0.9985** |
| Prophet avg MAPE | 5.41% |
| Additional peak trains recommended | +116 across network |
| MongoDB documents | 552,172 |

**How to read the accuracy numbers**

- **Published (~95%)** — original model that can see LMPI formula ingredients (easy task).
- **Clean (~75%)** — honest model: population, walk distance, bus, auto, interchange, elevated only.
- **Delhi holdout (54%)** — Mumbai-trained clean model tested on real Delhi survey severity (cross-city transfer).
- **Combined clean (~76.5%)** — clean model cross-validated on Mumbai 69 + Delhi 50 labeled stations.

---

## LMPI labels vs clean classifier (faculty point)

**LMPI is still the station priority index** — it colors the map, ranks interventions, and defines Critical / High / Medium. Mumbai and Delhi LMPI both come from the same weighted survey formula.

**The severity classifier that we report as “honest” does *not* take LMPI as input.** Faculty feedback was that ~95% accuracy is inflated if the model can see the same problem scores the LMPI formula uses (it almost copies the label). So we train two setups:

| Setup | What the model sees | Role |
|---|---|---|
| **Published (leaky)** | Features that include LMPI ingredients (problem scores / related fields) | Matches the original published ~95% result |
| **Clean (honest)** | Station facts only: `pop_density`, `auto_supply_score`, `bus_connectivity_score`, `walk_dist_m`, `is_interchange`, `is_elevated` | The number to discuss in viva / review |

Clean deliberately **excludes** `lmpi_score`, auto/walk/bus/crowd/safety problem scores, LMPI percentile, and accessibility score.

In short: **LMPI labels the stations; the clean model predicts that label from station facts without being spoon-fed LMPI.** Delhi holdout and combined Mumbai+Delhi CV both use this clean feature set. Shown on the dashboard under **Model Comparison → Honest evaluation**.

---

## Project Structure

```
LY Project/
├── .env                          # MongoDB URI (keep private, not committed)
├── .gitignore
├── requirements.txt
├── README.md
├── docker-compose.yml
│
├── Data/
│   ├── Raw/                      # Source CSVs (incl. Delhi survey + priors)
│   │   ├── 01_station_master.csv
│   │   ├── 02_historical_ridership_*.csv
│   │   ├── 03_hourly_ridership_12mo.csv
│   │   ├── 09_delhi_survey_responses.csv
│   │   └── 10_delhi_station_priors.csv
│   └── Derived/                  # Feature-engineered CSVs
│
├── Scripts/                      # Pipeline + expansion build
│   ├── derive_*.py / layer*.py / ...
│   └── build_expansion.py        # Delhi survey LMPI + future Mumbai bundle
│
├── Backend/
│   ├── database.py
│   ├── main.py                   # FastAPI (Mumbai Mongo + expansion routes)
│   └── expansion_bundle.json     # Served to the dashboard
│
├── Frontend/                     # React dashboard (network switcher)
│
├── Models/                       # Trained .pkl files
├── Notebooks/
├── Docs/                         # Literature notes
│
└── Outputs/
    ├── Expansion/bundle.json
    ├── Plots/
    └── Results/
```

---

## ML Pipeline

### Layer 1 — Station Classification
- **Models:** Random Forest + XGBoost (+ Decision Tree baseline)
- **Target:** LMPI severity band (Critical / High / Medium) — LMPI is the label, not a clean-model feature
- **Published features:** can include LMPI ingredients → ~95.6% XGBoost (leaky / easy)
- **Clean features:** station facts only (population, auto supply, bus connectivity, walk distance, interchange, elevated) → ~75.4% Mumbai CV · ~76.5% Mumbai+Delhi CV · 54% Delhi holdout
- **Output:** Priority class per station; dashboard reports both published and clean so the distinction is explicit

### Layer 2 — Feature Engineering
- Classification + forecasting feature sets
- Zero nulls, fully preprocessed

### Layer 3 — Ridership Forecasting
- **Models:** XGBoost (network-wide) + Prophet (per key station) + Linear Regression baseline
- **Output:** 30-day forecast + Jan–Jun 2026 forecast
- **XGBoost:** MAPE 2.64%, R² 0.9985
- **Prophet stations:** Andheri, Ghatkopar, Marol Naka, DN Nagar, Chakala, WEH

### Layer 4 — Optimization
- **Intervention scoring:** Ranked last-mile actions (bus / auto / cab)
- **Frequency optimization:** Trains/hr per time window
- **Interchange sync:** Metro-to-metro planning waits (no railway / monorail links)

---

## LMPI — Last-Mile Pressure Index

```
LMPI = Auto×0.28 + Walking×0.22 + Bus×0.20 + Crowding×0.18 + Safety×0.12
```

| Score | Category | Stations (Mumbai 69) |
|---|---|---|
| ≥ 64 | Critical | 14 |
| 52–63 | High | 38 |
| 38–51 | Medium | 16 |
| < 38 | Low | 1 |

Delhi uses the **same formula**, aggregated from survey problem scores (same method as Mumbai).

LMPI is for **priority scoring and ops ranking**. Predicting severity **without** those formula inputs is the clean classifier described above.

---

## Dashboard networks

| Network | LMPI source | Ridership |
|---|---|---|
| Mumbai — 69 stations | Survey-backed (MongoDB) | Observed / calibrated |
| Delhi — 50 stations | Survey-backed (4,560 responses) | Scenario scale (not DMRC tickets) |
| Mumbai — future lines | Formula from station facts (synthetic) | MMRDA 2031 × 0.45 split |

Use the sidebar network menu to switch. Orange “synthetic” banners apply only to future Mumbai lines.

---

## Backend API

```bash
cd Backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Core Mumbai endpoints:

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
| GET | `/models/comparison` | Classification + forecasting comparison |

Expansion endpoints (Delhi + future Mumbai): `/expansion/stations`, `/expansion/evaluation`, `/expansion/forecast`, `/expansion/festivals`, `/expansion/interventions`, `/expansion/interchange`, and related routes. Query with `?network=delhi` or `?network=mumbai_future`.

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

Delhi and future-line pages read from `Backend/expansion_bundle.json` (not Mongo).

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

# 6. Faculty extension bundle (Delhi survey + future Mumbai)
python Scripts/build_expansion.py
```

### Monthly update
```bash
python Scripts/update_monthly.py   # ~3.8 min retrain
```

---

## Running with Docker

The Backend (FastAPI) and Frontend (React dashboard) are containerized so the app can be
demoed with one command, without installing Node or Python locally. The ML pipeline
(Scripts/, Models/) is not containerized — those run once, ahead of time, on the host, and
their Mumbai output already lives in MongoDB Atlas by the time you run the containers.
Rebuild the expansion bundle before Docker if you change Delhi survey data or assumptions.

### Prerequisites
- Docker Desktop
- A populated MongoDB Atlas database (i.e. `Scripts/load_to_mongodb.py` has already been run)
- `.env` in the project root with `MONGO_URI` and `DB_NAME` (same file the scripts use)

### Run

```bash
docker compose up --build
```

- Backend: http://localhost:8420
- Frontend: http://localhost:5420

(Ports are non-default — `8420`/`5420` instead of `8000`/`5173` — to avoid clashing with other
local projects. Change them in `docker-compose.yml` and `Frontend/src/api.js`'s `API_BASE` if you
need different ports.)

`docker compose down` stops both containers. Rebuild after changing backend/frontend code with
`docker compose up -d --build` again — Docker caches unchanged layers so rebuilds are fast.

The backend image installs a lean API stack (`Backend/requirements.txt`) plus the expansion
bundle — not the full ML stack in the root `requirements.txt`.

---

## Data Notes

- Historical ridership calibrated to MMRDA totals
- COVID years (2020–21) kept with `is_covid=1` flag
- Apr–Dec 2025 synthetic extension flagged with `is_synthetic=1`
- Festival window = ±2 days to reduce boundary overlap
- Mumbai survey: real Aqua Line responses + mirrored synthetic data where needed
- Delhi survey: station-level responses in `Data/Raw/09_delhi_survey_responses.csv` (4,560 rows)
- Delhi priors: `Data/Raw/10_delhi_station_priors.csv` (notes / confidence — not model inputs)

---

## Faculty-review extension

`Scripts/build_expansion.py` writes `Outputs/Expansion/bundle.json` and copies it to
`Backend/expansion_bundle.json`. It does **not** replace the original 69-station Mongo results.

- **Future Mumbai** (Lines 2B, 4, 5, 6, 7A, 9): MMRDA station lists; daily riders = published 2031 line totals × 0.45. LMPI is formula-estimated; only formula-agreement transfer is reported.
- **Delhi**: survey-backed LMPI and severity (same aggregation as Mumbai). Daily ridership remains a role-based scenario scale, not DMRC ticket counts.
- **Evaluation reported in the dashboard (Model Comparison):**
  - Published vs clean severity (Mumbai)
  - Leave-one-line-out + learning curve
  - Delhi survey holdout accuracy + confusion matrix
  - Combined Mumbai+Delhi clean CV
  - Future Mumbai formula-agreement transfer check
- On Mumbai 69, **Future Impact** shows extra riders only at stations where a new line meets the existing network.

---

## Future Scope

- Reinforcement learning (requires live AFCS feed)
- Automated monthly scheduler
- Live AFCS / DMRC ridership feeds for Delhi
- Research paper submission
- Replacing future-Mumbai scenario rows with observed ridership when those feeds exist
