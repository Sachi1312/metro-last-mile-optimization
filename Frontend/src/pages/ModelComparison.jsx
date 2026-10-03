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
  const [evaluation, setEvaluation] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .modelComparison()
      .then((res) => setData(res.data))
      .catch((e) => setError(e.message));
    api.expansionEvaluation().then((res) => setEvaluation(res.data)).catch(() => {});
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

      {evaluation && <HonestEvaluation evaluation={evaluation} />}
    </div>
  );
}

const HONEST_EXPLAIN = [
  {
    title: "Why two accuracies",
    body: "Published (~95%) can see the same survey scores the LMPI formula uses — so it almost copies the formula. Clean (~75%) sees only station facts: population, walk distance, bus, auto, interchange, elevated. That is the honest score.",
  },
  {
    title: "Leave one line out",
    body: "Train on three Mumbai lines and test on the held-out line. Shows whether the model generalizes to a line it never trained on.",
  },
  {
    title: "Learning curve",
    body: "As more real Mumbai stations are used for training, validation accuracy rises. With few stations the model underfits; more data helps.",
  },
  {
    title: "Delhi survey + future Mumbai",
    body: "Delhi now has survey labels (4,560 responses). We report real Delhi holdout accuracy for the Mumbai-trained clean model, plus a combined Mumbai+Delhi clean CV. Future Mumbai still has only formula agreement.",
  },
];

function countChips(counts) {
  return Object.entries(counts || {})
    .map(([k, v]) => `${k} ${v}`)
    .join(" · ");
}

