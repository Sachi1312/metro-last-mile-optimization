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
import { useNetwork } from "../context/NetworkContext.jsx";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip);

const selectStyle = {
  padding: "9px 14px",
  borderRadius: 8,
  border: "1px solid var(--border)",
  background: "var(--card)",
  fontSize: 13.5,
  fontWeight: 500,
  minWidth: 160,
};

export default function DailyImpact() {
  const { network } = useNetwork();
  const [meta, setMeta] = useState(null);
  const [dayType, setDayType] = useState("weekday");
  const [windowId, setWindowId] = useState("morning_peak");
  const [impact, setImpact] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .dailyImpactWindows()
      .then((res) => {
        setMeta(res.data);
        if (res.data.day_types?.length) setDayType(res.data.day_types[0].id);
        if (res.data.windows?.length) setWindowId(res.data.windows[0].id);
      })
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (network !== "mumbai69" || !dayType || !windowId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .dailyImpact(dayType, windowId)
      .then((res) => !cancelled && setImpact(res.data))
      .catch((e) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [network, dayType, windowId]);

  if (network !== "mumbai69") {
    return (
      <div>
        <PageHeader
          title="Daily Impact"
          subtitle="Normal-day resource diversion across time windows"
        />
        <Card style={{ padding: 28, textAlign: "center", color: "var(--text-secondary)", fontSize: 13.5 }}>
          Daily Impact is available for <strong>Mumbai — 69 stations</strong> only.
          Switch the network in the sidebar to use this page.
        </Card>
      </div>
    );
  }

  if (error) return <ErrorState message={error} />;

  return (
    <div>
      <PageHeader
        title="Daily Impact"
        subtitle="Which stations are peaking in this normal-day window — and which are soft vs their own day — so trains, autos, and buses can shift where demand actually is"
        right={
          meta && (
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <select value={dayType} onChange={(e) => setDayType(e.target.value)} style={selectStyle}>
                {meta.day_types.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.label}
                  </option>
                ))}
              </select>
              <select value={windowId} onChange={(e) => setWindowId(e.target.value)} style={selectStyle}>
                {meta.windows.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.label}
                  </option>
                ))}
              </select>
            </div>
          )
        }
      />

      {loading || !impact ? (
        <Loading label={`Loading ${dayType} ${windowId.replace(/_/g, " ")} impact`} />
      ) : (
        <>
          {impact.caveat && (
            <div
              style={{
                padding: "12px 16px",
                background: "#FFF8E8",
                border: "1px solid #EF9F27",
                borderRadius: 8,
                fontSize: 12,
                color: "var(--text-primary)",
                lineHeight: 1.6,
                marginBottom: 20,
              }}
            >
              <strong>Data limitation:</strong> {impact.caveat}
            </div>
          )}

          <Card style={{ padding: 20, marginBottom: 20 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>
              Share of own day in window — {impact.day_type_label} · {impact.window_label}
            </h3>
            <p style={{ fontSize: 11.5, color: "var(--text-secondary)", marginBottom: 16 }}>
              All {impact.station_count} stations, ranked by % of each station&apos;s own daily riders that fall
              in this window (hours {impact.hours?.[0]}–{impact.hours?.[impact.hours.length - 1]}; network
              average share: {impact.network_avg_window_share_pct}%). Absolute riders shown in tooltips.
            </p>
            <RankedChart
              stations={impact.stations}
              networkAvgShare={impact.network_avg_window_share_pct}
            />
          </Card>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: 20 }}>
            <StationGroup
              title="Peaking now — Shift Resources Here"
              subtitle="This window is a large share of their own day — deploy extra trains, autos, and staff here"
              stations={impact.surge_stations}
              tone="surge"
              networkAvgShare={impact.network_avg_window_share_pct}
              topShare={impact.stations[0]?.avg_window_share_pct}
              topStationName={impact.stations[0]?.station_name}
            />
            <StationGroup
              title="Soft now — Divert Resources From Here"
              subtitle="This window is a small share of their own day — trim window-specific top-up and route capacity to peaking stations"
              stations={impact.quiet_stations}
              tone="quiet"
              networkAvgShare={impact.network_avg_window_share_pct}
              topShare={impact.stations[0]?.avg_window_share_pct}
              topStationName={impact.stations[0]?.station_name}
            />
          </div>
        </>
      )}
    </div>
  );
}

