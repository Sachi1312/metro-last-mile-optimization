import { useEffect, useMemo, useState } from "react";
import { Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
} from "chart.js";
import api from "../api.js";
import { Card, PageHeader, StatTile } from "../components/ui.jsx";
import { Loading, ErrorState } from "../components/StatusStates.jsx";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip);

const SEASONAL_EFFECTS = [
  { month: "January", effect: "Post-holiday normalization", impact: "Baseline" },
  { month: "February", effect: "Steady office commute demand", impact: "Baseline" },
  { month: "March", effect: "Financial year-end travel uptick", impact: "+3–5%" },
  { month: "April", effect: "Summer heat reduces walking last-mile", impact: "+2%" },
  { month: "May", effect: "School vacation, lower weekday peaks", impact: "-4%" },
  { month: "June", effect: "Monsoon onset shifts mode to metro", impact: "+6–8%" },
];

export default function Forecasting() {
  const [allStations, setAllStations] = useState(null);
  const [selected, setSelected] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .stations()
      .then((res) => {
        setAllStations(res.data.stations);
        if (res.data.stations.length) {
          setSelected(res.data.stations[0].station_name);
        }
      })
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!selected) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .forecast2026(selected)
      .then((res) => !cancelled && setData(res.data))
      .catch((e) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [selected]);

  if (error) return <ErrorState message={error} />;

  const monthly = data?.monthly_summary || [];

  return (
    <div>
      <PageHeader
        title="Forecasting"
        subtitle="Layer 3 — XGBoost time-series forecasting, Jan–Jun 2026, per station"
        right={
          allStations && (
            <select
              value={selected}
              onChange={(e) => setSelected(e.target.value)}
              style={{
                padding: "9px 14px",
                borderRadius: 8,
                border: "1px solid var(--border)",
                background: "var(--card)",
                fontSize: 13.5,
                fontWeight: 500,
                minWidth: 220,
              }}
            >
              {allStations.map((s) => (
                <option key={s.station_name} value={s.station_name}>
                  {s.station_name} ({s.severity_label})
                </option>
              ))}
            </select>
          )
        }
      />

      {loading || !data ? (
        <Loading label={`Loading forecast for ${selected || "station"}`} />
      ) : (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 14, marginBottom: 24 }}>
            <StatTile label="Model" value={data.model} />
            <StatTile label="Forecast Period" value="Jan – Jun 2026" />
            <StatTile label="Network MAPE" value="2.64%" accent="var(--accent)" />
            <StatTile label="Network R²" value="0.9985" />
          </div>

          <Card style={{ padding: 20, marginBottom: 20 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>Monthly Forecast — {data.station_name}</h3>
            <p style={{ fontSize: 11.5, color: "var(--text-secondary)", marginBottom: 16 }}>{data.reliability_note}</p>
            <MonthlyChart monthly={monthly} />
          </Card>

          <Card style={{ padding: 20 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 16 }}>Seasonal Effects</h3>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  <th style={thStyle}>Month</th>
                  <th style={thStyle}>Seasonal Driver</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Expected Impact</th>
                </tr>
              </thead>
              <tbody>
                {SEASONAL_EFFECTS.map((row) => (
                  <tr key={row.month} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={tdStyle}>{row.month}</td>
                    <td style={{ ...tdStyle, color: "var(--text-secondary)" }}>{row.effect}</td>
                    <td className="mono" style={{ ...tdStyle, textAlign: "right", fontWeight: 600 }}>
                      {row.impact}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </>
      )}
    </div>
  );
}

const thStyle = { textAlign: "left", padding: "8px 10px", color: "var(--text-secondary)", fontWeight: 600, fontSize: 11.5 };
const tdStyle = { padding: "10px 10px" };

function MonthlyChart({ monthly }) {
  const chartData = useMemo(
    () => ({
      labels: monthly.map((m) => m.month),
      datasets: [
        {
          label: "Avg daily footfall",
          data: monthly.map((m) => m.avg_footfall),
          backgroundColor: "#1565C0",
          borderRadius: 4,
          maxBarThickness: 48,
        },
      ],
    }),
    [monthly]
  );

  if (!monthly.length) return <div style={{ color: "var(--text-secondary)", fontSize: 12.5 }}>No forecast data available.</div>;

  return (
    <div style={{ height: 280 }}>
      <Bar
        data={chartData}
        options={{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: { callbacks: { label: (ctx) => `${ctx.parsed.y.toLocaleString()} riders/day` } },
          },
          scales: {
            x: { grid: { display: false }, ticks: { font: { family: "Inter", size: 11 } } },
            y: {
              grid: { color: "#EEF1F6" },
              ticks: { font: { family: "JetBrains Mono", size: 10 }, callback: (v) => v.toLocaleString() },
            },
          },
        }}
      />
    </div>
  );
}