function HonestEvaluation({ evaluation }) {
  const published = evaluation.leaky_severity_model;
  const clean = evaluation.clean_severity_model;
  const combined = evaluation.clean_severity_model_combined;
  const delhiHoldout = evaluation.delhi_holdout;
  const transfer = evaluation.transfer_check;
  const pct = (n) => (n == null || Number.isNaN(n) ? "—" : `${Math.round(n * 1000) / 10}%`);

  return (
    <Card style={{ padding: 20, marginTop: 20 }}>
      <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 4 }}>Honest evaluation — without spoon-feeding LMPI</h3>
      <p style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.55, marginBottom: 14 }}>
        This block answers the faculty point: what does the model find when it cannot see the LMPI formula ingredients?
      </p>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: 10,
          marginBottom: 18,
        }}
      >
        {HONEST_EXPLAIN.map((item) => (
          <div
            key={item.title}
            style={{
              padding: "12px 14px",
              background: "#F8FAFC",
              border: "1px solid var(--border)",
              borderRadius: 8,
            }}
          >
            <div style={{ fontSize: 12.5, fontWeight: 700, marginBottom: 4 }}>{item.title}</div>
            <p style={{ margin: 0, fontSize: 11.5, color: "var(--text-secondary)", lineHeight: 1.5 }}>{item.body}</p>
          </div>
        ))}
      </div>

      <h4 style={{ fontSize: 13, fontWeight: 700, marginBottom: 8 }}>Accuracy comparison</h4>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5, marginBottom: 18 }}>
        <thead>
          <tr style={{ borderBottom: "1px solid var(--border)", textAlign: "left" }}>
            <th style={{ padding: 8 }}>Model</th>
            <th style={{ padding: 8 }}>Accuracy</th>
            <th style={{ padding: 8 }}>Precision</th>
            <th style={{ padding: 8 }}>Recall</th>
            <th style={{ padding: 8 }}>F1</th>
          </tr>
        </thead>
        <tbody>
          {[
            ["Published setup (can see LMPI ingredients)", published],
            ["Clean station facts only (Mumbai 69)", clean],
            combined
              ? [`Clean combined (Mumbai + Delhi, ${combined.n_stations} stations)`, combined]
              : null,
          ]
            .filter(Boolean)
            .map(([label, row]) => (
            <tr key={label} style={{ borderBottom: "1px solid var(--border)" }}>
              <td style={{ padding: 8 }}>{label}</td>
              <td className="mono" style={{ padding: 8 }}>{pct(row.accuracy)}</td>
              <td className="mono" style={{ padding: 8 }}>{pct(row.precision_weighted)}</td>
              <td className="mono" style={{ padding: 8 }}>{pct(row.recall_weighted)}</td>
              <td className="mono" style={{ padding: 8 }}>{pct(row.f1_weighted)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h4 style={{ fontSize: 13, fontWeight: 700, marginBottom: 6 }}>Confusion matrices (Mumbai 69)</h4>
      <p style={{ fontSize: 11.5, color: "var(--text-secondary)", marginBottom: 12, lineHeight: 1.5 }}>
        Rows = true severity, columns = predicted. Numbers on the diagonal are correct predictions.
      </p>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
          gap: 16,
          marginBottom: 18,
        }}
      >
        <ConfusionMatrix
          title="Published setup"
          labels={published.labels || published.class_names}
          matrix={published.confusion_matrix}
        />
        <ConfusionMatrix
          title="Clean station facts only"
          labels={clean.labels || clean.class_names}
          matrix={clean.confusion_matrix}
        />
      </div>

      <h4 style={{ fontSize: 13, fontWeight: 700, marginBottom: 8 }}>Leave one Mumbai line out</h4>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5, marginBottom: 16 }}>
        <tbody>
          {evaluation.leave_one_line_out.map((row) => (
            <tr key={row.held_out_line} style={{ borderBottom: "1px solid var(--border)" }}>
              <td style={{ padding: 8 }}>Tested on Line {row.held_out_line}</td>
              <td className="mono" style={{ padding: 8 }}>{pct(row.accuracy)} accuracy</td>
              <td style={{ padding: 8, color: "var(--text-secondary)" }}>{row.test_stations} stations</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h4 style={{ fontSize: 13, fontWeight: 700, marginBottom: 8 }}>Learning curve, real Mumbai stations only</h4>
      {evaluation.learning_curve.map((row) => (
        <div key={row.stations} style={{ display: "flex", justifyContent: "space-between", fontSize: 12.5, padding: "4px 0" }}>
          <span>{row.stations} training stations</span>
          <span className="mono">train {pct(row.train_accuracy)} · validation {pct(row.validation_accuracy)}</span>
        </div>
      ))}

      {delhiHoldout?.accuracy != null && (
        <div style={{ marginTop: 22 }}>
          <h4 style={{ fontSize: 13, fontWeight: 700, marginBottom: 6 }}>Delhi survey holdout</h4>
          <div
            style={{
              padding: "12px 14px",
              background: "#EEF6FF",
              border: "1px solid #90CAF9",
              borderRadius: 8,
              fontSize: 12,
              lineHeight: 1.55,
              marginBottom: 14,
            }}
          >
            <strong>Real survey accuracy — not formula agreement. </strong>
            {delhiHoldout.note}
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
              gap: 14,
              marginBottom: 14,
            }}
          >
            <div
              style={{
                padding: 14,
                border: "1px solid var(--border)",
                borderRadius: 8,
                background: "#F8FAFC",
              }}
            >
              <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 6 }}>Delhi holdout accuracy</div>
              <div className="mono" style={{ fontSize: 26, fontWeight: 700 }}>
                {pct(delhiHoldout.accuracy)}
              </div>
              <div style={{ fontSize: 11.5, color: "var(--text-secondary)", marginBottom: 8 }}>
                Mumbai-trained clean model · {delhiHoldout.n_stations} stations
                {delhiHoldout.survey_responses ? ` · ${delhiHoldout.survey_responses.toLocaleString()} responses` : ""}
              </div>
              <div style={{ fontSize: 11.5, color: "var(--text-secondary)", lineHeight: 1.5 }}>
                <div>Model predicted: {countChips(delhiHoldout.predicted_severity_counts)}</div>
                <div>Survey severity: {countChips(delhiHoldout.survey_severity_counts)}</div>
              </div>
            </div>
            {combined && (
              <div
                style={{
                  padding: 14,
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  background: "#F8FAFC",
                }}
              >
                <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 6 }}>Combined clean CV</div>
                <div className="mono" style={{ fontSize: 26, fontWeight: 700 }}>
                  {pct(combined.accuracy)}
                </div>
                <div style={{ fontSize: 11.5, color: "var(--text-secondary)", marginBottom: 8 }}>
                  Mumbai 69 + Delhi survey · {combined.n_stations} labeled stations
                </div>
                <div style={{ fontSize: 11.5, color: "var(--text-secondary)", lineHeight: 1.5 }}>
                  {combined.note}
                </div>
              </div>
            )}
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
              gap: 16,
              marginBottom: 8,
            }}
          >
            <ConfusionMatrix
              title="Delhi holdout — survey vs Mumbai clean model"
              labels={delhiHoldout.labels}
              matrix={delhiHoldout.confusion_matrix}
            />
            {combined && (
              <ConfusionMatrix
                title="Combined clean CV confusion"
                labels={combined.class_names || combined.labels}
                matrix={combined.confusion_matrix}
              />
            )}
          </div>
        </div>
      )}

      {transfer?.mumbai_future && (
        <div style={{ marginTop: 22 }}>
          <h4 style={{ fontSize: 13, fontWeight: 700, marginBottom: 6 }}>Future Mumbai transfer check</h4>
          <div
            style={{
              padding: "12px 14px",
              background: "#FFF8E8",
              border: "1px solid #EF9F27",
              borderRadius: 8,
              fontSize: 12,
              lineHeight: 1.55,
              marginBottom: 14,
            }}
          >
            <strong>Agreement with formula labels — not survey accuracy. </strong>
            {transfer.note}
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
              gap: 14,
              marginBottom: 14,
            }}
          >
            <div
              style={{
                padding: 14,
                border: "1px solid var(--border)",
                borderRadius: 8,
                background: "#F8FAFC",
              }}
            >
              <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 6 }}>Mumbai future lines</div>
              <div className="mono" style={{ fontSize: 26, fontWeight: 700 }}>
                {pct(transfer.mumbai_future.agreement)}
              </div>
              <div style={{ fontSize: 11.5, color: "var(--text-secondary)", marginBottom: 8 }}>
                formula agreement · {transfer.mumbai_future.n_stations} stations
              </div>
              <div style={{ fontSize: 11.5, color: "var(--text-secondary)", lineHeight: 1.5 }}>
                <div>Model predicted: {countChips(transfer.mumbai_future.predicted_counts)}</div>
                <div>Formula band: {countChips(transfer.mumbai_future.formula_counts)}</div>
              </div>
            </div>
          </div>

          <ConfusionMatrix
            title="Future Mumbai — formula vs Mumbai model"
            labels={transfer.mumbai_future.labels}
            matrix={transfer.mumbai_future.confusion_matrix}
          />
        </div>
      )}

      <p style={{ margin: "16px 0 0", fontSize: 12.5, color: "var(--text-secondary)", lineHeight: 1.55 }}>
        Clustering found {evaluation.clusters.k} groups (silhouette {evaluation.clusters.silhouette}) and
        disagreed with the LMPI band at {evaluation.clusters.disagreement_count} of the original stations.
      </p>
    </Card>
  );
}

