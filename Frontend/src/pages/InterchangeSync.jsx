import { useEffect, useMemo, useState } from "react";
import api from "../api.js";
import { Card, PageHeader } from "../components/ui.jsx";
import { Loading, ErrorState } from "../components/StatusStates.jsx";
import { useNetwork } from "../context/NetworkContext.jsx";
import SyntheticBanner from "../components/SyntheticBanner.jsx";

const QUALITY_COLOR = {
  excellent: "var(--low)",
  good: "var(--medium)",
  poor: "var(--critical)",
};

export default function InterchangeSync() {
  const { expansion } = useNetwork();
  if (expansion) return <ExpansionInterchange />;
  return <MumbaiInterchange />;
}

function ExpansionInterchange() {
  const { network, synthetic, surveyBacked } = useNetwork();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .expansionInterchange(network)
      .then((res) => setData(res.data))
      .catch((e) => setError(e.message));
  }, [network]);

  if (error) return <ErrorState message={error} />;
  if (!data) return <Loading label="Loading interchange checks" />;

  const networkLabel = network === "delhi" ? "Delhi" : "future Mumbai";
  const note =
    data.rows[0]?.note ||
    "Metro-to-metro planning check only. Railway / monorail links are excluded. Wait is half the headway, not a live timetable.";

  return (
    <div>
      <PageHeader
        title="Interchange Sync"
        subtitle={`Metro-to-metro interchange sync for ${networkLabel} — same idea as Mumbai 69 (no railway / monorail links)`}
      />
      {synthetic && <SyntheticBanner>{note}</SyntheticBanner>}
      {network === "delhi" && surveyBacked && (
        <div style={{ padding: "12px 16px", background: "#EEF6FF", border: "1px solid #90CAF9", borderRadius: 8, fontSize: 12.5, lineHeight: 1.55, marginBottom: 18 }}>
          {note}
        </div>
      )}
      {data.rows.length === 0 ? (
        <div style={{ padding: 28, textAlign: "center", color: "var(--text-secondary)", fontSize: 13 }}>
          No metro-to-metro interchange stations on this network list.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {data.rows.map((r) => {
            const lineA = r.line_a || r.line;
            const lineB = r.line_b || r.connects_to;
            const qualityColor = QUALITY_COLOR[r.sync_quality] || "var(--text-secondary)";
            return (
              <Card key={`${r.station_name}-${lineA}-${lineB}`} style={{ padding: "16px 18px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 14, flexWrap: "wrap", alignItems: "center" }}>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 14.5 }}>{r.station_name}</div>
                    <div style={{ fontSize: 12.5, color: "var(--text-secondary)", marginTop: 3 }}>
                      Line {lineA} &harr; Line {lineB} interchange
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 18, alignItems: "center", flexWrap: "wrap" }}>
                    <div style={{ textAlign: "right" }}>
                      <div className="mono" style={{ fontWeight: 700, fontSize: 16 }}>{r.expected_wait_min} min</div>
                      <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>expected wait</div>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <div className="mono" style={{ fontWeight: 700, fontSize: 16 }}>{r.trains_per_hour}</div>
                      <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>trains/hr</div>
                    </div>
                    <div
                      style={{
                        padding: "6px 12px",
                        borderRadius: 20,
                        fontSize: 12,
                        fontWeight: 600,
                        color: qualityColor,
                        background: "var(--card)",
                        border: `1px solid ${qualityColor}`,
                        textTransform: "capitalize",
                      }}
                    >
                      {r.sync_quality}
                    </div>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

function MumbaiInterchange() {
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
