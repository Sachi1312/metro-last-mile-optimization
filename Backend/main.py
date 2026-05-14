# ============================================================
# main.py — FastAPI Backend
# Mumbai Metro Resource Optimization System
# Endpoints:
#   GET /                          → health check
#   GET /network/summary           → network overview stats
#   GET /stations                  → all 69 stations
#   GET /station/{name}            → single station full profile
#   GET /forecast/{station}        → 30-day forecast
#   GET /forecast/2026/{station}   → 2026 H1 forecast
#   GET /interventions             → ranked intervention queue
#   GET /frequency/{station}       → trains/hr recommendations
#   GET /interchange               → sync analysis all 3 stations
#   GET /lmpi/line/{line}          → all stations on a line
# ============================================================

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from database import get_db
from datetime import datetime
import os

app = FastAPI(
    title="MetroOpt API",
    description="Mumbai Metro Resource Optimization System",
    version="1.0.0"
)

# ── CORS — allows dashboard HTML to call this API ─────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

db = get_db()

# ── Helper: clean MongoDB doc ─────────────────────────────────
def clean(doc):
    """Remove MongoDB _id and convert to serializable format."""
    if doc is None:
        return None
    doc.pop("_id", None)
    for k, v in doc.items():
        if isinstance(v, datetime):
            doc[k] = v.isoformat()
    return doc

def clean_many(docs):
    return [clean(d) for d in docs]

# ══════════════════════════════════════════════════════════════
# ROOT — Health check
# ══════════════════════════════════════════════════════════════
@app.get("/")
def root():
    meta = db["project_metadata"].find_one({}, {"_id": 0})
    return {
        "status":      "online",
        "project":     "MetroOpt — Mumbai Metro Resource Optimization",
        "version":     "1.0.0",
        "database":    "metropt (MongoDB Atlas)",
        "collections": db.list_collection_names(),
        "last_updated": meta.get("last_updated") if meta else None,
    }

# ══════════════════════════════════════════════════════════════
# NETWORK SUMMARY
# ══════════════════════════════════════════════════════════════
@app.get("/network/summary")
def network_summary():
    """Overall network stats for dashboard top metrics."""
    meta = db["project_metadata"].find_one({}, {"_id": 0})

    # LMPI distribution
    lmpi_dist = {}
    for sev in ["Critical","High","Medium","Low"]:
        lmpi_dist[sev] = db["lmpi_scores"].count_documents({"severity_label": sev})

    # Top critical station
    top = db["lmpi_scores"].find_one(
        {"severity_label": "Critical"},
        sort=[("lmpi_score", -1)],
        projection={"_id": 0, "station_name": 1, "lmpi_score": 1}
    )

    # Avg LMPI
    pipeline = [{"$group": {"_id": None, "avg_lmpi": {"$avg": "$lmpi_score"}}}]
    avg_result = list(db["lmpi_scores"].aggregate(pipeline))
    avg_lmpi = round(avg_result[0]["avg_lmpi"], 1) if avg_result else 0

    # Frequency stats
    freq_pipeline = [
        {"$match": {"time_window": "morning_peak"}},
        {"$group": {"_id": None,
                    "total_delta": {"$sum": "$delta_trains_hr"},
                    "avg_delta":   {"$avg": "$delta_trains_hr"}}}
    ]
    freq_result = list(db["results_frequency"].aggregate(freq_pipeline))

    return {
        "total_stations":     db["stations"].count_documents({}),
        "total_lines":        4,
        "severity_distribution": lmpi_dist,
        "avg_lmpi_score":     avg_lmpi,
        "top_critical_station": clean(top),
        "model_accuracy": meta.get("model_accuracy") if meta else {},
        "interchange_stations": meta.get("interchange_stations") if meta else [],
        "frequency_stats": {
            "total_additional_trains_peak": round(freq_result[0]["total_delta"], 1) if freq_result else 0,
            "avg_additional_trains_peak":   round(freq_result[0]["avg_delta"], 1)   if freq_result else 0,
        },
        "data_range": meta.get("data_range") if meta else {},
        "forecast_range": meta.get("forecast_range") if meta else {},
    }

