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
import { Card, PageHeader } from "../components/ui.jsx";
import { Loading, ErrorState } from "../components/StatusStates.jsx";
import SeverityBadge, { severityColor } from "../components/SeverityBadge.jsx";
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

const SEVERITY_LEGEND = [
  { label: "Critical", color: "#E24B4A" },
  { label: "High", color: "#EF9F27" },
  { label: "Medium", color: "#BA7517" },
  { label: "Other", color: "#4A5568" },
];

function stationRole(stationName, impact) {
  if (!impact || !stationName) return "mid";
  if (impact.surge_stations?.some((s) => s.station_name === stationName)) return "peaking";
  if (impact.quiet_stations?.some((s) => s.station_name === stationName)) return "soft";
  return "mid";
}

export default function DailyImpact() {
  const { network } = useNetwork();
  const [meta, setMeta] = useState(null);
  const [dayType, setDayType] = useState("weekday");
  const [windowId, setWindowId] = useState("morning_peak");
  const [stationFilter, setStationFilter] = useState("");
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
      .then((res) => {
        if (cancelled) return;
        setImpact(res.data);
        setStationFilter((prev) => {
          if (!prev) return "";
          const stillThere = res.data.stations?.some((s) => s.station_name === prev);
          return stillThere ? prev : "";
        });
      })
      .catch((e) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [network, dayType, windowId]);

  const stationOptions = useMemo(() => {
    if (!impact?.stations) return [];
    return [...impact.stations].sort((a, b) => a.station_name.localeCompare(b.station_name));
  }, [impact]);

  const selectedStation = useMemo(() => {
    if (!stationFilter || !impact?.stations) return null;
    return impact.stations.find((s) => s.station_name === stationFilter) || null;
  }, [stationFilter, impact]);

  const selectedRole = stationRole(stationFilter, impact);

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
        subtitle="Which metro stations are peaking vs soft in this normal-day window — so autos, taxis, and buses at soft exits can divert toward peaking exits"
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
              {impact && (
                <select
                  value={stationFilter}
                  onChange={(e) => setStationFilter(e.target.value)}
                  style={{ ...selectStyle, minWidth: 200 }}
                >
                  <option value="">All stations</option>
                  {stationOptions.map((s) => (
                    <option key={s.station_name} value={s.station_name}>
                      {s.station_name}
                    </option>
                  ))}
                </select>
              )}
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
              Window riders by station — {impact.day_type_label} · {impact.window_label}
            </h3>
            <p style={{ fontSize: 11.5, color: "var(--text-secondary)", marginBottom: 10 }}>
              Top 20 by absolute riders in this window (hours {impact.hours?.[0]}–
              {impact.hours?.[impact.hours.length - 1]}). Bar length = volume for readability; peaking /
              soft lists below still use share of own day (network avg share{" "}
              {impact.network_avg_window_share_pct}%).
            </p>
            <SeverityLegend />
            <RankedChart stations={impact.stations} highlightName={stationFilter || null} />
          </Card>

          {selectedStation ? (
            <StationFocus
              station={selectedStation}
              role={selectedRole}
              impact={impact}
            />
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: 20 }}>
              <StationGroup
                title="Peaking now — Pull Feeders Here"
                subtitle="This window is a large share of their own day — divert autos, taxis, and buses toward these exits"
                stations={impact.surge_stations}
                tone="surge"
                networkAvgShare={impact.network_avg_window_share_pct}
                topShare={impact.stations[0]?.avg_window_share_pct}
                topStationName={impact.stations[0]?.station_name}
                onSelectStation={setStationFilter}
              />
              <StationGroup
                title="Soft now — Send Feeders From Here"
                subtitle="This window is a small share of their own day — spare autos, taxis, and buses can move to peaking exits"
                stations={impact.quiet_stations}
                tone="quiet"
                networkAvgShare={impact.network_avg_window_share_pct}
                topShare={impact.stations[0]?.avg_window_share_pct}
                topStationName={impact.stations[0]?.station_name}
                onSelectStation={setStationFilter}
              />
            </div>
          )}
        </>
      )}
    </div>
  );
}

function SeverityLegend() {
  return (
    <div style={{ display: "flex", gap: 14, flexWrap: "wrap", marginBottom: 12, fontSize: 11.5 }}>
      {SEVERITY_LEGEND.map((item) => (
        <span key={item.label} style={{ display: "inline-flex", alignItems: "center", gap: 6, color: "var(--text-secondary)" }}>
          <span style={{ width: 10, height: 10, borderRadius: 2, background: item.color }} />
          {item.label}
        </span>
      ))}
    </div>
  );
}