function RankedChart({ stations, networkAvgShare }) {
  const top = stations.slice(0, 20);
  const chartData = {
    labels: top.map((s) => s.station_name),
    datasets: [
      {
        label: "Share of own day (%)",
        data: top.map((s) => s.avg_window_share_pct),
        backgroundColor: top.map((s) =>
          s.avg_window_share_pct >= (networkAvgShare || 0) ? "#E24B4A" : "#1D9E75"
        ),
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
                  return `${ctx.parsed.x}% of own day · ${s.avg_window_footfall.toLocaleString()} riders in window`;
                },
              },
            },
          },
          scales: {
            x: {
              grid: { color: "#EEF1F6" },
              ticks: {
                font: { family: "JetBrains Mono", size: 10 },
                callback: (v) => `${v}%`,
              },
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

function StationGroup({ title, subtitle, stations, tone, networkAvgShare, topShare, topStationName }) {
  const accent = tone === "surge" ? "var(--critical)" : "var(--low)";
  return (
    <Card style={{ padding: 20 }}>
      <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 4, color: accent }}>{title}</h3>
      <p style={{ fontSize: 11.5, color: "var(--text-secondary)", marginBottom: tone === "quiet" ? 8 : 14 }}>
        {subtitle}
      </p>
      {tone === "quiet" && topShare != null && (
        <p style={{ fontSize: 11, color: "var(--text-secondary)", marginBottom: 6, fontStyle: "italic" }}>
          Spare capacity from these stations can move to {topStationName} and other peaking stations
          (up to {topShare}% of their own day in this window).
        </p>
      )}
      {tone === "quiet" && (
        <p style={{ fontSize: 11, color: "var(--text-secondary)", marginBottom: 14, lineHeight: 1.5 }}>
          Note: everyday severity (Critical/High) is year-round last-mile pressure, not this window&apos;s
          share. A Critical hub can still appear here if it is <em>soft relative to its own day</em> in
          this band — divert window-specific top-up, not cut base service.
        </p>
      )}
      {stations.length === 0 ? (
        <div style={{ color: "var(--text-secondary)", fontSize: 12.5 }}>No stations in this group.</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {stations.map((s) => (
            <div
              key={s.station_name}
              style={{
                padding: "10px 12px",
                border: "1px solid var(--border)",
                borderLeft: `3px solid ${accent}`,
                borderRadius: 8,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10 }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ fontSize: 12.5, fontWeight: 600 }}>{s.station_name}</span>
                    {s.severity_label && <SeverityBadge severity={s.severity_label} />}
                  </div>
                  <div style={{ fontSize: 10.5, color: "var(--text-secondary)", marginTop: 2 }}>
                    Line {s.line}
                    {s.share_vs_network_pct != null && (
                      <>
                        {" "}
                        · {s.share_vs_network_pct >= 0 ? "+" : ""}
                        {s.share_vs_network_pct}% vs network share
                      </>
                    )}
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div className="mono" style={{ fontSize: 14, fontWeight: 700, color: accent }}>
                    {s.avg_window_share_pct}%
                  </div>
                  <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>of own day</div>
                  <div style={{ fontSize: 10, color: "var(--text-secondary)", marginTop: 2 }}>
                    {s.avg_window_footfall.toLocaleString()} riders in window
                  </div>
                  {s.suggested_shift_trains_hr != null && (
                    <div style={{ fontSize: 10, color: "var(--text-secondary)", marginTop: 2 }}>
                      {s.suggested_shift_trains_hr >= 0 ? "+" : ""}
                      {s.suggested_shift_trains_hr} trains/hr vs avg share
                    </div>
                  )}
                </div>
              </div>
              {tone === "quiet" && networkAvgShare > 0 && (
                <div style={{ fontSize: 10.5, color: "var(--text-secondary)", marginTop: 6 }}>
                  {Math.round((s.avg_window_share_pct / networkAvgShare) * 100)}% of network average window
                  share ({networkAvgShare}%)
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