# ══════════════════════════════════════════════════════════════
# ALL STATIONS
# ══════════════════════════════════════════════════════════════
@app.get("/stations")
def get_all_stations(line: str = None):
    """
    Get all 69 stations with LMPI scores and severity.
    Optional filter: ?line=1 or ?line=2A or ?line=7 or ?line=3
    """
    # Base station info
    station_filter = {"line": line} if line else {}
    stations = list(db["stations"].find(station_filter, {"_id": 0}))

    # Merge LMPI scores
    lmpi_map = {
        d["station_name"]: d
        for d in db["lmpi_scores"].find({}, {"_id": 0})
    }

    # Merge final recommendations
    rec_map = {
        d["station_name"]: d
        for d in db["results_final_recommendations"].find({}, {"_id": 0})
    }

    result = []
    for st in stations:
        name = st["station_name"]
        lmpi = lmpi_map.get(name, {})
        rec  = rec_map.get(name, {})
        result.append({
            "station_name":          name,
            "line":                  st.get("line"),
            "role":                  st.get("role"),
            "is_interchange":        st.get("is_interchange"),
            "is_elevated":           st.get("is_elevated"),
            "pop_density":           st.get("pop_density"),
            "lmpi_score":            lmpi.get("lmpi_score"),
            "severity_label":        lmpi.get("severity_label"),
            "recommended_last_mile": lmpi.get("recommended_last_mile"),
            "priority_rank":         rec.get("priority_rank"),
            "optimization_score":    rec.get("optimization_score"),
            "rec_trains_peak":       rec.get("rec_trains_peak"),
            "fore_avg_daily":        rec.get("fore_avg_daily"),
        })

    # Sort by LMPI descending
    result.sort(key=lambda x: x.get("lmpi_score") or 0, reverse=True)
    return {"count": len(result), "stations": result}

# ══════════════════════════════════════════════════════════════
# SINGLE STATION DETAIL
# ══════════════════════════════════════════════════════════════
@app.get("/station/{station_name}")
def get_station(station_name: str):
    """Full profile for a single station."""

    # Station master
    st = db["stations"].find_one({"station_name": station_name}, {"_id": 0})
    if not st:
        raise HTTPException(status_code=404, detail=f"Station '{station_name}' not found")

    # LMPI scores
    lmpi = clean(db["lmpi_scores"].find_one({"station_name": station_name}, {"_id": 0}))

    # Layer 1 prediction
    l1 = clean(db["results_layer1"].find_one({"station_name": station_name}, {"_id": 0}))

    # Frequency recommendations
    freq = clean_many(db["results_frequency"].find(
        {"station_name": station_name}, {"_id": 0}
    ))

    # Top interventions (max 3)
    interventions = clean_many(db["results_interventions"].find(
        {"station_name": station_name}, {"_id": 0},
    ).limit(3))

    # 30-day forecast (last 7 days as preview)
    forecast_30 = clean_many(db["results_forecast_30day"].find(
        {"station_name": station_name}, {"_id": 0}
    ).sort("date", 1).limit(7))

    # 2026 forecast summary by month
    forecast_2026 = list(db["results_forecast_2026"].aggregate([
        {"$match": {"station_name": station_name}},
        {"$group": {
            "_id": "$month_name",
            "avg_footfall": {"$avg": "$forecasted_footfall"},
            "max_footfall": {"$max": "$forecasted_footfall"},
            "reliability":  {"$first": "$reliability"},
        }},
        {"$sort": {"_id": 1}},
    ]))
    forecast_2026 = [
        {"month": d["_id"],
         "avg_footfall": round(d["avg_footfall"]),
         "max_footfall": d["max_footfall"],
         "reliability":  d["reliability"]}
        for d in forecast_2026
    ]

    # Interchange sync (if applicable)
    sync = clean_many(db["results_interchange_sync"].find(
        {"station": station_name,
         "event_type": "Normal",
         "time_window": {"$in": ["morning_peak","evening_peak"]}},
        {"_id": 0}
    ))

    # Optimization score
    opt = clean(db["results_optimization"].find_one(
        {"station_name": station_name}, {"_id": 0}
    ))

    return {
        "station_info":      st,
        "lmpi":              lmpi,
        "classification":    l1,
        "frequency":         freq,
        "interventions":     interventions,
        "forecast_30day":    forecast_30,
        "forecast_2026":     forecast_2026,
        "interchange_sync":  sync,
        "optimization":      opt,
    }

# ══════════════════════════════════════════════════════════════
# 30-DAY FORECAST
# ══════════════════════════════════════════════════════════════
@app.get("/forecast/{station_name}")
def get_forecast_30day(station_name: str):
    """30-day footfall forecast for a station."""
    docs = clean_many(db["results_forecast_30day"].find(
        {"station_name": station_name},
        {"_id": 0}
    ).sort("date", 1))

    if not docs:
        raise HTTPException(status_code=404,
                            detail=f"No forecast found for '{station_name}'")

    total  = sum(d.get("forecasted_footfall", 0) for d in docs)
    avg    = round(total / len(docs)) if docs else 0
    peak   = max(d.get("forecasted_footfall", 0) for d in docs)

    return {
        "station_name":    station_name,
        "forecast_period": "30 days",
        "total_forecasted":total,
        "avg_daily":       avg,
        "peak_day":        peak,
        "daily_forecast":  docs,
    }

