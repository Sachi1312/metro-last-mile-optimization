# PPT Update Plan — Progress Review

**For:** Resource Optimization of Last-Mile Connectivity in Urban Metro Systems (Group 7)
**Purpose:** What to add/change vs. the last deck (`...Final_ (1).pdf`) to show real progress — the dashboard is now fully built and integrated, not an idea.

Legend: 🆕 New slide · ✏️ Edit existing slide · 📸 Screenshot needed (I can't capture these myself right now — take them from your running dashboard at `http://localhost:5420`)

---

## 1. 🆕 Insert right after the title slide: "Progress Since Last Review"

A single summary slide so the panel immediately sees what changed. This is the slide that answers "what have you actually done."

**Content — two columns:**

*Left, "Then":*
- Dashboard was a planned UI, not built
- Model comparison: RF vs XGBoost only (classification), Prophet vs XGBoost only (forecasting)
- Static plots for festival impact, no drill-down

*Right, "Now":*
- Full React + FastAPI + MongoDB dashboard, 8 screens, fully live
- Containerized with Docker — one-command deploy
- 4 classification models compared (+ Decision Tree, Logistic Regression), 4 forecasting models compared (+ Linear Regression, seasonal-naive baseline)
- Interactive Festival Impact tool — ranks all 69 stations per festival, suggests resource reallocation
- Historical drill-down (2024–2025, real festival/monsoon data) and Actual-vs-Predicted validation view

---

## 2. ✏️ Slide 16 "Dashboard" — replace entirely

This is the slide you specifically flagged. Currently it shows the dashboard as a concept. Replace with real screenshots of the running app and a short "what it does" list.

📸 **Capture these 4 screens** (open each URL, screenshot the full page):
1. `http://localhost:5420/` — Network Map (69 stations, severity color-coding, line filters)
2. `http://localhost:5420/station/BKC` — Station Detail (LMPI factor bars, SHAP explanation, forecast chart)
3. `http://localhost:5420/festivals` — Festival Impact (new feature, see slide 4 below)
4. `http://localhost:5420/models` — Model Comparison (new feature, see slide 5 below)

**Slide layout:** 2×2 grid of the four screenshots, each with a one-line caption. Title: "Live Dashboard — 8 Screens, Fully Integrated with Backend."

**Caption text to use:**
- Network Map — "All 69 stations, color-coded by severity, filterable by line"
- Station Detail — "Per-station LMPI breakdown, SHAP explanation, festival-aware forecast"
- Festival Impact — "Ranks stations by real festival-day surge for resource reallocation"
- Model Comparison — "Every model trained, compared on held-out accuracy"

---

## 3. ✏️ Slide 18 "Tech Stack" — fill in (currently has empty/placeholder fields)

Replace the blank "Frontend: Database / Backend: / Tools:" layout with the actual stack:

| Layer | Technology |
|---|---|
| **Frontend** | React 19 + Vite, Chart.js, React Router — 8-page SPA |
| **Backend** | FastAPI (Python), 20+ REST endpoints |
| **Database** | MongoDB Atlas — 25 collections, 552K+ documents |
| **ML/Data** | scikit-learn, XGBoost, Prophet, pandas |
| **Deployment** | Docker + Docker Compose — backend & frontend containerized |
| **Tools** | Git/GitHub, VS Code, Google Forms (data collection) |

Note explicitly: **"Backend and frontend are now fully connected — no mock data. Every chart on the dashboard reads live from MongoDB via the FastAPI backend."**

---

## 4. 🆕 New slide: "Festival Impact — Resource Reallocation"

This feature didn't exist last time (slide 14 only had a static plot: "Average Ridership Boost During Festivals vs Normal Days"). It's now a full interactive tool — worth its own slide since it's genuinely new decision-support logic, not just a UI wrapper.

📸 **Capture:** `http://localhost:5420/festivals` with a festival selected (Ganesh Chaturthi or Diwali works well) — capture the ranked bar chart and the two-column Surge/Divert cards.

**Content to explain (this is a good talking point for the viva):**
- For any of 11 real festivals, ranks all 69 stations by **extra riders vs. their own normal-day baseline**
- Surge stations → recommend deploying extra trains/autos/buses here
- Lowest-surge stations → recommend diverting that spare capacity here instead
- Example finding: on Ganesh Chaturthi, Andheri gains +21,184 riders vs. Airport Road's +143 — a >140× difference in the same network on the same day
- **Honest caveat we surfaced ourselves:** the underlying festival multiplier is applied network-wide rather than being station-specific, so known real-world hotspots (e.g., Dadar during Ganesh visarjan processions) don't always rank first — we flag this limitation directly in the UI rather than hide it. (Good to mention proactively — shows rigor.)

---

## 5. 🆕 New slide: "Model Comparison — Why XGBoost"

Existing slides 12–13 already show RF vs XGBoost and Prophet vs XGBoost separately with real numbers. This new slide unifies both into one comparison and adds two baseline models that make the justification much stronger.

**Classification (5-fold CV accuracy):**

| Model | Accuracy | Note |
|---|---|---|
| Decision Tree | 92.7% | Overfits — 100% train vs 92.7% test |
| Logistic Regression | 94.2% | Ties RF only because classes are linearly separable here |
| Random Forest | 94.2% | |
| **XGBoost** | **95.6%** | **Selected** |

**Forecasting (held-out MAPE, lower is better):**

| Model | MAPE |
|---|---|
| Linear Regression (same features as XGBoost) | 16.73% |
| Seasonal Naive ("same day last week") | 14.61% |
| Prophet | 5.41% |
| **XGBoost** | **2.64%** |

**Key talking point:** Linear Regression, trained on the *exact same features* as XGBoost, performs *worse* than a naive last-week guess. This proves the footfall relationships are genuinely nonlinear — XGBoost isn't winning just because it has more features, it's winning because tree-based boosting captures interactions a linear model can't.

📸 **Capture:** `http://localhost:5420/models` — both chart sections.

---

## 6. ✏️ Slide 19 "Implementation Schedule" — mark completion status

Add a status column or color-code completed items:
- ✅ Dashboard development & integration — **Complete**
- ✅ Docker deployment — **Complete**
- ✅ Extended model comparison (baseline models) — **Complete**
- ✅ Festival impact / resource reallocation tool — **Complete**
- 🔲 (whatever remains per your original schedule — final report writeup, etc.)

---

## Presenting tomorrow — quick order of operations

1. Open `http://localhost:5420` in a browser tab **before** you start presenting (or run `docker compose up -d --build` this evening and leave it running).
2. Take the 6 screenshots listed above tonight while everything's fresh — the pages are all live right now.
3. If anyone asks "is this live or a mockup," you can literally open the dashboard on screen and click through it — that's the strongest possible answer to "was this actually built."
