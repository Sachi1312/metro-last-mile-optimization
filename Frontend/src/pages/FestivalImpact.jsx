import { useEffect, useState } from "react";
import { Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
} from "chart.js";
import api from "../api.js";
import { Card, PageHeader } from "../components/ui.jsx";
import { Loading, ErrorState } from "../components/StatusStates.jsx";
import SeverityBadge from "../components/SeverityBadge.jsx";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip);

export default function FestivalImpact() {
  const [festivals, setFestivals] = useState(null);
  const [selected, setSelected] = useState("");
  const [impact, setImpact] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .festivals()
      .then((res) => {
        setFestivals(res.data.festivals);
        if (res.data.festivals.length) setSelected(res.data.festivals[0]);
      })
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!selected) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .festivalImpact(selected)
      .then((res) => !cancelled && setImpact(res.data))
      .catch((e) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [selected]);

  if (error) return <ErrorState message={error} />;

  return (
    <div>
      <PageHeader
        title="Festival Impact"
        subtitle="Which stations surge and which stay quiet on a given festival — so resources shift there instead of sitting idle elsewhere"
        right={
          festivals && (
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
                minWidth: 200,
              }}
            >
              {festivals.map((f) => (
                <option key={f} value={f}>
                  {f}
                </option>
              ))}
            </select>
          )
        }
      />

      {loading || !impact ? (
        <Loading label={`Loading ${selected || "festival"} impact`} />
      ) : (
        <>
          <Card style={{ padding: 20, marginBottom: 20 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>
              Extra Riders by Station — {impact.festival}
            </h3>
            <p style={{ fontSize: 11.5, color: "var(--text-secondary)", marginBottom: 16 }}>
              All {impact.station_count} stations, ranked by extra riders vs. each station's own normal-day average.
              (The dataset's festival multiplier is close to uniform network-wide — ranking by that percentage alone
              wouldn't separate stations meaningfully, so this ranks by absolute rider increase, which does.)
            </p>
            <RankedChart stations={impact.stations} />
          </Card>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: 20 }}>
            <StationGroup
              title="Surge Stations — Shift Resources Here"
              subtitle="Largest absolute increase in riders — deploy extra trains, autos, and staff here on this festival"
              stations={impact.surge_stations}
              tone="surge"
            />
            <StationGroup
              title="Quiet Stations — Safe to Reduce"
              subtitle="Flat or below-baseline riders on this festival — frequency can be trimmed without impact"
              stations={impact.quiet_stations}
              tone="quiet"
            />
          </div>
        </>
      )}
    </div>
  );
}

function RankedChart({ stations }) {
  const top = stations.slice(0, 20);
  const chartData = {
    labels: top.map((s) => s.station_name),
    datasets: [
      {
        label: "Extra riders",
        data: top.map((s) => s.extra_riders),
        backgroundColor: top.map((s) => (s.extra_riders >= 0 ? "#1D9E75" : "#E24B4A")),
        borderRadius: 4,
        maxBarThickness: 26,
      },
    ],
  };
  return (
    <div style={{ height: 340 }}>
      <Bar
        data={chartData}
        options={{
          responsive: true,
          maintainAspectRatio: false,
          indexAxis: "y",
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: (ctx) => {
                  const s = top[ctx.dataIndex];
                  return `${ctx.parsed.x > 0 ? "+" : ""}${ctx.parsed.x.toLocaleString()} riders vs normal day (${s.avg_festival_boost >= 0 ? "+" : ""}${Math.round(s.avg_festival_boost * 100)}% network rate)`;
                },
              },
            },
          },
          scales: {
            x: {
              grid: { color: "#EEF1F6" },
              ticks: { font: { family: "JetBrains Mono", size: 10 }, callback: (v) => v.toLocaleString() },
            },
            y: {
              grid: { display: false },
              ticks: { font: { family: "Inter", size: 10.5 } },
            },
          },
        }}
      />
    </div>
  );
}

function StationGroup({ title, subtitle, stations, tone }) {
  const accent = tone === "surge" ? "var(--critical)" : "var(--low)";
  return (
    <Card style={{ padding: 20 }}>
      <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 4, color: accent }}>{title}</h3>
      <p style={{ fontSize: 11.5, color: "var(--text-secondary)", marginBottom: 14 }}>{subtitle}</p>
      {stations.length === 0 ? (
        <div style={{ color: "var(--text-secondary)", fontSize: 12.5 }}>
          {tone === "quiet"
            ? "No station shows reduced demand for this festival — every station sees a genuine surge, network-wide."
            : "No stations in this group."}
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {stations.map((s) => (
            <div
              key={s.station_name}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "10px 12px",
                border: "1px solid var(--border)",
                borderLeft: `3px solid ${accent}`,
                borderRadius: 8,
                gap: 10,
              }}
            >
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span style={{ fontSize: 12.5, fontWeight: 600 }}>{s.station_name}</span>
                  {s.severity_label && <SeverityBadge severity={s.severity_label} />}
                </div>
                <div style={{ fontSize: 10.5, color: "var(--text-secondary)", marginTop: 2 }}>Line {s.line}</div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div className="mono" style={{ fontSize: 14, fontWeight: 700, color: accent }}>
                  {s.extra_riders >= 0 ? "+" : ""}
                  {s.extra_riders.toLocaleString()}
                </div>
                <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>riders vs normal day</div>
                {s.suggested_extra_trains_hr !== null && s.suggested_extra_trains_hr !== undefined && (
                  <div style={{ fontSize: 10, color: "var(--text-secondary)", marginTop: 2 }}>
                    {s.suggested_extra_trains_hr >= 0 ? "+" : ""}
                    {s.suggested_extra_trains_hr} trains/hr
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
