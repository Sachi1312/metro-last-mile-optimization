import { useEffect, useState } from "react";
import api from "../api.js";
import { Card, PageHeader, StatTile } from "../components/ui.jsx";
import { Loading, ErrorState } from "../components/StatusStates.jsx";

// Friendlier labels for a few known feature columns; anything else falls back
// to a title-cased version of the raw column name.
const FEATURE_LABELS = {
  is_interchange: "Interchange status",
  freq_gap_ratio: "Frequency gap ratio",
  num_interventions: "Number of interventions needed",
  dissatisfaction_idx: "Survey dissatisfaction index",
  rec_trains_peak: "Recommended peak trains/hr",
  interchange_pressure: "Interchange transfer pressure",
  bus_problem_score: "Bus connectivity problem score",
  auto_problem_score: "Auto/cab problem score",
  walking_problem_score: "Walking distance problem score",
  crowding_score: "Crowding score",
  safety_score: "Safety score",
  pop_density: "Population density",
};

function featureLabel(key) {
  return FEATURE_LABELS[key] || key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function Classification() {
  const [summary, setSummary] = useState(null);
  const [details, setDetails] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([api.networkSummary(), api.classificationDetails()])
      .then(([sRes, dRes]) => {
        setSummary(sRes.data);
        setDetails(dRes.data);
      })
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <ErrorState message={error} />;
  if (!summary || !details) return <Loading label="Loading classification results" />;

  const acc = summary.model_accuracy || {};
  const topFeatures = (details.feature_importance?.XGBoost || []).slice(0, 6);
  const maxImportance = topFeatures[0]?.importance || 1;
  const foldAccuracy = details.fold_accuracy || {};

  return (
    <div>
      <PageHeader
        title="Classification"
        subtitle="Layer 1 — station severity classification via XGBoost and Random Forest, 5-fold stratified cross-validation"
      />

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 14, marginBottom: 24 }}>
        <StatTile label="XGBoost Accuracy" value={fmtPct(acc.xgb_classifier)} accent="var(--accent)" />
        <StatTile label="Random Forest Accuracy" value={fmtPct(acc.rf_classifier)} />
        <StatTile label="Stations Classified" value={summary.total_stations} />
        <StatTile label="Cross-Validation" value="5-fold" sub="Stratified" />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: 20, marginBottom: 20 }}>
        <Card style={{ padding: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>Feature Importance</h3>
          <p style={{ fontSize: 11.5, color: "var(--text-secondary)", marginBottom: 16 }}>
            Top contributing features — XGBoost classifier, from the trained model
          </p>
          {topFeatures.length === 0 ? (
            <div style={{ color: "var(--text-secondary)", fontSize: 12.5 }}>No feature importance data available.</div>
          ) : (
            topFeatures.map((f) => (
              <div key={f.feature} style={{ marginBottom: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 4 }}>
                  <span style={{ color: "var(--text-secondary)" }}>{featureLabel(f.feature)}</span>
                  <span className="mono" style={{ fontWeight: 600 }}>
                    {(f.importance * 100).toFixed(1)}%
                  </span>
                </div>
                <div style={{ height: 6, background: "#EEF1F6", borderRadius: 4, overflow: "hidden" }}>
                  <div
                    style={{
                      width: `${(f.importance / maxImportance) * 100}%`,
                      height: "100%",
                      background: "var(--accent)",
                      borderRadius: 4,
                    }}
                  />
                </div>
              </div>
            ))
          )}
        </Card>

        <Card style={{ padding: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>Severity Distribution</h3>
          <p style={{ fontSize: 11.5, color: "var(--text-secondary)", marginBottom: 16 }}>
            Predicted class balance across the network
          </p>
          {Object.entries(summary.severity_distribution || {}).map(([sev, count]) => (
            <div key={sev} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
              <span style={{ fontSize: 13, fontWeight: 500 }}>{sev}</span>
              <span className="mono" style={{ fontSize: 14, fontWeight: 700 }}>{count}</span>
            </div>
          ))}
        </Card>
      </div>

      <Card style={{ padding: 20 }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>Fold Accuracy — 5-Fold Stratified CV</h3>
        <p style={{ fontSize: 11.5, color: "var(--text-secondary)", marginBottom: 16 }}>
          Actual per-fold test accuracy from cross-validation on the trained models
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16 }}>
          {Object.keys(foldAccuracy).length === 0 ? (
            <div style={{ color: "var(--text-secondary)", fontSize: 12.5 }}>No fold accuracy data available.</div>
          ) : (
            Object.entries(foldAccuracy).map(([model, folds]) => (
              <div key={model}>
                <div style={{ fontSize: 12.5, fontWeight: 600, marginBottom: 8 }}>{model}</div>
                <div style={{ display: "flex", gap: 6 }}>
                  {folds.map((f) => (
                    <div
                      key={f.fold}
                      style={{
                        flex: 1,
                        background: "#F8FAFC",
                        border: "1px solid var(--border)",
                        borderRadius: 6,
                        padding: "8px 4px",
                        textAlign: "center",
                      }}
                    >
                      <div style={{ fontSize: 9.5, color: "var(--text-secondary)" }}>Fold {f.fold}</div>
                      <div className="mono" style={{ fontSize: 12.5, fontWeight: 700, marginTop: 2 }}>
                        {f.accuracy}%
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      </Card>
    </div>
  );
}

function fmtPct(v) {
  if (v === undefined || v === null) return "—";
  const num = v <= 1 ? v * 100 : v;
  return `${num.toFixed(1)}%`;
}
