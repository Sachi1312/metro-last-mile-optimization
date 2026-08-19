import { useEffect, useState } from "react";
import api from "../api.js";
import { PageHeader, StatTile } from "../components/ui.jsx";
import { Loading, ErrorState } from "../components/StatusStates.jsx";
import SeverityBadge, { severityColor } from "../components/SeverityBadge.jsx";
import { estimateFleetCount, fleetLabel, aggregateFleetCounts } from "../utils/fleetEstimate.js";

const SEVERITIES = ["Critical", "High", "Medium", "Low"];

export default function Interventions() {
  const [severity, setSeverity] = useState(null);
  const [data, setData] = useState(null);
  const [networkTotals, setNetworkTotals] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setData(null);
    api
      .interventions(severity, 30)
      .then((res) => setData(res.data))
      .catch((e) => setError(e.message));
  }, [severity]);

  useEffect(() => {
    Promise.all([api.interventions(null, 300), api.networkSummary()])
      .then(([ivRes, sumRes]) => {
        const fleet = aggregateFleetCounts(ivRes.data.interventions);
        setNetworkTotals({
          autos: fleet.auto,
          buses: fleet.bus,
          trains: sumRes.data.frequency_stats?.total_additional_trains_peak,
        });
      })
      .catch(() => {});
  }, []);

  if (error) return <ErrorState message={error} />;

  const maxImpact = data ? Math.max(...data.interventions.map((iv) => iv.impact_score || 0), 1) : 1;

  return (
    <div>
      <PageHeader
        title="Interventions"
        subtitle="Layer 4 — ranked last-mile intervention queue, prioritized by impact and cost-effectiveness"
        right={
          <div style={{ display: "flex", gap: 6 }}>
            <FilterButton active={!severity} onClick={() => setSeverity(null)}>
              All
            </FilterButton>
            {SEVERITIES.map((s) => (
              <FilterButton key={s} active={severity === s} onClick={() => setSeverity(s)} dot={severityColor(s)}>
                {s}
              </FilterButton>
            ))}
          </div>
        }
      />

      {networkTotals && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 14, marginBottom: 20 }}>
          <StatTile
            label="Additional Trains Needed"
            value={networkTotals.trains !== undefined ? `+${networkTotals.trains}` : "—"}
            sub="peak hour, network-wide"
          />
          <StatTile
            label="Approx. Auto/E-Rickshaw Fleet"
            value={`≈ ${networkTotals.autos}`}
            sub="assuming ~Rs 2L/vehicle/year"
          />
          <StatTile
            label="Approx. Bus/Shuttle Fleet"
            value={`≈ ${networkTotals.buses}`}
            sub="assuming ~Rs 15L/vehicle/year"
          />
        </div>
      )}

      {!data ? (
        <Loading label="Loading interventions" />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {data.interventions.map((iv, i) => (
            <InterventionCard key={i} iv={iv} rank={i + 1} maxImpact={maxImpact} />
          ))}
          {data.interventions.length === 0 && (
            <div style={{ padding: 40, textAlign: "center", color: "var(--text-secondary)" }}>
              No interventions match this filter.
            </div>
          )}
        </div>
      )}
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

function InterventionCard({ iv, rank, maxImpact }) {
  const color = severityColor(iv.severity_label);
  const pct = ((iv.impact_score || 0) / maxImpact) * 100;
  const fleet = estimateFleetCount(iv.intervention, iv.estimated_cost_lakhs);
  return (
    <div
      style={{
        background: "var(--card)",
        border: "1px solid var(--border)",
        borderLeft: `3px solid ${color}`,
        borderRadius: "var(--radius)",
        boxShadow: "var(--shadow)",
        padding: "16px 20px",
        display: "flex",
        alignItems: "center",
        gap: 20,
        flexWrap: "wrap",
      }}
    >
      <div
        className="mono"
        style={{
          width: 30,
          height: 30,
          borderRadius: 8,
          background: "#F4F6F9",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 12,
          fontWeight: 700,
          color: "var(--text-secondary)",
          flexShrink: 0,
        }}
      >
        {rank}
      </div>

      <div style={{ flex: "2 1 260px", minWidth: 220 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <span style={{ fontWeight: 600, fontSize: 13.5 }}>{iv.intervention}</span>
          <SeverityBadge severity={iv.severity_label} />
        </div>
        <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 3 }}>
          {iv.station_name} · Line {iv.line} · {iv.priority} priority
          {fleet && ` · ≈ ${fleet.count} ${fleetLabel(fleet.type)}`}
        </div>
      </div>

      <div style={{ flex: "1 1 160px", minWidth: 140 }}>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, marginBottom: 4 }}>
          <span style={{ color: "var(--text-secondary)" }}>Impact</span>
          <span className="mono" style={{ fontWeight: 600 }}>
            {iv.impact_score}
          </span>
        </div>
        <div style={{ height: 6, background: "#EEF1F6", borderRadius: 4, overflow: "hidden" }}>
          <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 4 }} />
        </div>
      </div>

      <div style={{ textAlign: "right", flexShrink: 0 }}>
        <div className="mono" style={{ fontSize: 15, fontWeight: 700 }}>
          Rs {iv.estimated_cost_lakhs} L
        </div>
        <div style={{ fontSize: 10.5, color: "var(--text-secondary)" }}>estimated cost</div>
      </div>
    </div>
  );
}
