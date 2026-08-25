import { useEffect, useState } from "react";
import { Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
  Legend,
} from "chart.js";
import api from "../api.js";
import { Card, PageHeader } from "../components/ui.jsx";
import { Loading, ErrorState } from "../components/StatusStates.jsx";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

const MODEL_COLORS = {
  XGBoost: "#1565C0",
  "Random Forest": "#27ae60",
  "Logistic Regression": "#8e44ad",
  "Decision Tree": "#E24B4A",
  Prophet: "#EF9F27",
  "Linear Regression": "#8e44ad",
  "Seasonal Naive": "#94A3B8",
};

export default function ModelComparison() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .modelComparison()
      .then((res) => setData(res.data))
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <ErrorState message={error} />;
  if (!data) return <Loading label="Loading model comparison" />;

  const { classification, forecasting } = data;

  return (
    <div>
      <PageHeader
        title="Model Comparison"
        subtitle="Every model trained or evaluated in this project, compared on held-out accuracy — the basis for choosing XGBoost as the production model"
      />

      <Card style={{ padding: 20, marginBottom: 20 }}>
        <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 4 }}>Classification — Severity Prediction</h3>
        <p style={{ fontSize: 11.5, color: "var(--text-secondary)", marginBottom: 16 }}>
          5-fold stratified cross-validation accuracy, identical feature set and folds across all four models
        </p>
        <ClassificationChart summary={classification.summary} />
        <SummaryTable
          rows={classification.summary}
          columns={[
            { key: "model", label: "Model" },
            { key: "cv_accuracy_pct", label: "CV Accuracy", suffix: "%" },
            { key: "f1_weighted_pct", label: "F1 (weighted)", suffix: "%" },
            { key: "note", label: "Note", muted: true },
          ]}
        />
        <Verdict>
          <strong>XGBoost chosen</strong> for classification: matches or leads on CV accuracy (95.6%) while
          handling the mixed numeric/categorical feature set natively and giving usable feature-importance
          rankings for interpretability. The single Decision Tree overfits badly (100% train vs 92.7% test —
          a 7.3-point gap) which is exactly the failure mode Random Forest's ensembling exists to fix.
          Logistic Regression ties on accuracy here only because the classes are strongly separated by a few
          dominant features (e.g. interchange status), which won't generalize as well if the feature set grows.
        </Verdict>
      </Card>

      <Card style={{ padding: 20 }}>
        <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 4 }}>Forecasting — Daily Footfall</h3>
        <p style={{ fontSize: 11.5, color: "var(--text-secondary)", marginBottom: 16 }}>
          Held-out test error — XGBoost and the seasonal-naive baseline share the exact same chronological
          80/20 split and test rows; Prophet's figures are averaged across its 6 evaluated sample stations
        </p>
        <ForecastingChart summary={forecasting.summary} />
        <SummaryTable
          rows={forecasting.summary}
          columns={[
            { key: "model", label: "Model" },
            { key: "mape", label: "MAPE", suffix: "%" },
            { key: "mae", label: "MAE (riders)" },
            { key: "r2", label: "R²" },
            { key: "coverage", label: "Coverage", muted: true },
          ]}
        />
        <Verdict>
          <strong>XGBoost chosen</strong> for forecasting: 2.64% MAPE against a 14.61% MAPE seasonal-naive
          baseline shows the model is capturing real signal beyond "same day last week," and it beats
          Prophet's per-station average (5.41% MAPE) by combining calendar, festival, monsoon, and
          interchange features Prophet doesn't use directly. Tellingly, Linear Regression trained on the
          exact same feature set XGBoost uses still comes in at 16.73% MAPE — worse than the naive
          baseline — confirming the footfall relationships are meaningfully nonlinear and a tree-based
          model is doing real work here, not just having more features to lean on.
        </Verdict>
      </Card>
    </div>
  );
}

function ClassificationChart({ summary }) {
  const chartData = {
    labels: summary.map((s) => s.model),
    datasets: [
      {
        label: "CV Accuracy (%)",
        data: summary.map((s) => s.cv_accuracy_pct),
        backgroundColor: summary.map((s) => MODEL_COLORS[s.model] || "#94A3B8"),
        borderRadius: 4,
        maxBarThickness: 70,
      },
    ],
  };
  return (
    <div style={{ height: 240, marginBottom: 16 }}>
      <Bar
        data={chartData}
        options={{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: { callbacks: { label: (ctx) => `${ctx.parsed.y}%` } },
          },
          scales: {
            x: { grid: { display: false }, ticks: { font: { family: "Inter", size: 11 } } },
            y: {
              min: 80,
              max: 100,
              grid: { color: "#EEF1F6" },
              ticks: { font: { family: "JetBrains Mono", size: 10 }, callback: (v) => `${v}%` },
            },
          },
        }}
      />
    </div>
  );
}

function ForecastingChart({ summary }) {
  const chartData = {
    labels: summary.map((s) => s.model),
    datasets: [
      {
        label: "MAPE (%)",
        data: summary.map((s) => s.mape),
        backgroundColor: summary.map((s) => MODEL_COLORS[s.model] || "#94A3B8"),
        borderRadius: 4,
        maxBarThickness: 70,
      },
    ],
  };
  return (
    <div style={{ height: 240, marginBottom: 16 }}>
      <Bar
        data={chartData}
        options={{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: { callbacks: { label: (ctx) => `${ctx.parsed.y}% MAPE (lower is better)` } },
          },
          scales: {
            x: { grid: { display: false }, ticks: { font: { family: "Inter", size: 11 } } },
            y: {
              grid: { color: "#EEF1F6" },
              ticks: { font: { family: "JetBrains Mono", size: 10 }, callback: (v) => `${v}%` },
            },
          },
        }}
      />
    </div>
  );
}

function SummaryTable({ rows, columns }) {
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
        <thead>
          <tr style={{ borderBottom: "1px solid var(--border)" }}>
            {columns.map((c) => (
              <th
                key={c.key}
                style={{ textAlign: c.key === "model" ? "left" : "right", padding: "8px 10px", color: "var(--text-secondary)", fontWeight: 600, fontSize: 11.5 }}
              >
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.model} style={{ borderBottom: "1px solid var(--border)" }}>
              {columns.map((c) => (
                <td
                  key={c.key}
                  className={c.key === "model" ? "" : "mono"}
                  style={{
                    padding: "10px 10px",
                    textAlign: c.key === "model" ? "left" : "right",
                    fontWeight: c.key === "model" ? 600 : 500,
                    color: c.muted ? "var(--text-secondary)" : "var(--text-primary)",
                    fontSize: c.muted ? 11 : 12.5,
                  }}
                >
                  {r[c.key]}
                  {c.suffix || ""}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Verdict({ children }) {
  return (
    <div
      style={{
        marginTop: 16,
        padding: "12px 16px",
        background: "var(--accent-light)",
        border: "1px solid var(--accent)",
        borderRadius: 8,
        fontSize: 12.5,
        color: "var(--text-primary)",
        lineHeight: 1.6,
      }}
    >
      {children}
    </div>
  );
}