function RankedChart({ stations, highlightName }) {
  const top = [...stations]
    .sort((a, b) => b.avg_window_footfall - a.avg_window_footfall)
    .slice(0, 20);

  const chartData = {
    labels: top.map((s) => s.station_name),
    datasets: [
      {
        label: "Window riders",
        data: top.map((s) => s.avg_window_footfall),
        backgroundColor: top.map((s) => {
          const base = severityColor(s.severity_label);
          if (highlightName && s.station_name !== highlightName) {
            return `${base}55`;
          }
          return base;
        }),
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
                  return `${ctx.parsed.x.toLocaleString()} riders · ${s.avg_window_share_pct}% of own day · ${s.severity_label || "—"}`;
                },
              },
            },
          },
          scales: {
            x: {
              grid: { color: "#EEF1F6" },
              ticks: {
                font: { family: "JetBrains Mono", size: 10 },
                callback: (v) => v.toLocaleString(),
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

function StationFocus({ station, role, impact }) {
  const exclude = station.station_name;
  const peakingPartners = (impact.surge_stations || [])
    .filter((s) => s.station_name !== exclude)
    .slice(0, 3);
  const softPartners = (impact.quiet_stations || [])
    .filter((s) => s.station_name !== exclude)
    .slice(0, 3);

  const roleLabel =
    role === "peaking" ? "Peaking now" : role === "soft" ? "Soft now" : "Mid-band this window";
  const roleColor =
    role === "peaking" ? "var(--critical)" : role === "soft" ? "var(--low)" : "var(--text-secondary)";

  const feederLabel =
    station.suggested_shift_trains_hr == null
      ? "—"
      : `${station.suggested_shift_trains_hr >= 0 ? "+" : ""}${station.suggested_shift_trains_hr}`;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card style={{ padding: 20 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6, flexWrap: "wrap" }}>
          <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>{station.station_name}</h3>
          {station.severity_label && <SeverityBadge severity={station.severity_label} />}
          <span
            style={{
              fontSize: 11,
              fontWeight: 600,
              color: roleColor,
              border: `1px solid ${roleColor}`,
              borderRadius: 999,
              padding: "2px 8px",
            }}
          >
            {roleLabel}
          </span>
        </div>
        <p style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 14 }}>
          Line {station.line} · {impact.day_type_label} · {impact.window_label}
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <Metric
            label="Riders in window"
            value={station.avg_window_footfall.toLocaleString()}
            hint="Average passengers here in this day type + time window (historical hourly mean)."
          />
          <Metric
            label="Share of own day"
            value={`${station.avg_window_share_pct}%`}
            hint="Percent of this station’s full-day riders that fall in this window — used for peaking / soft."
          />
          <Metric
            label="vs network share"
            value={`${station.share_vs_network_pct >= 0 ? "+" : ""}${station.share_vs_network_pct}%`}
            hint="How that share compares to the average station in the same window (+ = more concentrated here)."
          />
          <Metric
            label="Feeder divert"
            value={feederLabel}
            hint="Last-mile priority (−3 to +3): pull autos/taxis/buses toward peaking (+), send spare from soft (−), mid = 0. Not fleet dispatch."
          />
        </div>
        <p style={{ fontSize: 11.5, color: "var(--text-secondary)", marginTop: 14, lineHeight: 1.55 }}>
          {role === "peaking" &&
            "This window is a large part of this station’s day — pull autos, taxis, and buses here. Soft stations below are spare feeder sources."}
          {role === "soft" &&
            "This window is a small part of this station’s day — spare autos, taxis, and buses here can divert toward peaking exits below."}
          {role === "mid" &&
            "Share of own day is typical (not top or bottom quartile). Short lists below show where to pull or send feeders in this same window."}
        </p>
      </Card>

      <PartnerSection
        title="Peaking stations (short list)"
        subtitle="Pull autos, taxis, and buses toward these exits — this window is a large share of their own day."
        stations={peakingPartners}
        accent="var(--critical)"
        empty="No other peaking stations in this window."
        unitPositive="feeder pull"
        unitNegative="send feeders"
      />
      <PartnerSection
        title="Soft stations (short list)"
        subtitle="Spare autos, taxis, and buses at these exits — this window is a small share of their own day."
        stations={softPartners}
        accent="var(--low)"
        empty="No other soft stations in this window."
        unitPositive="feeder pull"
        unitNegative="send feeders"
      />
    </div>
  );
}

