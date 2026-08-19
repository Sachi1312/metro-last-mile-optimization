import { useEffect, useMemo, useState } from "react";
import api from "../api.js";
import { Card, PageHeader } from "../components/ui.jsx";
import { Loading, ErrorState } from "../components/StatusStates.jsx";

const QUALITY_COLOR = {
  excellent: "var(--low)",
  good: "var(--medium)",
  poor: "var(--critical)",
};

export default function InterchangeSync() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .interchange("Normal")
      .then((res) => setData(res.data))
      .catch((e) => setError(e.message));
  }, []);

  const byStation = useGroupedByStation(data?.details);

  if (error) return <ErrorState message={error} />;
  if (!data) return <Loading label="Loading interchange sync analysis" />;

  return (
    <div>
      <PageHeader
        title="Interchange Sync"
        subtitle="Timetable synchronization analysis for metro-to-metro interchange stations — Marol Naka, DN Nagar, Gundavali"
      />

      <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
        {Object.entries(byStation).map(([station, rows]) => (
          <StationSyncBlock key={station} station={station} rows={rows} summary={data.summary[station]} />
        ))}
      </div>
    </div>
  );
}

function useGroupedByStation(details) {
  return useMemo(() => {
    const grouped = {};
    for (const d of details || []) {
      if (!grouped[d.station]) grouped[d.station] = [];
      grouped[d.station].push(d);
    }
    return grouped;
  }, [details]);
}

function StationSyncBlock({ station, rows, summary }) {
  return (
    <Card style={{ padding: 22 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, flexWrap: "wrap", gap: 10 }}>
        <div>
          <h3 style={{ fontSize: 15, fontWeight: 700 }}>{station}</h3>
          <p style={{ fontSize: 11.5, color: "var(--text-secondary)", marginTop: 2 }}>
            {rows[0]?.line_a} &harr; {rows[0]?.line_b} interchange
          </p>
        </div>
        {summary && (
          <div style={{ display: "flex", gap: 14 }}>
            <SummaryPill label="Excellent" value={summary.excellent || 0} color="var(--low)" />
            <SummaryPill label="Good" value={summary.good || 0} color="var(--medium)" />
            <SummaryPill label="Poor" value={summary.poor || 0} color="var(--critical)" />
          </div>
        )}
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
          gap: 12,
        }}
      >
        {rows.map((r, i) => (
          <WaitCard key={i} row={r} />
        ))}
      </div>
    </Card>
  );
}

function SummaryPill({ label, value, color }) {
  return (
    <div style={{ textAlign: "center" }}>
      <div className="mono" style={{ fontSize: 16, fontWeight: 700, color }}>
        {value}
      </div>
      <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>{label}</div>
    </div>
  );
}

function WaitCard({ row }) {
  const color = QUALITY_COLOR[(row.sync_quality || "").toLowerCase()] || "var(--text-secondary)";
  return (
    <div
      style={{
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: "12px 14px",
        background: "#FBFCFE",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div style={{ fontSize: 12, fontWeight: 600, textTransform: "capitalize" }}>
          {row.time_window?.replace(/_/g, " ")}
        </div>
        <span
          style={{
            fontSize: 10,
            fontWeight: 700,
            color,
            textTransform: "uppercase",
            background: `${color}18`,
            padding: "2px 7px",
            borderRadius: 10,
          }}
        >
          {row.sync_quality}
        </span>
      </div>

      <div style={{ display: "flex", gap: 16, marginTop: 10 }}>
        <div>
          <div style={{ fontSize: 9.5, color: "var(--text-secondary)" }}>Without sync</div>
          <div className="mono" style={{ fontSize: 15, fontWeight: 700 }}>
            {row.avg_wait_without_sync_min} min
          </div>
        </div>
        <div>
          <div style={{ fontSize: 9.5, color: "var(--text-secondary)" }}>With sync</div>
          <div className="mono" style={{ fontSize: 15, fontWeight: 700, color: "var(--accent)" }}>
            {row.avg_wait_with_sync_min} min
          </div>
        </div>
      </div>

      <div style={{ fontSize: 10.5, color: "var(--text-secondary)", marginTop: 8 }}>
        Offset {row.optimal_offset_sec}s · Journey {row.total_journey_min} min
      </div>
    </div>
  );
}
