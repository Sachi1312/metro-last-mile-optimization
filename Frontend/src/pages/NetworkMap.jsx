import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api.js";
import { PageHeader, StatTile } from "../components/ui.jsx";
import { Loading, ErrorState } from "../components/StatusStates.jsx";
import SeverityBadge, { severityColor, lineColor } from "../components/SeverityBadge.jsx";

const LINES = [
  { value: null, label: "All Lines" },
  { value: "1", label: "Line 1" },
  { value: "2A", label: "Line 2A" },
  { value: "7", label: "Line 7" },
  { value: "3", label: "Line 3" },
];

const SEVERITIES = ["Critical", "High", "Medium", "Low"];

export default function NetworkMap() {
  const [stations, setStations] = useState(null);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState(null);
  const [line, setLine] = useState(null);
  const [severityFilter, setSeverityFilter] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;
    setStations(null);
    setError(null);
    Promise.all([api.stations(line), api.networkSummary()])
      .then(([sRes, nRes]) => {
        if (cancelled) return;
        setStations(sRes.data.stations);
        setSummary(nRes.data);
      })
      .catch((e) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [line]);

  if (error) return <ErrorState message={error} />;
  if (!stations) return <Loading label="Loading network data" />;

  const filtered = severityFilter
    ? stations.filter((s) => s.severity_label === severityFilter)
    : stations;

  return (
    <div>
      <PageHeader
        title="Network Map"
        subtitle="69 stations across Lines 1, 2A, 7, and 3 — color coded by last-mile priority severity"
      />

      {summary && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
            gap: 14,
            marginBottom: 24,
          }}
        >
          <StatTile label="Total Stations" value={summary.total_stations} />
          <StatTile
            label="Critical"
            value={summary.severity_distribution?.Critical ?? 0}
            accent="var(--critical)"
          />
          <StatTile
            label="High"
            value={summary.severity_distribution?.High ?? 0}
            accent="var(--high)"
          />
          <StatTile label="Avg LMPI Score" value={summary.avg_lmpi_score} />
          <StatTile
            label="Top Critical Station"
            value={summary.top_critical_station?.station_name ?? "—"}
            sub={
              summary.top_critical_station
                ? `LMPI ${summary.top_critical_station.lmpi_score}`
                : null
            }
          />
        </div>
      )}

      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 20,
          alignItems: "center",
          marginBottom: 20,
        }}
      >
        <FilterGroup label="Line">
          {LINES.map((l) => (
            <FilterButton
              key={l.label}
              active={line === l.value}
              onClick={() => setLine(l.value)}
              dot={l.value ? lineColor(l.value) : null}
            >
              {l.label}
            </FilterButton>
          ))}
        </FilterGroup>

        <FilterGroup label="Severity">
          <FilterButton active={!severityFilter} onClick={() => setSeverityFilter(null)}>
            All
          </FilterButton>
          {SEVERITIES.map((s) => (
            <FilterButton
              key={s}
              active={severityFilter === s}
              onClick={() => setSeverityFilter(s)}
              dot={severityColor(s)}
            >
              {s}
            </FilterButton>
          ))}
        </FilterGroup>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
          gap: 14,
        }}
      >
        {filtered.map((s) => (
          <StationCard key={s.station_name} station={s} onClick={() => navigate(`/station/${encodeURIComponent(s.station_name)}`)} />
        ))}
      </div>

      {filtered.length === 0 && (
        <div style={{ padding: 40, textAlign: "center", color: "var(--text-secondary)" }}>
          No stations match this filter.
        </div>
      )}
    </div>
  );
}

function FilterGroup({ label, children }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <span style={{ fontSize: 11.5, color: "var(--text-secondary)", fontWeight: 600 }}>{label}</span>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>{children}</div>
    </div>
  );
}

function FilterButton({ active, onClick, children, dot }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 6,
        padding: "6px 12px",
        borderRadius: 20,
        fontSize: 12.5,
        fontWeight: 500,
        border: `1px solid ${active ? "var(--accent)" : "var(--border)"}`,
        background: active ? "var(--accent-light)" : "var(--card)",
        color: active ? "var(--accent)" : "var(--text-secondary)",
      }}
    >
      {dot && <span style={{ width: 7, height: 7, borderRadius: "50%", background: dot }} />}
      {children}
    </button>
  );
}

function StationCard({ station, onClick }) {
  const color = severityColor(station.severity_label);
  return (
    <div
      onClick={onClick}
      style={{
        background: "var(--card)",
        border: "1px solid var(--border)",
        borderLeft: `3px solid ${color}`,
        borderRadius: "var(--radius)",
        boxShadow: "var(--shadow)",
        padding: "14px 16px",
        cursor: "pointer",
        transition: "box-shadow 0.15s, transform 0.15s",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.boxShadow = "var(--shadow-hover)";
        e.currentTarget.style.transform = "translateY(-1px)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.boxShadow = "var(--shadow)";
        e.currentTarget.style.transform = "none";
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
        <div>
          <div style={{ fontWeight: 600, fontSize: 14 }}>{station.station_name}</div>
          <div style={{ fontSize: 11.5, color: "var(--text-secondary)", marginTop: 2 }}>
            Line {station.line}
            {station.is_interchange ? " · Interchange" : ""}
          </div>
        </div>
        <SeverityBadge severity={station.severity_label} />
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 6, marginTop: 12 }}>
        <span className="mono" style={{ fontSize: 20, fontWeight: 700 }}>
          {station.lmpi_score ?? "—"}
        </span>
        <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>LMPI</span>
      </div>
      {station.recommended_last_mile && (
        <div style={{ fontSize: 11.5, color: "var(--text-secondary)", marginTop: 6 }}>
          {station.recommended_last_mile}
        </div>
      )}
    </div>
  );
}