function ConfusionMatrix({ title, labels, matrix }) {
  if (!labels?.length || !matrix?.length) {
    return (
      <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>No confusion matrix for {title}.</div>
    );
  }

  const maxCell = Math.max(...matrix.flat(), 1);

  return (
    <div
      style={{
        padding: 14,
        border: "1px solid var(--border)",
        borderRadius: 8,
        background: "var(--card)",
      }}
    >
      <div style={{ fontSize: 12.5, fontWeight: 700, marginBottom: 10 }}>{title}</div>
      <div style={{ overflowX: "auto" }}>
        <table style={{ borderCollapse: "collapse", fontSize: 11.5, minWidth: "100%" }}>
          <thead>
            <tr>
              <th style={{ padding: "6px 8px", textAlign: "left", color: "var(--text-secondary)", fontWeight: 600 }}>
                Actual \ Pred
              </th>
              {labels.map((label) => (
                <th key={label} style={{ padding: "6px 8px", textAlign: "center", fontWeight: 600 }}>
                  {label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {labels.map((rowLabel, i) => (
              <tr key={rowLabel}>
                <td style={{ padding: "6px 8px", fontWeight: 600 }}>{rowLabel}</td>
                {(matrix[i] || []).map((value, j) => {
                  const onDiag = i === j;
                  const intensity = value / maxCell;
                  return (
                    <td
                      key={`${rowLabel}-${labels[j]}`}
                      className="mono"
                      style={{
                        padding: "8px",
                        textAlign: "center",
                        fontWeight: onDiag ? 700 : 500,
                        background: onDiag
                          ? `rgba(21, 101, 192, ${0.12 + intensity * 0.35})`
                          : value > 0
                            ? `rgba(226, 75, 74, ${0.06 + intensity * 0.2})`
                            : "transparent",
                      }}
                    >
                      {value}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
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
