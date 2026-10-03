import { useEffect, useState } from "react";
import api from "../api.js";
import { Card, PageHeader } from "../components/ui.jsx";
import { Loading, ErrorState } from "../components/StatusStates.jsx";
import { useNetwork } from "../context/NetworkContext.jsx";
import SyntheticBanner from "../components/SyntheticBanner.jsx";

export default function ModeChoice() {
  const { network, synthetic } = useNetwork();
  const [data, setData] = useState(null);
  const [selected, setSelected] = useState("");
  const [error, setError] = useState(null);

  useEffect(() => {
    setData(null);
    setSelected("");
    api
      .expansionChoice(network)
      .then((res) => {
        setData(res.data);
        if (res.data.rows?.length) setSelected(res.data.rows[0].station_name);
      })
      .catch((e) => setError(e.message));
  }, [network]);

  if (error) return <ErrorState message={error} />;
  if (!data) return <Loading label="Loading mode choice" />;

  const station = data.rows.find((r) => r.station_name === selected) || data.rows[0];
  const toward = data.coefficients.filter((c) => c.direction === "opt in");
  const away = data.coefficients.filter((c) => c.direction === "opt out");

  return (
    <div>
      <PageHeader
        title="Mode Choice"
        subtitle="Would a commuter opt in, and which station facts push them toward the metro or away from it."
        right={
          <select
            value={station?.station_name || ""}
            onChange={(e) => setSelected(e.target.value)}
            style={{ padding: "9px 14px", borderRadius: 8, border: "1px solid var(--border)", minWidth: 220, background: "var(--card)" }}
          >
            {data.rows.map((r) => (
              <option key={r.station_name} value={r.station_name}>
                {r.station_name}
              </option>
            ))}
          </select>
        }
      />

      {synthetic && (
        <SyntheticBanner>
          This chance is the Mumbai-trained model applied to the station's facts. It is not a survey taken in Delhi or on a future line.
        </SyntheticBanner>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 14, marginBottom: 18 }}>
        <Card style={{ padding: 16 }}>
          <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>Opt-in chance</div>
          <div className="mono" style={{ fontSize: 28, fontWeight: 700 }}>
            {station ? `${Math.round(station.opt_in_probability * 100)}%` : "—"}
          </div>
          {station?.discovered_cluster && (
            <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4 }}>{station.discovered_cluster}</div>
          )}
        </Card>
        <Card style={{ padding: 16 }}>
          <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>Model accuracy</div>
          <div className="mono" style={{ fontSize: 28, fontWeight: 700 }}>{Math.round(data.accuracy * 1000) / 10}%</div>
          <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
            Majority baseline {Math.round(data.majority_baseline * 1000) / 10}%
          </div>
        </Card>
        <Card style={{ padding: 16 }}>
          <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>F1 / precision</div>
          <div className="mono" style={{ fontSize: 28, fontWeight: 700 }}>{Math.round(data.f1_weighted * 1000) / 10}%</div>
          <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
            Precision {Math.round(data.precision_weighted * 1000) / 10}%
          </div>
        </Card>
      </div>

      {station?.survey_opt_in_rate != null && (
        <p style={{ fontSize: 12.5, color: "var(--text-secondary)", marginBottom: 14 }}>
          On the real Mumbai survey, {Math.round(station.survey_opt_in_rate * 100)}% of responses at {station.station_name} met the opt-in rule.
          The model, which never saw those answers, estimates {Math.round(station.opt_in_probability * 100)}%.
        </p>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 16 }}>
        <ReasonCard title="Pushes people toward the metro" rows={toward} />
        <ReasonCard title="Pushes people away" rows={away} />
      </div>

      <Card style={{ padding: 16, marginTop: 16 }}>
        <div style={{ fontSize: 12.5, lineHeight: 1.55, color: "var(--text-secondary)" }}>{data.rule}</div>
      </Card>
    </div>
  );
}

function ReasonCard({ title, rows }) {
  return (
    <Card style={{ padding: 16 }}>
      <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 10 }}>{title}</h3>
      {rows.map((r) => (
        <div key={r.feature} style={{ display: "flex", justifyContent: "space-between", gap: 12, padding: "8px 0", borderBottom: "1px solid var(--border)", fontSize: 13 }}>
          <span>{r.label}</span>
          <span className="mono">{r.coefficient > 0 ? "+" : ""}{r.coefficient}</span>
        </div>
      ))}
      {rows.length === 0 && <div style={{ fontSize: 12.5, color: "var(--text-secondary)" }}>None of the station facts pushed this way.</div>}
    </Card>
  );
}