# ══════════════════════════════════════════════════════════════
# 2026 FORECAST
# ══════════════════════════════════════════════════════════════
@app.get("/forecast/2026/{station_name}")
def get_forecast_2026(station_name: str, month: str = None):
    """
    Jan–Jun 2026 forecast for a station.
    Optional filter: ?month=January
    """
    query = {"station_name": station_name}
    if month:
        query["month_name"] = month

    docs = clean_many(db["results_forecast_2026"].find(
        query, {"_id": 0}
    ).sort("date", 1))

    if not docs:
        raise HTTPException(status_code=404,
                            detail=f"No 2026 forecast for '{station_name}'")

    # Monthly summary
    from collections import defaultdict
    monthly = defaultdict(list)
    for d in docs:
        monthly[d.get("month_name","")].append(d.get("forecasted_footfall", 0))

    monthly_summary = [
        {"month":        m,
         "avg_footfall": round(sum(v)/len(v)),
         "total":        sum(v),
         "days":         len(v)}
        for m, v in monthly.items()
    ]

    return {
        "station_name":     station_name,
        "forecast_period":  "Jan 2026 – Jun 2026",
        "model":            "XGBoost",
        "monthly_summary":  monthly_summary,
        "daily_forecast":   docs,
        "reliability_note": "High (Jan–Mar) | Good (Apr–May) | Moderate (Jun)",
    }

# ══════════════════════════════════════════════════════════════
# INTERVENTIONS
# ══════════════════════════════════════════════════════════════
@app.get("/interventions")
def get_interventions(severity: str = None, limit: int = 20):
    """
    Ranked intervention queue.
    Optional filter: ?severity=Critical
    """
    query = {}
    if severity:
        query["severity_label"] = severity

    docs = clean_many(db["results_interventions"].find(
        query, {"_id": 0}
    ).sort("priority_score", -1).limit(limit))

    return {
        "count":         len(docs),
        "filter":        severity or "all",
        "interventions": docs,
    }

# ══════════════════════════════════════════════════════════════
# FREQUENCY RECOMMENDATIONS
# ══════════════════════════════════════════════════════════════
@app.get("/frequency/{station_name}")
def get_frequency(station_name: str):
    """Frequency recommendations for all time windows."""
    docs = clean_many(db["results_frequency"].find(
        {"station_name": station_name},
        {"_id": 0}
    ).sort("time_window", 1))

    if not docs:
        raise HTTPException(status_code=404,
                            detail=f"No frequency data for '{station_name}'")

    return {
        "station_name": station_name,
        "windows":      docs,
    }

# ══════════════════════════════════════════════════════════════
# INTERCHANGE SYNC
# ══════════════════════════════════════════════════════════════
@app.get("/interchange")
def get_interchange(event_type: str = "Normal"):
    """
    Interchange sync analysis for all 3 metro↔metro stations.
    Optional filter: ?event_type=Ganesh Chaturthi
    """
    docs = clean_many(db["results_interchange_sync"].find(
        {"event_type": event_type},
        {"_id": 0}
    ).sort([("station", 1), ("time_window", 1)]))

    # Summary per station
    from collections import defaultdict
    summary = defaultdict(lambda: {"excellent":0,"good":0,"poor":0,"total":0})
    for d in docs:
        st  = d.get("station","")
        q   = d.get("sync_quality","").lower()
        summary[st][q] = summary[st].get(q, 0) + 1
        summary[st]["total"] += 1

    return {
        "event_type": event_type,
        "stations":   list(summary.keys()),
        "summary":    dict(summary),
        "details":    docs,
    }

# ══════════════════════════════════════════════════════════════
# STATIONS BY LINE
# ══════════════════════════════════════════════════════════════
@app.get("/lmpi/line/{line}")
def get_line_stations(line: str):
    """All stations on a specific line with LMPI scores."""
    docs = clean_many(db["lmpi_scores"].find(
        {"line": line},
        {"_id": 0}
    ).sort("lmpi_score", -1))

    if not docs:
        raise HTTPException(status_code=404,
                            detail=f"No stations found for line '{line}'")

    avg_lmpi = round(sum(d.get("lmpi_score",0) for d in docs) / len(docs), 1)

    sev_dist = {}
    for sev in ["Critical","High","Medium","Low"]:
        sev_dist[sev] = sum(1 for d in docs if d.get("severity_label")==sev)

    return {
        "line":                 line,
        "station_count":        len(docs),
        "avg_lmpi":             avg_lmpi,
        "severity_distribution":sev_dist,
        "stations":             docs,
    }

# ══════════════════════════════════════════════════════════════
# RUN SERVER
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)