function PartnerSection({ title, subtitle, stations, accent, empty, unitPositive, unitNegative }) {
  return (
    <Card style={{ padding: 20 }}>
      <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 4, color: accent }}>{title}</h3>
      <p style={{ fontSize: 11.5, color: "var(--text-secondary)", marginBottom: 14 }}>{subtitle}</p>
      {stations.length === 0 ? (
        <div style={{ fontSize: 12.5, color: "var(--text-secondary)" }}>{empty}</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {stations.map((s) => {
            const prio = s.suggested_shift_trains_hr;
            const unit =
              prio == null ? "" : prio >= 0 ? unitPositive || "feeder pull" : unitNegative || "send feeders";
            return (
              <div
                key={s.station_name}
                style={{
                  padding: "10px 12px",
                  border: "1px solid var(--border)",
                  borderLeft: `3px solid ${severityColor(s.severity_label)}`,
                  borderRadius: 8,
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center" }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
                      <span style={{ fontSize: 12.5, fontWeight: 600 }}>{s.station_name}</span>
                      {s.severity_label && <SeverityBadge severity={s.severity_label} />}
                    </div>
                    <div style={{ fontSize: 10.5, color: "var(--text-secondary)", marginTop: 2 }}>
                      Line {s.line} · {s.avg_window_share_pct}% of own day · {s.avg_window_footfall.toLocaleString()} riders
                    </div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div className="mono" style={{ fontSize: 13, fontWeight: 700 }}>
                      {prio == null ? "—" : `${prio >= 0 ? "+" : ""}${prio}`}
                    </div>
                    <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>{unit || "—"}</div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}

function Metric({ label, value, hint }) {
  return (
    <div style={{ padding: "10px 12px", background: "#F8FAFC", borderRadius: 8, border: "1px solid var(--border)" }}>
      <div style={{ fontSize: 10.5, color: "var(--text-secondary)", marginBottom: 4 }}>{label}</div>
      <div className="mono" style={{ fontSize: 16, fontWeight: 700 }}>{value}</div>
      {hint && (
        <div style={{ fontSize: 10, color: "var(--text-secondary)", marginTop: 6, lineHeight: 1.45 }}>{hint}</div>
      )}
    </div>
  );
}

function StationGroup({ title, subtitle, stations, tone, networkAvgShare, topShare, topStationName, onSelectStation }) {
  const accent = tone === "surge" ? "var(--critical)" : "var(--low)";
  return (
    <Card style={{ padding: 20 }}>
      <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 4, color: accent }}>{title}</h3>
      <p style={{ fontSize: 11.5, color: "var(--text-secondary)", marginBottom: tone === "quiet" ? 8 : 14 }}>
        {subtitle}
      </p>
      {tone === "quiet" && topShare != null && (
        <p style={{ fontSize: 11, color: "var(--text-secondary)", marginBottom: 6, fontStyle: "italic" }}>
          Autos, taxis, and buses waiting at these exits can divert toward {topStationName} and other
          peaking stations (up to {topShare}% of their own day in this window).
        </p>
      )}
      {tone === "quiet" && (
        <p style={{ fontSize: 11, color: "var(--text-secondary)", marginBottom: 14, lineHeight: 1.5 }}>
          Note: everyday severity (Critical/High) is year-round last-mile pressure, not this window&apos;s
          share. A Critical hub can still appear here if it is <em>soft relative to its own day</em> in
          this band — send spare feeders for this window, not cut base service. Click a station to focus.
        </p>
      )}
      {stations.length === 0 ? (
        <div style={{ color: "var(--text-secondary)", fontSize: 12.5 }}>No stations in this group.</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {stations.map((s) => (
            <button
              key={s.station_name}
              type="button"
              onClick={() => onSelectStation?.(s.station_name)}
              style={{
                padding: "10px 12px",
                border: "1px solid var(--border)",
                borderLeft: `3px solid ${severityColor(s.severity_label)}`,
                borderRadius: 8,
                background: "var(--card)",
                textAlign: "left",
                cursor: "pointer",
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
                    {s.avg_window_footfall.toLocaleString()} riders
                  </div>
                </div>
              </div>
              {tone === "quiet" && networkAvgShare > 0 && (
                <div style={{ fontSize: 10.5, color: "var(--text-secondary)", marginTop: 6 }}>
                  {Math.round((s.avg_window_share_pct / networkAvgShare) * 100)}% of network average window
                  share ({networkAvgShare}%)
                </div>
              )}
            </button>
          ))}
        </div>
      )}
    </Card>
  );
}
